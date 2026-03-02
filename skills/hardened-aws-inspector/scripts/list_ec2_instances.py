import boto3
import json

def list_ec2_instances():
    """
    Lists all EC2 instances in a summary format.
    This function is read-only and does not modify any resources.
    """
    try:
        ec2 = boto3.client('ec2')
        response = ec2.describe_instances()

        instances_summary = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance.get('InstanceId', 'N/A')
                instance_type = instance.get('InstanceType', 'N/A')
                state = instance.get('State', {}).get('Name', 'N/A')
                
                # Get the 'Name' tag if it exists
                name_tag = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'N/A')

                instances_summary.append({
                    'InstanceId': instance_id,
                    'Name': name_tag,
                    'Type': instance_type,
                    'State': state
                })

        # Print the summary as a JSON array for easy parsing
        print(json.dumps(instances_summary, indent=2))

    except Exception as e:
        error_message = {
            "error": "Failed to list EC2 instances.",
            "details": str(e)
        }
        print(json.dumps(error_message, indent=2))

if __name__ == "__main__":
    list_ec2_instances()
