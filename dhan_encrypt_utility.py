import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Load or generate encryption key
load_dotenv()

if os.environ.get('key'):
    mysecret = os.environ.get('key').encode()
else:
    # Generate new key for first time
    mysecret = Fernet.generate_key()
    with open(".env", "w") as envf:
        envf.write(f"key={mysecret.decode()}")

print(f"Encryption key: {mysecret}")

f = Fernet(mysecret)
access_token = input("Enter Dhan access token to encrypt: ")

# Encrypt the access token
password = str(access_token).encode()
encrypted = f.encrypt(password)

print(f"Encrypted access token: {encrypted.decode()}")
print("\nUse this encrypted value in your config.json file")
print("To decrypt: use the deCryptPwd() function in the main script")