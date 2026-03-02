import os
import snowflake.connector
import json

def list_databases():
    """
    Connects to Snowflake and lists all available databases.
    Reads connection details from environment variables.
    """
    try:
        # Fetch credentials from environment variables
        user = os.getenv('SNOWFLAKE_USER')
        password = os.getenv('SNOWFLAKE_PASSWORD')
        account = os.getenv('SNOWFLAKE_ACCOUNT')
        warehouse = os.getenv('SNOWFLAKE_WAREHOUSE')
        database = os.getenv('SNOWFLAKE_DATABASE')
        role = os.getenv('SNOWFLAKE_ROLE')

        # Basic validation
        if not all([user, password, account]):
            raise ValueError("SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, and SNOWFLAKE_ACCOUNT environment variables must be set.")

        # Establish connection
        conn = snowflake.connector.connect(
            user=user,
            password=password,
            account=account,
            warehouse=warehouse,
            database=database,
            role=role
        )

        # Execute a read-only query
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        
        databases = [row[1] for row in cursor.fetchall()]

        print(json.dumps({"databases": databases}, indent=2))

    except Exception as e:
        error_message = {
            "error": "Failed to list Snowflake databases.",
            "details": str(e)
        }
        print(json.dumps(error_message, indent=2))
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()
        if 'conn' in locals() and conn is not None:
            conn.close()

if __name__ == "__main__":
    list_databases()
