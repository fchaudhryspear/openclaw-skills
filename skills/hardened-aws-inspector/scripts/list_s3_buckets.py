import boto3
import json
from datetime import datetime

def list_s3_buckets():
    """
    Lists all S3 buckets with their creation date.
    This function is read-only and does not modify any resources.
    """
    try:
        s3 = boto3.client('s3')
        response = s3.list_buckets()

        buckets_summary = []
        for bucket in response['Buckets']:
            creation_date = bucket.get('CreationDate')
            if isinstance(creation_date, datetime):
                creation_date = creation_date.isoformat()

            buckets_summary.append({
                'Name': bucket.get('Name', 'N/A'),
                'CreationDate': creation_date
            })

        print(json.dumps(buckets_summary, indent=2))

    except Exception as e:
        error_message = {
            "error": "Failed to list S3 buckets.",
            "details": str(e)
        }
        print(json.dumps(error_message, indent=2))

if __name__ == "__main__":
    list_s3_buckets()
