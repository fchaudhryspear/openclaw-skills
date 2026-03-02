
import os
import sys
import base64
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from aws_lambda_powertools.logging import Logger

# Mock logger for local testing
class MockLogger:
    def info(self, message, extra=None):
        print(f"INFO: {message} {extra}")
    def error(self, message, extra=None):
        print(f"ERROR: {message} {extra}")

logger = MockLogger()

# The _convert_key_to_der and get_snowflake_connection functions are copied directly
# from real-time-financial-data-lake/functions/application_webhook/lambda_function.py

def _convert_key_to_der(private_key_raw: str) -> bytes:
    private_key_raw = private_key_raw.strip()
    if "BEGIN" in private_key_raw and "END" in private_key_raw:
        private_key = serialization.load_pem_private_key(
            private_key_raw.encode("utf-8"),
            password=None,
        )
        return private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    try:
        return base64.b64decode(private_key_raw)
    except Exception as e:
        raise ValueError(
            "Private key format not recognized. "
            "Expected PEM format or base64-encoded DER." + str(e)
        )

def get_snowflake_connection(request_id: str):
    logger.info("Attempting to connect to Snowflake", extra={"request_id": request_id})
    try:
        conn_params = {
            "account": os.environ["SNOWFLAKE_ACCOUNT"],
            "user": os.environ["SNOWFLAKE_USER"],
            "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
            "database": os.environ["SNOWFLAKE_DATABASE"],
            "schema": os.environ["SNOWFLAKE_SCHEMA"],
            "client_session_keep_alive": True,
        }
        
        if os.environ.get("SNOWFLAKE_ROLE"):
            conn_params["role"] = os.environ["SNOWFLAKE_ROLE"]
        
        private_key_raw = os.environ.get("SNOWFLAKE_PRIVATE_KEY")
        if private_key_raw:
            private_key_der = _convert_key_to_der(private_key_raw)
            conn_params["private_key"] = private_key_der
            logger.info("Using key-pair authentication", extra={"request_id": request_id})
        elif os.environ.get("SNOWFLAKE_PASSWORD"):
            conn_params["password"] = os.environ["SNOWFLAKE_PASSWORD"]
            logger.info("Using password authentication", extra={"request_id": request_id})
        else:
            raise ValueError("Either SNOWFLAKE_PRIVATE_KEY or SNOWFLAKE_PASSWORD environment variable must be set")
        
        conn = snowflake.connector.connect(**conn_params)
        logger.info("Successfully connected to Snowflake", extra={"request_id": request_id})
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to Snowflake: {str(e)}", extra={"request_id": request_id})
        raise


# Set environment variables for the test
os.environ["SNOWFLAKE_ACCOUNT"] = "SBUBJHD-TY50972"
os.environ["SNOWFLAKE_USER"] = "FCHAUDHRY"
os.environ["SNOWFLAKE_WAREHOUSE"] = "INGESTION_WH"
os.environ["SNOWFLAKE_DATABASE"] = "LENDING_DB"
os.environ["SNOWFLAKE_SCHEMA"] = "RAW"
os.environ["SNOWFLAKE_ROLE"] = "ACCOUNTADMIN"
os.environ["SNOWFLAKE_PRIVATE_KEY"] = "MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCRqkkwx4Mq9/Iwc6flLHbl+GL9YF4rTTFo5hMHTew4169xI8lQWBFpz3nwUlTZF7t+qs0QXzio/MAtHDlJrTu/d9JkN9dq4AYwSlSW1AbWNf3TTyaPlrvZReBoTHz4w5q4A8U90A2yPGenn27HsefFvTh1Igs6FAGgqS4xRc/aYgOOPwyu2yZ7ZA7h/DxDHweBqedLj/XoufKzkXXXUXYYlWCwubETiPHoSIY+ZyYUCfxfIj+I/gQzOgDR6RI+ddnSyar3jL6+YA+a9YW2pay8+UyFZ6QVnY5UtgdKoMWWtc7fcq5zjG8TomXRyEh5+Lyu7v1difIGOPAeYXHY97WLAgMBAAECggEABRj9/biFtRu/PIXXotQHBy5FnJNiSEany4F9ufw2n5iguadkdKzYUykhHdFrybskYx7sFT4X2AYcXZfGw3bOB/nUAZDYt5NGdCstwaeC4704+EulUFIYmdZxr4S5vOTvhbAQF4Uv7YRipkGUmWV29HsWPjcmSG6JzgsNpEjKqNxGumMwZ3qTMO2E5ni4TvXaAB9KrIb8mL6EOk3PzwnbSlugnfJvVTC6p2F8hDCkLDIj669WKw+SJiKUxtV/2BwWUJ/uUVTFwQ8jXhiOIzhHrWRO+6BD9mQp9jxaUfmEva8zog8S72mhOJsoeaFLW2+g5ahmCm9De6IzgIJ91KCINQKBgQDColXw8rYrJLPZXyWlCg+o+Fu7RmtimcZlAy13Q1wVHej6nROEbJvAOwZXWfmFYFBwSiqQlsKGjCxxW/JHoFbJZYreW6L82dCB8yhHaTLiz4DNtOF3EzHXFmPwFnU2KJqKfVYSJrhQ3uYWiib0ef/0bcX+V9fjqHBw+SX3BEZvBQKBgQC/l3q9V3c6A0jskY8C3CysgXWYs8ENc1OpR3atnVDtGAniE/pqiAA+HDFlV9NUJiftGVkIQOXMmb6ZZ4jFMSHc8kTG/7Du80AzKVhZ9Bsfdwstgb+mby4eOVGGuzE6k4+0+oFnZNHQmpolHHWEzs4M7K/Pi/CvHD3n0j5mVdoXTwKBgGV25WCP1wHUx2FZZbGM9i77Ei8l/dNQIQoFxwz2c6mahxsnCcauK9/hpWOiRx8N38E6GMh5n30u0/hgm4RVhQjGw8c5dFVmY3lrPqNDp0BwNlCGrEc8HW5ogL7npkEOl8n8nwMlZk7adI5phPdMJm/RTjdSqfxHkh6C9BS7CNDVAoGATIywjMBKsdIoK+VIl6Ly8oXTP4zqoH4ouiUEhP+rGuAU6tCCqFfoiOho0A4UMLYCE9ih2wtbBbGUFuToH6mu1wGxezUkM4TbbNWjKGXBBIRi4e7KbSxU59yM92EJnVbh/zRryazdrBRpbFR/m+2pJD7ZS/qk0sJc9afqKKc6uT8CgYAVy17iVWnlikzWQhG5m/BK3HCbe0BcYmcmmxNfH2xgINtWNLzbw3UXVZPOSWcTAJd19rOh4+D6nppPyKm6/XcrrOdpbNewCZn1GspmWZdmNx90wC77sfWE/dMX7E5dnkjAAiij03yhB2EbW1opPYD/mlBJwPL4MSBZdPAoikL7vg=="

try:
    conn = get_snowflake_connection("test-request-id")
    print("Snowflake connection successful!")
    conn.close()
except Exception as e:
    print(f"Snowflake connection failed: {e}")
