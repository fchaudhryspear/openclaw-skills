"""
Real-Time Data Lake — Data Quality Check
=========================================
Validates ingested loan data against business rules before
forwarding to Snowflake. Triggered by S3 put events.

@module DataQualityCheck
@version 2.1.0
"""

import json
import os
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

import boto3
from botocore.exceptions import ClientError

# ── Configuration ────────────────────────────────────────────────────
S3_BUCKET = os.environ.get("S3_BUCKET", "prod-lending-data-lake")
QUALITY_PREFIX = "validated/"
REJECTED_PREFIX = "rejected/"
SNS_TOPIC = os.environ.get("ALERT_TOPIC_ARN", "")

MIN_LOAN_AMOUNT = Decimal("1000")
MAX_LOAN_AMOUNT = Decimal("50000000")
VALID_LOAN_TYPES = {"conventional", "fha", "va", "jumbo", "construction", "heloc", "personal"}
VALID_STATUSES = {"received", "processing", "approved", "denied", "funded", "closed"}

logger = logging.getLogger("data_quality")
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
sns = boto3.client("sns")


def validate_record(record):
    """Run data quality checks on a loan record."""
    issues = []
    
    # Required fields
    for field in ["application_id", "loan_type", "status"]:
        if not record.get(field):
            issues.append({"field": field, "issue": "missing_required"})
    
    # Loan type validation
    loan_type = (record.get("loan_type") or "").lower()
    if loan_type and loan_type not in VALID_LOAN_TYPES:
        issues.append({"field": "loan_type", "issue": f"invalid_value: {loan_type}"})
    
    # Status validation
    status = (record.get("status") or "").lower()
    if status and status not in VALID_STATUSES:
        issues.append({"field": "status", "issue": f"invalid_value: {status}"})
    
    # Monetary validation
    loan_amount = record.get("loan_amount")
    if loan_amount is not None:
        try:
            amount = Decimal(str(loan_amount))
            if amount < MIN_LOAN_AMOUNT or amount > MAX_LOAN_AMOUNT:
                issues.append({"field": "loan_amount", "issue": f"out_of_range: {amount}"})
        except (InvalidOperation, TypeError):
            issues.append({"field": "loan_amount", "issue": "invalid_decimal"})
    
    return len(issues) == 0, issues


def lambda_handler(event, context):
    """Process S3 events for data quality checks."""
    processed = 0
    rejected = 0
    
    for s3_event in event.get("Records", []):
        bucket = s3_event["s3"]["bucket"]["name"]
        key = s3_event["s3"]["object"]["key"]
        
        try:
            # Read the raw record
            response = s3.get_object(Bucket=bucket, Key=key)
            record = json.loads(response["Body"].read().decode("utf-8"))
            
            is_valid, issues = validate_record(record)
            
            if is_valid:
                # Move to validated prefix
                validated_key = key.replace("raw/", QUALITY_PREFIX, 1)
                record["_quality"] = {"passed": True, "checked_at": datetime.utcnow().isoformat() + "Z"}
                s3.put_object(
                    Bucket=bucket, Key=validated_key,
                    Body=json.dumps(record, default=str),
                    ContentType="application/json",
                    ServerSideEncryption="aws:kms",
                )
                processed += 1
            else:
                # Move to rejected prefix
                rejected_key = key.replace("raw/", REJECTED_PREFIX, 1)
                record["_quality"] = {"passed": False, "issues": issues, "checked_at": datetime.utcnow().isoformat() + "Z"}
                s3.put_object(
                    Bucket=bucket, Key=rejected_key,
                    Body=json.dumps(record, default=str),
                    ContentType="application/json",
                )
                rejected += 1
                
                # Alert on rejections
                if SNS_TOPIC:
                    try:
                        sns.publish(
                            TopicArn=SNS_TOPIC,
                            Subject="Data Quality Alert: Record Rejected",
                            Message=json.dumps({
                                "record_id": record.get("_metadata", {}).get("record_id", "unknown"),
                                "issues": issues,
                                "s3_key": key,
                            }),
                        )
                    except ClientError:
                        logger.warning("Failed to send SNS alert")
            
            logger.info(json.dumps({
                "type": "QUALITY_CHECK",
                "s3_key": key,
                "passed": is_valid,
                "issues_count": len(issues),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }))
            
        except ClientError as e:
            logger.error(json.dumps({
                "type": "AWS_ERROR",
                "s3_key": key,
                "error": e.response["Error"]["Code"],
            }))
        except json.JSONDecodeError:
            logger.error(json.dumps({"type": "PARSE_ERROR", "s3_key": key}))
    
    return {"processed": processed, "rejected": rejected}
