"""
Real-Time Data Lake — Webhook Ingestion Handler
================================================
Receives loan application webhooks from partner APIs,
validates the payload, stores raw data in S3, and triggers
downstream processing (data quality, DynamoDB, Snowflake).

@module WebhookHandler
@version 2.1.0
"""

import json
import os
import logging
import uuid
from datetime import datetime
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# ── Configuration (no magic numbers) ─────────────────────────────────────
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
S3_BUCKET = os.environ.get("S3_BUCKET", "prod-lending-data-lake")
S3_PREFIX = os.environ.get("S3_PREFIX", "raw/")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "real-time-data-lake-loan-applications")
IDEMPOTENCY_TABLE = os.environ.get("IDEMPOTENCY_TABLE", "real-time-data-lake-idempotency-keys")
IDEMPOTENCY_TTL_HOURS = 24
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGIN", "https://missioncontrol.credologi.com").split(",")
MAX_PAYLOAD_SIZE_BYTES = 1_048_576  # 1 MB

# ── Structured logging ───────────────────────────────────────────────────
logger = logging.getLogger("webhook")
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

# ── AWS Clients ──────────────────────────────────────────────────────────
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)
idempotency = dynamodb.Table(IDEMPOTENCY_TABLE)

# ── CORS Headers ─────────────────────────────────────────────────────────
def cors_headers(origin=None):
    """Build CORS headers. Only allow configured origins."""
    allowed = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
    return {
        "Access-Control-Allow-Origin": allowed,
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Api-Key",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
        "Content-Type": "application/json",
    }


def json_response(status_code, body, origin=None):
    """Build a standard JSON response."""
    return {
        "statusCode": status_code,
        "headers": cors_headers(origin),
        "body": json.dumps(body, default=str),
    }


def audit_log(action, source, record_id=None, metadata=None):
    """Structured audit log — never logs PII/loan data."""
    logger.info(json.dumps({
        "type": "AUDIT",
        "action": action,
        "source": source,
        "record_id": record_id,
        "metadata": metadata or {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }))


def check_idempotency(key):
    """Check if this request was already processed."""
    try:
        response = idempotency.get_item(Key={"idempotency_key": key})
        return response.get("Item") is not None
    except ClientError as e:
        logger.warning(f"Idempotency check failed: {e.response['Error']['Code']}")
        return False


def record_idempotency(key, result):
    """Record that this request was processed."""
    try:
        ttl = int(datetime.utcnow().timestamp()) + (IDEMPOTENCY_TTL_HOURS * 3600)
        idempotency.put_item(Item={
            "idempotency_key": key,
            "result": result,
            "ttl": ttl,
            "created_at": datetime.utcnow().isoformat() + "Z",
        })
    except ClientError as e:
        logger.warning(f"Idempotency record failed: {e.response['Error']['Code']}")


def validate_payload(body):
    """Validate webhook payload. Returns (is_valid, errors)."""
    errors = []
    if not isinstance(body, dict):
        return False, ["Payload must be a JSON object"]
    
    required_fields = ["application_id", "loan_type", "status"]
    for field in required_fields:
        if field not in body:
            errors.append(f"Missing required field: {field}")
    
    # Validate monetary fields use proper types
    for money_field in ["loan_amount", "monthly_payment", "interest_rate"]:
        if money_field in body and body[money_field] is not None:
            try:
                Decimal(str(body[money_field]))
            except Exception:
                errors.append(f"Invalid numeric value for {money_field}")
    
    return len(errors) == 0, errors


def lambda_handler(event, context):
    """Main webhook handler."""
    # CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return json_response(200, {"message": "OK"})
    
    origin = event.get("headers", {}).get("Origin") or event.get("headers", {}).get("origin")
    
    try:
        # Parse body
        raw_body = event.get("body", "")
        if not raw_body:
            return json_response(400, {"error": "Empty request body"}, origin)
        
        # Size check
        if len(raw_body) > MAX_PAYLOAD_SIZE_BYTES:
            return json_response(413, {"error": "Payload too large"}, origin)
        
        body = json.loads(raw_body)
        
        # Validate
        is_valid, errors = validate_payload(body)
        if not is_valid:
            return json_response(400, {"error": "Validation failed", "details": errors}, origin)
        
        # Idempotency check
        idempotency_key = body.get("application_id", str(uuid.uuid4()))
        if check_idempotency(idempotency_key):
            audit_log("DUPLICATE_WEBHOOK", "api", idempotency_key)
            return json_response(200, {"message": "Already processed", "id": idempotency_key}, origin)
        
        # Generate record ID
        record_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Store raw payload in S3 (data lake raw layer)
        s3_key = f"{S3_PREFIX}{datetime.utcnow().strftime('%Y/%m/%d')}/{record_id}.json"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps({**body, "_metadata": {
                "record_id": record_id,
                "ingested_at": timestamp,
                "source": "webhook",
            }}, default=str),
            ContentType="application/json",
            ServerSideEncryption="aws:kms",  # SSE-KMS encryption at rest
        )
        
        # Store in DynamoDB for quick access
        table.put_item(Item={
            "application_id": idempotency_key,
            "record_id": record_id,
            "loan_type": body.get("loan_type", "unknown"),
            "status": body.get("status", "received"),
            "s3_key": s3_key,
            "ingested_at": timestamp,
            "updated_at": timestamp,
            # Use Decimal for monetary values
            **{k: Decimal(str(v)) for k, v in body.items() 
               if k in ("loan_amount", "monthly_payment", "interest_rate") and v is not None},
        })
        
        # Record idempotency
        record_idempotency(idempotency_key, "success")
        
        # Audit log (no PII — just metadata)
        audit_log("WEBHOOK_RECEIVED", "api", idempotency_key, {
            "record_id": record_id,
            "loan_type": body.get("loan_type"),
            "s3_key": s3_key,
        })
        
        return json_response(200, {
            "message": "Received",
            "record_id": record_id,
            "s3_key": s3_key,
        }, origin)
        
    except json.JSONDecodeError:
        return json_response(400, {"error": "Invalid JSON"}, origin)
    except ClientError as e:
        logger.error(json.dumps({
            "type": "AWS_ERROR",
            "service": e.response["Error"].get("Code"),
            "message": e.response["Error"].get("Message"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }))
        return json_response(500, {"error": "Internal error"}, origin)
    except Exception as e:
        logger.error(json.dumps({
            "type": "UNHANDLED_ERROR",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }))
        return json_response(500, {"error": "Internal error"}, origin)
