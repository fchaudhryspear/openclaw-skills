import boto3
import json
from datetime import datetime

def list_iam_users():
    """
    Lists all IAM users with their creation date.
    This function is read-only and does not modify any resources.
    """
    try:
        iam = boto3.client('iam')
        # Use the paginator to handle accounts with many users
        paginator = iam.get_paginator('list_users')
        pages = paginator.paginate()

        users_summary = []
        for page in pages:
            for user in page['Users']:
                create_date = user.get('CreateDate')
                if isinstance(create_date, datetime):
                    create_date = create_date.isoformat()
                
                users_summary.append({
                    'UserName': user.get('UserName', 'N/A'),
                    'UserId': user.get('UserId', 'N/A'),
                    'Arn': user.get('Arn', 'N/A'),
                    'CreateDate': create_date
                })

        print(json.dumps(users_summary, indent=2))

    except Exception as e:
        error_message = {
            "error": "Failed to list IAM users.",
            "details": str(e)
        }
        print(json.dumps(error_message, indent=2))

if __name__ == "__main__":
    list_iam_users()
