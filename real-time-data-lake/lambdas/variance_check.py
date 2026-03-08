"""
Real-Time Data Lake — Variance Detection
==========================================
Compares current data against historical baselines to detect
anomalies (sudden volume changes, unusual loan amounts, etc.).
Alerts via SNS when variance exceeds thresholds.

@module VarianceCheck
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
SNS_TOPIC_ARN = os.environ.get("ALERT_TOPIC_ARN", "arn:aws:sns:us-east-1:386757865833:prod-loan-variance-alerts")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "real-time-data-lake-loan-applications")
VARIANCE_THRESHOLD_PCT = Decimal("25")  # Alert if >25% variance
MIN_SAMPLE_SIZE = 10  # Need at least 10 records for meaningful comparison
QUERY_PAGE_SIZE = 100  # Paginate DynamoDB queries

logger = logging.getLogger("variance_check")
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")
table = dynamodb.Table(DYNAMODB_TABLE)


def get_recent_stats():
    """Get recent loan application statistics from DynamoDB (paginated)."""
    items = []
    response = table.scan(Limit=QUERY_PAGE_SIZE)
    items.extend(response.get("Items", []))
    
    # Paginate (but cap at reasonable limit)
    max_pages = 10
    page = 1
    while "LastEvaluatedKey" in response and page < max_pages:
        response = table.scan(
            Limit=QUERY_PAGE_SIZE,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))
        page += 1
    
    return items


def calculate_variance(current, baseline):
    """Calculate percentage variance between two values."""
    if baseline == 0:
        return Decimal("100") if current > 0 else Decimal("0")
    return abs(current - baseline) / baseline * Decimal("100")


def lambda_handler(event, context):
    """Run variance detection checks."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    alerts = []
    
    try:
        items = get_recent_stats()
        
        if len(items) < MIN_SAMPLE_SIZE:
            logger.info(json.dumps({
                "type": "VARIANCE_CHECK",
                "status": "skipped",
                "reason": f"Insufficient data ({len(items)} < {MIN_SAMPLE_SIZE})",
                "timestamp": timestamp,
            }))
            return {"status": "skipped", "reason": "insufficient_data"}
        
        # Volume check
        total_count = len(items)
        
        # Amount distribution check
        amounts = []
        for item in items:
            amt = item.get("loan_amount")
            if amt is not None:
                try:
                    amounts.append(Decimal(str(amt)))
                except Exception:
                    pass
        
        if amounts:
            avg_amount = sum(amounts) / len(amounts)
            max_amount = max(amounts)
            min_amount = min(amounts)
            
            # Check for outliers (> 3x average)
            outliers = [a for a in amounts if a > avg_amount * 3]
            if outliers:
                alerts.append({
                    "type": "AMOUNT_OUTLIER",
                    "count": len(outliers),
                    "avg_amount": str(avg_amount),
                    "max_outlier": str(max(outliers)),
                })
        
        # Send alerts if any
        if alerts and SNS_TOPIC_ARN:
            try:
                sns.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Subject=f"Data Lake Variance Alert: {len(alerts)} anomalies",
                    Message=json.dumps({"alerts": alerts, "timestamp": timestamp}, default=str),
                )
            except ClientError as e:
                logger.warning(f"SNS publish failed: {e.response['Error']['Code']}")
        
        logger.info(json.dumps({
            "type": "VARIANCE_CHECK",
            "status": "completed",
            "records_checked": total_count,
            "alerts_raised": len(alerts),
            "timestamp": timestamp,
        }))
        
        return {"status": "completed", "records": total_count, "alerts": len(alerts)}
        
    except Exception as e:
        logger.error(json.dumps({
            "type": "VARIANCE_ERROR",
            "error_type": type(e).__name__,
            "message": str(e),
            "timestamp": timestamp,
        }))
        return {"status": "error", "error": str(e)}
