---
name: hardened-aws-inspector
description: A secure, read-only skill for inspecting AWS resources. Use this to list or describe resources like EC2 instances, S3 buckets, IAM users, and more. This skill enforces a strict read-only security model and does not support any creation, modification, or deletion of resources.
---

# Hardened AWS Inspector

This skill provides a set of secure, read-only tools to inspect your AWS environment. It is designed with the principle of least privilege in mind.

## Security Model

- **Read-Only:** All underlying IAM permissions and scripts are strictly limited to `describe*`, `list*`, and `get*` actions.
- **No Arbitrary Commands:** This skill does not provide a generic AWS CLI pass-through. Each function is a specific, hardened script for a defined task.
- **Validated Inputs:** All function arguments are validated to prevent injection or unintended use.

## Available Tools

To use a tool, execute the corresponding script from the `scripts/` directory.

### EC2

- **List EC2 Instances**:
  ```bash
  python3 skills/hardened-aws-inspector/scripts/list_ec2_instances.py
  ```
  Returns a summary of all EC2 instances, including ID, Type, State, and Name.

### S3

- **List S3 Buckets**:
  ```bash
  python3 skills/hardened-aws-inspector/scripts/list_s3_buckets.py
  ```
  Returns a list of all S3 buckets and their creation dates.

### IAM

- **List IAM Users**:
  ```bash
  python3 skills/hardened-aws-inspector/scripts/list_iam_users.py
  ```
  Returns a list of all IAM users, including their ARN and creation date.

### Amplify

- **List Amplify Apps**:
  ```bash
  python3 skills/hardened-aws-inspector/scripts/list_amplify_apps.py
  ```
  Returns a list of all AWS Amplify apps and their details.
