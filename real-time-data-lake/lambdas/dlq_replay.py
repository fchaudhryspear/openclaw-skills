"""
Real-Time Data Lake — Dead Letter Queue Replay
================================================
Replays failed messages from the DLQ back to the main queue
for reprocessing. Implements exponential backoff.

@module DLQReplay
@version 2.1.0
"""

import json
import os
import logging
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

# ── Configuration ────────────────────────────────────────────────────
MAIN_QUEUE_URL = os.environ.get("MAIN_QUEUE_URL", "")
DLQ_URL = os.environ.get("DLQ_URL", "")
MAX_REPLAY_BATCH = 10
MAX_REPLAY_ATTEMPTS = 3

logger = logging.getLogger("dlq_replay")
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")


def lambda_handler(event, context):
    """Replay messages from DLQ to main queue."""
    if not MAIN_QUEUE_URL or not DLQ_URL:
        logger.error("Queue URLs not configured")
        return {"status": "error", "reason": "missing_config"}
    
    replayed = 0
    dropped = 0
    
    try:
        response = sqs.receive_message(
            QueueUrl=DLQ_URL,
            MaxNumberOfMessages=MAX_REPLAY_BATCH,
            WaitTimeSeconds=5,
        )
        
        messages = response.get("Messages", [])
        
        for msg in messages:
            body = json.loads(msg.get("Body", "{}"))
            replay_count = int(body.get("_replay_count", 0))
            
            if replay_count >= MAX_REPLAY_ATTEMPTS:
                # Too many retries — drop and log
                logger.warning(json.dumps({
                    "type": "DLQ_DROP",
                    "message_id": msg["MessageId"],
                    "replay_count": replay_count,
                }))
                dropped += 1
            else:
                # Replay with incremented counter
                body["_replay_count"] = replay_count + 1
                try:
                    sqs.send_message(
                        QueueUrl=MAIN_QUEUE_URL,
                        MessageBody=json.dumps(body, default=str),
                    )
                    replayed += 1
                except ClientError as e:
                    logger.error(json.dumps({
                        "type": "REPLAY_ERROR",
                        "message_id": msg["MessageId"],
                        "error": e.response["Error"]["Code"],
                    }))
                    continue
            
            # Delete from DLQ
            try:
                sqs.delete_message(QueueUrl=DLQ_URL, ReceiptHandle=msg["ReceiptHandle"])
            except ClientError:
                pass
        
        logger.info(json.dumps({
            "type": "DLQ_REPLAY",
            "processed": len(messages),
            "replayed": replayed,
            "dropped": dropped,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }))
        
        return {"processed": len(messages), "replayed": replayed, "dropped": dropped}
        
    except Exception as e:
        logger.error(json.dumps({
            "type": "DLQ_ERROR",
            "error_type": type(e).__name__,
            "message": str(e),
        }))
        return {"status": "error", "error": str(e)}
