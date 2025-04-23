from airflow import DAG
from airflow.models import Variable
from airflow.decorators import task
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
from datetime import datetime
import requests
import pandas as pd
import io

# -----------------------------
# EXTRACT TASK
# -----------------------------
@task
def extract_data(url):
    response = requests.get(url)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text))
    print(f"Extracted {len(df)} rows from CSV.")
    return df.to_dict(orient='records')

# -----------------------------
# TRANSFORM TASK
# -----------------------------
@task
def transform_data(raw_data):
    df = pd.DataFrame(raw_data)

    # Convert datetime fields
    datetime_cols = ['received_datetime', 'enroute_datetime', 'dispatch_datetime', 'onscene_datetime']
    for col in datetime_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # Filter and keep required columns
    df = df[['id', 'cad_number', 'received_datetime', 'dispatch_datetime',
             'onscene_datetime', 'police_district', 'enroute_datetime']]
    
    # Drop rows with missing critical values
    df = df.dropna(subset=['received_datetime', 'enroute_datetime','dispatch_datetime', 'onscene_datetime', 'police_district'])

    # Calculate time deltas
    df['dispatch_to_received_min'] = (df['dispatch_datetime'] - df['received_datetime']).dt.total_seconds() / 60.0
    df['enroute_to_dispatch_min'] = (df['enroute_datetime'] - df['dispatch_datetime']).dt.total_seconds() / 60.0
    df['onscene_to_enroute_min'] = (df['onscene_datetime'] - df['enroute_datetime']).dt.total_seconds() / 60.0

    # Convert datetime fields to strings for JSON-safe output
    for col in datetime_cols:
        df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')

    return df.to_dict(orient='records')

# -----------------------------
# LOAD TASK
# -----------------------------
@task
def load_data(records, database, schema, table):
    hook = SnowflakeHook(snowflake_conn_id='snowflake_conn')
    conn = hook.get_conn()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN;")
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {database}.{schema}.{table} (
                id STRING,
                cad_number STRING,
                received_datetime TIMESTAMP,
                dispatch_datetime TIMESTAMP,
                onscene_datetime TIMESTAMP,
                police_district STRING,
                dispatch_to_received_min FLOAT, 
                enroute_to_dispatch_min FLOAT, 
                onscene_to_enroute_min FLOAT
            );
        """)
        cur.execute(f"DELETE FROM {database}.{schema}.{table}")

        insert_stmt = f"""
            INSERT INTO {database}.{schema}.{table} VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        for row in records:
            values = [row.get(col) or None for col in [
                "id", "cad_number", "received_datetime", "dispatch_datetime",
                "onscene_datetime", "police_district",
                "dispatch_to_received_min", "enroute_to_dispatch_min",
                "onscene_to_enroute_min"
            ]]
            print(values)  # Debug output
            cur.execute(insert_stmt, tuple(values))

        cur.execute("COMMIT;")
        print(f"Successfully loaded {len(records)} records into {database}.{schema}.{table}")
    except Exception as e:
        cur.execute("ROLLBACK;")
        print(f"Error loading data: {e}")
        raise
    finally:
        cur.close()

# -----------------------------
# DAG DEFINITION
# -----------------------------
with DAG(
    dag_id='law_enforcement_ETL',
    start_date=datetime(2025, 4, 5),
    catchup=False,
    schedule='30 2 * * *',
    tags=['ETL', 'law_enforcement']
) as dag:

    url = Variable.get("lab2_LawInforcement_url")
    database = "dev"
    schema = "raw"
    table = "law_enforcement_calls"
    extracted = extract_data(url)
    transformed = transform_data(extracted)
    load = load_data(transformed, database, schema, table)

    extracted >> transformed >> load
