# Snowflake Key Authentication Fix for application_webhook Lambda

## The Problem

The current code passes the private key as a string, but Snowflake's Python connector 
expects it as DER-format bytes.

## The Fix

Replace your `get_snowflake_connection` function with this version:

```python
import os
import base64
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from aws_lambda_powertools.logging import Logger

logger = Logger(service="application-webhook")


def get_snowflake_connection(request_id: str):
    """
    Establish secure Snowflake connection using key pair authentication.
    
    Supports two key formats:
    1. Base64-encoded DER (stored in env var/Secrets Manager as string)
    2. PEM format (with -----BEGIN PRIVATE KEY----- headers)
    """
    logger.info("Attempting to connect to Snowflake", extra={"request_id": request_id})
    
    try:
        # Get the private key from environment
        private_key_raw = os.environ.get("SNOWFLAKE_PRIVATE_KEY")
        
        if not private_key_raw:
            raise ValueError("SNOWFLAKE_PRIVATE_KEY environment variable not set")
        
        # Try to detect format and convert to DER bytes
        private_key_der = _convert_key_to_der(private_key_raw)
        
        conn = snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_USER"],
            warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
            database=os.environ["SNOWFLAKE_DATABASE"],
            schema=os.environ["SNOWFLAKE_SCHEMA"],
            private_key=private_key_der,  # Must be DER bytes, not string
            client_session_keep_alive=True,
        )
        
        logger.info("Successfully connected to Snowflake", extra={"request_id": request_id})
        return conn
        
    except Exception as e:
        logger.error(f"Failed to connect to Snowflake: {str(e)}", extra={"request_id": request_id})
        raise


def _convert_key_to_der(private_key_raw: str) -> bytes:
    """
    Convert private key from various formats to DER bytes for Snowflake.
    
    Handles:
    - Base64-encoded DER (recommended for env vars)
    - PEM format (with or without headers)
    """
    private_key_raw = private_key_raw.strip()
    
    # Check if it's PEM format (contains BEGIN/END)
    if "BEGIN" in private_key_raw and "END" in private_key_raw:
        # It's PEM - convert to DER
        private_key = serialization.load_pem_private_key(
            private_key_raw.encode("utf-8"),
            password=None,
        )
        return private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    
    # Assume it's base64-encoded DER (no newlines, no headers)
    try:
        return base64.b64decode(private_key_raw)
    except Exception:
        raise ValueError(
            "Private key format not recognized. "
            "Expected PEM format or base64-encoded DER."
        )
```

## Deployment Steps

### Option 1: Quick Fix (Update Lambda Environment Variable)

1. **Get your current private key** from wherever it's stored

2. **Run the formatter script** to convert it:
   ```bash
   cd /Users/faisalshomemacmini/.openclaw/workspace/real-time-financial-data-lake
   python3 ../../format_snowflake_key.py /path/to/your/private_key.pem
   ```

3. **Update the Lambda environment variable** `SNOWFLAKE_PRIVATE_KEY` with the 
   base64 output (it's a single long string, no headers)

4. **Deploy the updated Lambda code** with the fixed `get_snowflake_connection` function

### Option 2: Use Secrets Manager (Recommended)

1. Store the key in Secrets Manager as JSON:
   ```json
   {
     "private_key": "-----BEGIN PRIVATE KEY-----\nMII...\n-----END PRIVATE KEY-----"
   }
   ```

2. Update the Lambda to fetch from Secrets Manager and convert

## Testing

```python
import os
os.environ["SNOWFLAKE_ACCOUNT"] = "your_account"
os.environ["SNOWFLAKE_USER"] = "LAMBDA_API_USER"
os.environ["SNOWFLAKE_PRIVATE_KEY"] = "your_base64_key"

from lambda_function import get_snowflake_connection
conn = get_snowflake_connection("test-123")
print("Connected!" if conn else "Failed")
conn.close()
```

## Snowflake Setup

Make sure the user has the public key set:

```sql
USE ROLE ACCOUNTADMIN;
ALTER USER lambda_api_user SET RSA_PUBLIC_KEY='MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...';
```

To get the public key from your private key:
```bash
openssl rsa -in private_key.pem -pubout -out public_key.pem
# Remove headers/footers for Snowflake
cat public_key.pem | grep -v "^---" | tr -d '\n'
```
