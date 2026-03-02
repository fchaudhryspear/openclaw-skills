import psycopg2
import json
import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

def get_secret():
    """Retrieve secrets from AWS Secrets Manager."""
    secret_name = "/streamlit/irr_tool/db_credentials"  # IMPORTANT: Match this with your AWS Secret name
    region_name = os.getenv("AWS_REGION", "us-east-1") # Or your preferred AWS region

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        # For a production app, you'd want more robust error handling
        print(f"Error retrieving secret '{secret_name}': {e}")
        # Fallback for local development or if secret is not found (use carefully)
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "dbname": os.getenv("DB_NAME", "scenarios_db"),
            "user": os.getenv("DB_USER", "user"),
            "password": os.getenv("DB_PASSWORD", "password")
        }
    else:
        if 'SecretString' in get_secret_value_response:
            return json.loads(get_secret_value_response['SecretString'])
        else:
            # Decode binary secret if it's not a string
            return json.loads(get_secret_value_response['SecretBinary'].decode('utf-8'))

def get_db_connection():
    """Establishes and returns a PostgreSQL database connection using secrets."""
    secrets = get_secret()
    conn = psycopg2.connect(
        dbname=secrets['dbname'],
        user=secrets['user'],
        password=secrets['password'],
        host=secrets['host'],
        port=secrets['port']
    )
    return conn

def init_db():
    """Initializes the PostgreSQL database table if it doesn't exist."""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS scenarios (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                customer_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                parameters JSONB NOT NULL,
                results JSONB NOT NULL
            )
        ''')
        conn.commit()
    except Exception as e:
        print(f"Error initializing database: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def save_scenario(name: str, customer_name: str, params: dict, results: dict):
    """Saves a financial scenario to the PostgreSQL database."""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO scenarios (name, customer_name, parameters, results)
            VALUES (%s, %s, %s, %s)
        ''', (name, customer_name, json.dumps(params), json.dumps(results)))
        conn.commit()
    except Exception as e:
        print(f"Error saving scenario '{name}': {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def load_scenarios():
    """Loads all saved scenarios from the PostgreSQL database."""
    conn = None
    scenarios = []
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT id, name, customer_name, created_at FROM scenarios ORDER BY created_at DESC')
        scenarios = c.fetchall()
    except Exception as e:
        print(f"Error loading scenarios: {e}")
    finally:
        if conn:
            conn.close()
    return scenarios

def get_scenario(scenario_id: int):
    """Retrieves a specific scenario by ID from the PostgreSQL database."""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT parameters, results FROM scenarios WHERE id = %s', (scenario_id,))
        result = c.fetchone()
        if result:
            return json.loads(result[0]), json.loads(result[1])
    except Exception as e:
        print(f"Error retrieving scenario {scenario_id}: {e}")
    finally:
        if conn:
            conn.close()
    return None, None

def delete_scenario(scenario_id: int):
    """Deletes a scenario by ID from the PostgreSQL database."""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM scenarios WHERE id = %s', (scenario_id,))
        conn.commit()
    except Exception as e:
        print(f"Error deleting scenario {scenario_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
