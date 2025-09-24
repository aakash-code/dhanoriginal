import time
import os
import traceback
import logging
import json
import sys
import asyncio
import websockets
from dhanhq import dhanhq
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Set logger
logging.basicConfig(
    filename='logcopytrade.log',
    format='%(asctime)s-%(process)d-%(levelname)s-%(message)s',
    level=logging.INFO
)

logging.info("Program Dhan Copytrader started")

sourceOrders = {}
childaccts = {}
orderlookup = {}
dhanmaster = None
configFile = 'config.json'

# Load configuration
with open(configFile, 'r') as f:
    config = json.load(f)

# Load encryption key
load_dotenv()
if os.environ.get('key'):
    mysecret = os.environ.get('key').encode()
else:
    print('Environment file not found. Exiting')
    sys.exit()


def deCryptPwd(encodedPwd):
    """Decrypt encrypted passwords/tokens"""
    f = Fernet(mysecret)
    enc = encodedPwd.encode()
    dec = f.decrypt(enc)
    return dec.decode()


def create_dhan_connection(user_config):
    """Create Dhan API connection"""
    try:
        dhan = dhanhq(
            client_id=user_config['client_id'],
            access_token=deCryptPwd(user_config['access_token'])
        )
        test = dhan.get_fund_limits()
        if test.get('status') != 'success':
            raise Exception("Failed to fetch fund limits")
        return dhan
    except Exception as e:
        logging.error(f"Failed to connect to Dhan for {user_config['client_id']}: {e}")
        print(f"Connection error for master client id: {user_config['client_id']}. Exiting program!")
        sys.exit()


def copyTrade(data):
    """Main copy trading logic"""
    logging.debug('Starting copy trade')
    
    # Check if product type should be filtered
    if data.get('Product') not in prodFilter:
        if data.get('Status') == 'CANCELLED':
            cancelTargetOrders(data)
        else:
            logging.debug('Copy trade open and update')
            
            # Process PENDING, TRANSIT, or OPEN orders
            status = data.get('Status', '')
            if status in ['PENDING', 'TRANSIT', 'OPEN', 'TRADED']:
                if data['OrderNo'] in sourceOrders:
                    if status in ['PENDING', 'OPEN']:
                        updateTargetOrders(data)
                else: 
                    createTargetOrders(data)
        showMarginsAvailable()
    else:
        logging.info(f"Product type {data.get('Product')} ignored")


def getTargetOrder(orderid, client_id):
    """Get target order ID from lookup"""
    key = f"{orderid}|{client_id}"
    return orderlookup.get(key)


def storeTargetOrder(parent_oid, client_id, child_oid):
    """Store child order mapping"""
    key = f"{parent_oid}|{client_id}"
    orderlookup[key] = child_oid


def createTargetOrders(data):
    """Create orders in all child accounts"""
    logging.info('Inside create orders')
    sourceOrders[data['OrderNo']] = data
    
    for childacct in childaccts:
        accDetail = childaccts[childacct]
        createTargetOrder(data, accDetail['client_id'], accDetail['dhanobj'], accDetail['multiplier'])


def createTargetOrder(orderdata, client_id, targetAccnt, multiplier):
    """Create individual target order"""
    logging.info(f'Creating order {orderdata["OrderNo"]} for {client_id}')

    try:
        quantity = int(round(int(orderdata['Quantity']) * float(multiplier), 0))
        
        order_id = targetAccnt.place_order(
            security_id=str(orderdata['SecurityId']),
            exchange_segment=map_exchange(orderdata['Exchange']),
            transaction_type=map_transaction_type(orderdata['TxnType']),
            quantity=quantity,
            order_type=map_order_type(orderdata['OrderType']),
            product_type=map_product_type(orderdata['Product']),
            price=float(orderdata.get('Price', 0)),
            trigger_price=float(orderdata.get('TriggerPrice', 0)),
            validity=map_validity(orderdata['Validity'])
        )
        
        storeTargetOrder(orderdata['OrderNo'], client_id, order_id['data']['order_id'])
        logging.info(f"Created order {client_id} - {order_id['data']['order_id']}")
        
    except Exception as e:
        stacktrace = traceback.format_exc()
        logging.error(f"ERROR Order create error {e} - {stacktrace}")
        print(f"Child order not created for parent order {orderdata['OrderNo']} for user id {client_id}")


def updateTargetOrders(data):
    """Update orders in all child accounts"""
    logging.info('Inside update orders')
    try:
        if checkifupdate(data):
            for childacct in childaccts:
                accDetail = childaccts[childacct]
                updateTargetOrder(data, accDetail['client_id'], accDetail['dhanobj'], accDetail['multiplier'])
            sourceOrders[data['OrderNo']] = data
        else:
            logging.info(f"Order id {data['OrderNo']} not changed. Not updated to child accounts")
    except Exception as e:
        stacktrace = traceback.format_exc()
        logging.error(f"ERROR Order update error {e} - {stacktrace}")
        print(f"Order mapping not found {data['OrderNo']}")


def updateTargetOrder(orderdata, client_id, targetAccnt, multiplier):
    """Update individual target order"""
    logging.info(f'Updating order {orderdata["OrderNo"]} for {client_id}')

    try:
        targetorder = getTargetOrder(orderdata['OrderNo'], client_id)
        if not targetorder:
            logging.error(f"Target order not found for {orderdata['OrderNo']} - {client_id}")
            return
            
        quantity = int(round(int(orderdata['Quantity']) * float(multiplier), 0))
        
        result = targetAccnt.modify_order(
            order_id=targetorder,
            order_type=map_order_type(orderdata['OrderType']),
            quantity=quantity,
            price=float(orderdata.get('Price', 0)),
            trigger_price=float(orderdata.get('TriggerPrice', 0)),
            validity=map_validity(orderdata['Validity'])
        )
        
        logging.info(f"Updated order {client_id} - {targetorder}")
        
    except Exception as e:
        stacktrace = traceback.format_exc()
        logging.error(f"ERROR Order update error {e} - {stacktrace}")
        print(f"Child order not updated for parent order {orderdata['OrderNo']} for user id {client_id}")


def cancelTargetOrders(data):
    """Cancel orders in all child accounts"""
    for childacct in childaccts:
        accDetail = childaccts[childacct]
        cancelTargetOrder(data, accDetail['client_id'], accDetail['dhanobj'])


def cancelTargetOrder(orderdata, client_id, targetAccnt): 
    """Cancel individual target order"""
    logging.info(f'Cancelling order {orderdata["OrderNo"]} for {client_id}')
    try:
        targetorder = getTargetOrder(orderdata['OrderNo'], client_id)
        if targetorder:
            result = targetAccnt.cancel_order(order_id=targetorder)
            logging.info(f"Cancelled order {client_id} - {targetorder}")
    except Exception as e:
        stacktrace = traceback.format_exc()
        logging.error(f"Order cancel error {e} - {stacktrace}")


def checkifupdate(orderdata):
    """Check if order parameters have changed"""
    if orderdata['OrderNo'] not in sourceOrders:
        return True
        
    origorder = sourceOrders[orderdata['OrderNo']]
    
    if orderdata.get('Status') == 'TRADED':
        return False

    # Compare key order parameters
    if (origorder.get('OrderType') == orderdata.get('OrderType') and
        origorder.get('Quantity') == orderdata.get('Quantity') and
        origorder.get('Price') == orderdata.get('Price') and
        origorder.get('TriggerPrice') == orderdata.get('TriggerPrice')):
        return False
    else:
        return True


def showMarginsAvailable():
    """Display margin information for all accounts"""
    print('---Client ID--------Available--------Used---------Cash Available-----------')
    showMargin(dhan=dhanmaster, client_id=masterconfig['client_id'])
    
    for childacct in childaccts:
        accDetail = childaccts[childacct]
        showMargin(dhan=accDetail['dhanobj'], client_id=accDetail['client_id'])
    print('--------------------------------------------------------------------')


def showMargin(dhan, client_id):
    """Show margin details for a specific account"""
    try:
        margin = dhan.get_fund_limits()
        if margin['status'] == 'success':
            funds = margin['data']
            available = funds.get('equity_amount', 0) + funds.get('commodity_amount', 0)
            used = funds.get('utilised_amount', 0)
            cash = funds.get('opening_balance', 0)
            print(f"{client_id:15} : {available:12,.0f}  {used:12,.0f}  {cash:12,.0f}")
        else:
            logging.error(f"Failed to fetch margins for {client_id}")
    except Exception as e:
        logging.error(f"Error fetching margins for {client_id}: {e}")


def map_exchange(exchange):
    """Map exchange codes"""
    exchange_map = {
        'NSE': dhanhq.NSE,
        'BSE': dhanhq.BSE,
        'NFO': dhanhq.NFO,
        'BFO': dhanhq.BFO,
        'MCX': dhanhq.MCX
    }
    return exchange_map.get(exchange, dhanhq.NSE)


def map_transaction_type(transaction_type):
    """Map transaction types"""
    if transaction_type == 'B':
        return dhanhq.BUY
    elif transaction_type == 'S':
        return dhanhq.SELL
    return dhanhq.BUY


def map_product_type(product):
    """Map product types"""
    product_map = {
        'I': dhanhq.INTRA,
        'C': dhanhq.CNC,
        'M': dhanhq.MARGIN,
        'V': dhanhq.CO,
        'B': dhanhq.BO
    }
    return product_map.get(product, dhanhq.CNC)


def map_order_type(order_type):
    """Map order types"""
    order_map = {
        'MKT': dhanhq.MARKET,
        'LMT': dhanhq.LIMIT,
        'SL': dhanhq.STOP_LOSS,
        'SLM': dhanhq.STOP_LOSS_MARKET
    }
    return order_map.get(order_type, dhanhq.MARKET)


def map_validity(validity):
    """Map validity types"""
    if validity == 'DAY':
        return dhanhq.DAY
    elif validity == 'IOC':
        return dhanhq.IOC
    else:
        return dhanhq.DAY


async def start_websocket_feed(client_id, access_token):
    """Starts the websocket feed for order updates with robust reconnection."""
    uri = "wss://api-order-update.dhan.co"

    while True:
        try:
            async with websockets.connect(uri) as websocket:
                # Authorize the connection
                auth_data = {
                    "auth_token": access_token,
                    "client_id": client_id,
                    "user_type": "SELF",
                    "feed_type": "order"
                }
                await websocket.send(json.dumps(auth_data))
                print("WebSocket authorized. Waiting for order updates...")

                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        if data.get("type") == "order_alert":
                            logging.info(f"Order alert received: {data['data']}")
                            copyTrade(data['data'])
                    except websockets.exceptions.ConnectionClosed:
                        print("WebSocket connection closed.")
                        break # Break inner loop to trigger reconnection
            except Exception as e:
                logging.error(f"Error in websocket feed: {e}")

        print("Reconnecting in 5 seconds...")
        await asyncio.sleep(5)


def main():
    """Main execution function"""
    global dhanmaster, masterconfig, prodFilter, childaccts
    
    # Load configuration
    masterconfig = config['MASTER']
    prodFilter = config.get('DONOTPROCESSPROD', [])
    
    logging.info('Connecting to Master account')
    
    try:
        # Connect to master account
        dhanmaster = create_dhan_connection(masterconfig)
        print(f'Master account {masterconfig["client_id"]} connection successful')
        
    except Exception as e:
        stacktrace = traceback.format_exc()
        logging.error(f"Connection Error {e} - {stacktrace}")
        print(f"Connection error for master client id: {masterconfig['client_id']}. Exiting program!")
        sys.exit(1)
    
    # Connect to child accounts
    logging.info('Connecting to target accounts')
    
    for childacct in config['CHILD']:
        child = {}
        childconfig = config['CHILD'][childacct]
        
        if childconfig.get('enabled') == 'Y':
            try:
                child['client_id'] = childconfig['client_id']
                child['multiplier'] = childconfig['multiplier']
                child['dhanobj'] = create_dhan_connection(childconfig)
                
                childaccts[child['client_id']] = child
                print(f"Child account {child['client_id']} connection successful")
                
            except Exception as e:
                stacktrace = traceback.format_exc()
                logging.error(f"Connection Error {e} - {stacktrace}")
                print(f"Connection error for client id: {childconfig['client_id']}. Skipping this account.")
                continue
    
    # Show initial margin information
    showMarginsAvailable()
    
    # Start the websocket feed
    try:
        access_token = deCryptPwd(masterconfig['access_token'])
        asyncio.run(start_websocket_feed(masterconfig['client_id'], access_token))
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        logging.error(f"Fatal error in main loop: {e}")
        print(f"A fatal error occurred: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        print(f"Fatal error occurred: {e}")
        sys.exit(1)