# Dhan Copy Trading System

A Python-based automated copy trading system that replicates trades from a master Dhan account to multiple child accounts in real-time.

## Features

- **Real-time Order Replication**: Automatically copies orders from master account to child accounts
- **Multi-Account Support**: Support for multiple child accounts with individual multipliers
- **Order Management**: Handles order creation, updates, and cancellations
- **Margin Monitoring**: Real-time margin and fund monitoring for all accounts
- **Secure Configuration**: Encrypted storage of access tokens
- **Comprehensive Logging**: Detailed logging for debugging and monitoring
- **Product Filtering**: Ability to exclude certain product types from copying

## Prerequisites

1. **Dhan Trading Account**: You need active Dhan trading accounts (master + child accounts)
2. **API Access**: Enable API access for all accounts through Dhan web platform
3. **Access Tokens**: Generate access tokens for each account
4. **Python 3.7+**: Compatible Python installation

## Installation

1. **Clone/Download** the repository to your local machine

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup Configuration**:
   - Copy `dhan_config_template.json` to `config.json`
   - Generate access tokens from Dhan web platform
   - Encrypt your access tokens using the encryption utility

## Getting Dhan API Access

1. **Login to Dhan Web Platform**
2. **Navigate to Profile Section**
3. **Go to "DhanHQ Trading APIs"**
4. **Click "Request Access"** (if first time)
5. **Generate Access Token**
6. **Copy the access token** for configuration

## Configuration Setup

### Step 1: Generate Encryption Key and Encrypt Access Tokens

```bash
python dhan_encrypt_utility.py
```

This will:
- Generate an encryption key (stored in `.env` file)
- Prompt you to enter access tokens to encrypt
- Provide encrypted values for `config.json`

### Step 2: Configure Accounts

Edit `config.json` with your account details:

```json
{
    "MASTER": {
        "client_id": "YOUR_MASTER_CLIENT_ID",
        "access_token": "encrypted_access_token_from_step1"
    },
    "CHILD": {
        "CHILD1": {
            "client_id": "CHILD_CLIENT_ID_1",
            "access_token": "encrypted_access_token_from_step1",
            "multiplier": 1,
            "enabled": "Y"
        }
    },
    "DONOTPROCESSPROD": ["BO", "CO"]
}
```

**Configuration Parameters**:
- `client_id`: Your Dhan client ID
- `access_token`: Encrypted access token from Step 1
- `multiplier`: Order quantity multiplier (1 = same quantity, 0.5 = half quantity)
- `enabled`: "Y" to enable account, "N" to disable
- `DONOTPROCESSPROD`: Product types to exclude from copying

## Running the System

```bash
python dhan_copytrader.py
```

The system will:
1. Connect to all configured accounts
2. Display margin information
3. Start monitoring for order updates
4. Automatically replicate orders from master to child accounts

## Key Differences from Zerodha Kite Version

### Authentication
- **Dhan**: Uses access tokens (no browser automation required)
- **Zerodha**: Required browser automation with TOTP

### API Structure
- **Dhan**: Direct REST API with `dhanhq` Python SDK
- **Zerodha**: Used `kiteconnect` SDK with WebSocket for live updates

### Configuration
- **Simplified**: No need for login URLs, passwords, or TOTP secrets
- **Token-based**: Only requires client ID and access token

### Order Parameters
- **Field Mapping**: Automatic mapping between Zerodha and Dhan order parameters
- **Product Types**: Different product type codes between brokers

## Order Flow

1. **Order Placed** in master account
2. **System Detects** order update
3. **Validates** order parameters and product type filters
4. **Calculates** quantities based on child account multipliers
5. **Places/Updates/Cancels** corresponding orders in child accounts
6. **Logs** all activities for monitoring

## Monitoring and Logs

- **Console Output**: Real-time status updates and margin information
- **Log File**: Detailed logging in `logcopytrade.log`
- **Error Handling**: Comprehensive error handling with stack traces

## Security Features

- **Encrypted Storage**: All access tokens are encrypted using Fernet encryption
- **Environment Variables**: Encryption key stored in `.env` file
- **No Plain Text Secrets**: No sensitive data stored in plain text

## Troubleshooting

### Common Issues

1. **Connection Errors**:
   - Verify access tokens are valid and not expired
   - Check client IDs are correct
   - Ensure API access is enabled for all accounts

2. **Order Creation Failures**:
   - Check margin availability in child accounts
   - Verify instrument mapping
   - Review product type filters

3. **Live Feed Issues**:
   - Dhan live feed may require additional setup
   - System can work without live feed using manual triggers

### Logging

Check `logcopytrade.log` for detailed information about:
- Connection status
- Order processing
- Error messages
- System events

## Limitations

1. **Live Feed**: Dhan's WebSocket implementation may differ from Zerodha
2. **Instrument Mapping**: May require manual mapping for some instruments
3. **Order Types**: Some complex order types may need additional handling

## Support

- Check Dhan API documentation: https://dhanhq.co/docs/v2/
- Review log files for error details
- Ensure all accounts have sufficient margins

## Disclaimer

This software is for educational purposes. Use at your own risk. Ensure you understand the implications of automated trading and test thoroughly with small quantities before deploying with larger amounts.