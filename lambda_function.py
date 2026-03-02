import os
import snowflake.connector
def lambda_handler(event, context):
    try:
        conn = snowflake.connector.connect(
            user=os.environ.get('SNOWFLAKE_USER'),
            password=os.environ.get('SNOWFLAKE_PASSWORD'),
            account=os.environ.get('SNOWFLAKE_ACCOUNT'),
            warehouse=os.environ.get('SNOWFLAKE_WAREHOUSE'),
            database=os.environ.get('SNOWFLAKE_DATABASE'),
            schema=os.environ.get('SNOWFLAKE_SCHEMA')
        )
        cur = conn.cursor()
        cur.execute("SELECT CURRENT_TIMESTAMP()")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return {
            'statusCode': 200,
            'body': str(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': str(e)
        }