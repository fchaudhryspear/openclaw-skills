---
name: hardened-snowflake-connector
description: A secure, read-only skill for inspecting a Snowflake data warehouse. Use this to list databases, schemas, tables, and run pre-defined, safe queries. This skill enforces a strict read-only security model.
---

# Hardened Snowflake Connector

This skill provides a set of secure, read-only tools to inspect your Snowflake environment. It is designed with the principle of least privilege in mind and uses a self-contained Python virtual environment.

## Security Model

- **Read-Only:** All Snowflake queries are strictly limited to non-destructive, read-only operations (e.g., `SHOW`, `SELECT`). The Snowflake user configured should have read-only permissions.
- **No Arbitrary Queries:** This skill does not provide a generic query pass-through. Each function is a specific, hardened script for a defined task.
- **Credential Management:** The skill requires Snowflake credentials to be set as environment variables. They are not stored in the skill's code.

## Setup

Before using any tools, you must export the following environment variables:

```bash
export SNOWFLAKE_USER="your_user"
export SNOWFLAKE_PASSWORD="your_password"
export SNOWFLAKE_ACCOUNT="your_account_identifier"
# Optional:
export SNOWFLAKE_WAREHOUSE="your_warehouse"
export SNOWFLAKE_DATABASE="your_database"
export SNOWFLAKE_ROLE="your_role"
```

## Execution Environment

This skill uses a dedicated Python virtual environment to manage its dependencies without affecting your system. **All scripts must be run using the Python interpreter located in the skill's `venv/bin/` directory.**

## Available Tools

### Databases

- **List Databases**:
  ```bash
  skills/hardened-snowflake-connector/venv/bin/python3 skills/hardened-snowflake-connector/scripts/list_databases.py
  ```
  Returns a list of all databases accessible by the configured user.
