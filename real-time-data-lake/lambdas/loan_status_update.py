"""
Real-Time Data Lake — Loan Status Update Handler
==================================================
Processes loan status change events from SQS queue.
Updates DynamoDB record and triggers downstream notifications.

@module LoanStatusUpdate
@version 2.1.0
"""

import json
import os
import logging
from datetime import datetime
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# ── Configuration ────────────────────────────────────────────────────
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "real-time-data-lake-loan-applications")
SNS_TOPIC_ARN = os.environ.get("ALERT_TOPIC_ARN", "")
VALID_STATUSES = {"received", "processing", "approved", "denied", "funded", "closed"}

logger = logging.getLogger("loan_status")
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)
sns = boto3.client("sns")


def lambda_handler(event, context):
    """Process SQS loan status update messages."""
    processed = 0
    failed = 0
    
    for record in event.get("Records", []):
        try:
            body = json.loads(record.get("body", "{}"))
            app_id = body.get("application_id")
            new_status = body.get("status", "").lower()
            
            if not app_id:
                logger.warning(json.dumps({"type": "MISSING_APP_ID", "body_keys": list(body.keys())}))
                failed += 1
                continue
            
            if new_status and new_status not in VALID_STATUSES:
                logger.warning(json.dumps({"type": "INVALID_STATUS", "status": new_status, "app_id": app_id}))
                failed += 1
                continue
            
            # Update DynamoDB
            update_expr = "SET #s = :status, updated_at = :ts"
            expr_values = {
                ":status": new_status or "unknown",
                ":ts": datetime.utcnow().isoformat() + "Z",
            }
            expr_names = {"#s": "status"}
            
            # Add monetary fields if present (use Decimal)
            for field in ["loan_amount", "monthly_payment"]:
                if field in body and body[field] is not None:
                    update_expr += f", {field} = :{field}"
                    expr_values[f":{field}"] = Decimal(str(body[field]))
            
            table.update_item(
                Key={"application_id": app_id},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
                ExpressionAttributeNames=expr_names,
            )
            
            # Log (no PII)
            logger.info(json.dumps({
                "type": "STATUS_UPDATE",
                "application_id": app_id,
                "new_status": new_status,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }))
            
            processed += 1
            
        except ClientError as e:
            logger.error(json.dumps({
                "type": "DYNAMO_ERROR",
                "error": e.response["Error"]["Code"],
            }))
            failed += 1
        except Exception as e:
            logger.error(json.dumps({
                "type": "PROCESSING_ERROR",
                "error_type": type(e).__name__,
                "message": str(e),
            }))
            failed += 1
    
    return {"processed": processed, "failed": failed}
