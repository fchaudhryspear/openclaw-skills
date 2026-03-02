#!/usr/bin/env python3
"""
AWS Security Audit Script
Checks for unauthorized activities since credential exposure
"""

import boto3
from datetime import datetime, timedelta
import json
import sys

def audit_cloudtrail(hours=24):
    """Check CloudTrail for suspicious activities in last N hours"""
    print("🔍 Auditing AWS CloudTrail...")
    
    client = boto3.client('cloudtrail')
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    # Look for high-risk events
    risk_events = [
        'CreateUser', 'CreateAccessKey', 'AttachUserPolicy',
        'PutUserPolicy', 'CreateRole', 'AssumeRole',
        'CreateBucket', 'DeleteBucket', 'PutBucketPolicy',
        'CreateFunction', 'UpdateFunctionCode',
        'RunInstances', 'TerminateInstances',
        'CreateTopic', 'CreateQueue'
    ]
    
    suspicious = []
    try:
        for event_name in risk_events:
            response = client.lookup_events(
                LookupAttributes=[
                    {'AttributeKey': 'EventName', 'AttributeValue': event_name}
                ],
                StartTime=start_time,
                EndTime=end_time,
                MaxResults=50
            )
            
            for event in response.get('Events', []):
                suspicious.append({
                    'time': event['EventTime'].isoformat(),
                    'event': event_name,
                    'user': event.get('Username', 'Unknown'),
                    'source_ip': event.get('SourceIPAddress', 'Unknown'),
                    'resource': event.get('Resources', [])
                })
        
        if suspicious:
            print(f"\n⚠️  FOUND {len(suspicious)} HIGH-RISK EVENTS:")
            print("-" * 60)
            for event in sorted(suspicious, key=lambda x: x['time']):
                print(f"  [{event['time']}] {event['event']}")
                print(f"    User: {event['user']}, IP: {event['source_ip']}")
                print()
        else:
            print("✅ No suspicious high-risk events found")
            
    except Exception as e:
        print(f"❌ Error querying CloudTrail: {e}")
        print("Make sure you have CloudTrail enabled and proper permissions")


def audit_ec2_instances():
    """Check for unexpected EC2 instances"""
    print("\n🔍 Auditing EC2 Instances...")
    
    ec2 = boto3.client('ec2')
    try:
        response = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        
        unexpected = []
        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                # Check for crypto mining or suspicious AMIs
                if any(keyword in str(instance).lower() for keyword in ['mining', 'bitcoin', 'crypto']):
                    unexpected.append(instance['InstanceId'])
                
        if unexpected:
            print(f"⚠️  Found {len(unexpected)} potentially suspicious instances:")
            for iid in unexpected:
                print(f"  - {iid}")
        else:
            print("✅ No obviously suspicious EC2 instances found")
            
    except Exception as e:
        print(f"❌ Error checking EC2: {e}")


def audit_iam_users():
    """Check for new IAM users"""
    print("\n🔍 Auditing IAM Users...")
    
    iam = boto3.client('iam')
    try:
        response = iam.list_users(MaxItems=100)
        
        for user in response.get('Users', []):
            age_days = (datetime.now(user['CreateDate'].tzinfo) - user['CreateDate']).days
            if age_days <= 7:
                print(f"⚠️  NEW USER CREATED (< 7 days old): {user['UserName']}")
                print(f"   Created: {user['CreateDate']}")
                print()
        
        print("✅ IAM user audit complete")
            
    except Exception as e:
        print(f"❌ Error checking IAM: {e}")


def audit_s3_buckets():
    """Check for public S3 buckets"""
    print("\n🔍 Auditing S3 Buckets...")
    
    s3 = boto3.client('s3')
    try:
        response = s3.list_buckets()
        
        public_buckets = []
        for bucket in response.get('Buckets', []):
            name = bucket['Name']
            try:
                acl = s3.get_bucket_acl(Bucket=name)
                grants = [g['Grantee'].get('URI') for g in acl.get('Grants', [])]
                if 'http://acs.amazonaws.com/groups/global/AllUsers' in grants:
                    public_buckets.append(name)
            except:
                pass
        
        if public_buckets:
            print(f"⚠️  FOUND PUBLIC BUCKETS:")
            for bucket in public_buckets:
                print(f"  - {bucket}")
        else:
            print("✅ No publicly accessible S3 buckets found")
            
    except Exception as e:
        print(f"❌ Error checking S3: {e}")


def audit_billing():
    """Check for unusual billing spikes"""
    print("\n🔍 Checking AWS Billing (last 7 days)...")
    
    ce = boto3.client('ce')
    try:
        end = datetime.utcnow().strftime('%Y-%m-%d')
        start = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        response = ce.get_cost_and_usage(
            TimePeriod={'Start': start, 'End': end},
            Granularity='DAILY',
            Metrics=['UnblendedCost']
        )
        
        total = sum(
            float(r.get('Metrics', {}).get('UnblendedCost', {}).get('Amount', 0))
            for r in response.get('ResultsByTime', [])
        )
        
        print(f"💰 Total spending (last 7 days): ${total:.2f}")
        if total > 100:
            print("⚠️  WARNING: Spending exceeds $100 - investigate immediately!")
        else:
            print("✅ Spending within normal range")
            
    except Exception as e:
        print(f"❌ Error checking billing: {e}")


if __name__ == '__main__':
    print("=" * 70)
    print("AWS SECURITY AUDIT - POST COMPROMISE CHECK")
    print("=" * 70)
    print()
    
    audit_cloudtrail(hours=48)
    audit_ec2_instances()
    audit_iam_users()
    audit_s3_buckets()
    audit_billing()
    
    print()
    print("=" * 70)
    print("AUDIT COMPLETE")
    print("=" * 70)
