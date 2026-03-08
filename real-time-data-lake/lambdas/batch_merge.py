"""
Real-Time Data Lake — Batch Merge to Snowflake
================================================
Periodically merges validated records from S3 into Snowflake
warehouse tables. Uses COPY INTO for efficient bulk loading.

@module BatchMerge
@version 2.1.0
"""

import json
import os
import logging
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

# ── Configuration ────────────────────────────────────────────────────
SNOWFLAKE_SECRET_ID = os.environ.get("SNOWFLAKE_SECRET_ID", "snowflake-lambda-key")
SNOWFLAKE_WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
SNOWFLAKE_DATABASE = os.environ.get("SNOWFLAKE_DATABASE", "LENDING_LAKE")
SNOWFLAKE_SCHEMA = os.environ.get("SNOWFLAKE_SCHEMA", "RAW")
S3_BUCKET = os.environ.get("S3_BUCKET", "prod-lending-data-lake")
BATCH_SIZE = 1000
MERGE_TIMEOUT_SECONDS = 300

logger = logging.getLogger("batch_merge")
logger.setLevel(logging.INFO)

secrets = boto3.client("secretsmanager")

# Connection cache for Lambda warm starts
_sf_conn = None


def get_snowflake_connection():
    """Get or create Snowflake connection using Secrets Manager."""
    global _sf_conn
    if _sf_conn is not None:
        try:
            _sf_conn.cursor().execute("SELECT 1")
            return _sf_conn
        except Exception:
            _sf_conn = None
    
    try:
        import snowflake.connector
        secret = secrets.get_secret_value(SecretId=SNOWFLAKE_SECRET_ID)
        creds = json.loads(secret["SecretString"])
        
        _sf_conn = snowflake.connector.connect(
            account=creds["account"],
            user=creds["user"],
            password=creds["password"],
            warehouse=SNOWFLAKE_WAREHOUSE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
            login_timeout=30,
            network_timeout=MERGE_TIMEOUT_SECONDS,
        )
        return _sf_conn
    except ClientError as e:
        logger.error(json.dumps({"type": "SECRET_ERROR", "error": e.response["Error"]["Code"]}))
        raise
    except ImportError:
        logger.error("snowflake-connector-python not installed")
        raise


def lambda_handler(event, context):
    """Merge validated S3 records into Snowflake."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        
        # Use COPY INTO for efficient bulk load (parameterized — no SQL injection)
        copy_sql = """
            COPY INTO loan_applications
            FROM @lending_stage/validated/
            FILE_FORMAT = (TYPE = JSON)
            PATTERN = '.*\\.json'
            ON_ERROR = 'CONTINUE'
        """
        
        cursor.execute(copy_sql)
        result = cursor.fetchone()
        rows_loaded = result[0] if result else 0
        
        logger.info(json.dumps({
            "type": "BATCH_MERGE",
            "rows_loaded": rows_loaded,
            "warehouse": SNOWFLAKE_WAREHOUSE,
            "timestamp": timestamp,
        }))
        
        return {"status": "success", "rows_loaded": rows_loaded, "timestamp": timestamp}
        
    except Exception as e:
        logger.error(json.dumps({
            "type": "MERGE_ERROR",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": timestamp,
        }))
        return {"status": "error", "error": str(e)}
