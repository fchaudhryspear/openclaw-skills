import boto3
import json
from datetime import datetime

def list_amplify_apps():
    """
    Lists all AWS Amplify apps.
    This function is read-only and does not modify any resources.
    """
    try:
        amplify = boto3.client('amplify')
        response = amplify.list_apps()

        apps_summary = []
        for app in response['apps']:
            create_time = app.get('createTime')
            update_time = app.get('updateTime')

            if isinstance(create_time, datetime):
                create_time = create_time.isoformat()
            if isinstance(update_time, datetime):
                update_time = update_time.isoformat()

            apps_summary.append({
                'name': app.get('name', 'N/A'),
                'appId': app.get('appId', 'N/A'),
                'appArn': app.get('appArn', 'N/A'),
                'defaultDomain': app.get('defaultDomain', 'N/A'),
                'platform': app.get('platform', 'N/A'),
                'createTime': create_time,
                'updateTime': update_time
            })

        print(json.dumps(apps_summary, indent=2))

    except Exception as e:
        error_message = {
            "error": "Failed to list Amplify apps.",
            "details": str(e)
        }
        print(json.dumps(error_message, indent=2))

if __name__ == "__main__":
    list_amplify_apps()
