"""
A basic dbt DAG that shows how to run dbt commands via the BashOperator.
Follows the standard dbt seed, run, and test pattern.
"""

from pendulum import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.hooks.base import BaseHook

DBT_PROJECT_DIR = "/opt/airflow/dbt"

# Fetch Airflow connection
conn = BaseHook.get_connection('snowflake_conn')

# Define environment variables (dbt expects these)
env_vars = {
    "DBT_USER": conn.extra_dejson.get("snowflake_userid") or "",
    "DBT_PASSWORD": conn.extra_dejson.get("snowflake_password") or "",
    "DBT_ACCOUNT": conn.extra_dejson.get("snowflake_account") or "",
    "DBT_SCHEMA": conn.schema or "",
    "DBT_DATABASE": conn.extra_dejson.get("database") or "",
    "DBT_ROLE": conn.extra_dejson.get("role") or "",
    "DBT_WAREHOUSE": conn.extra_dejson.get("warehouse") or "",
    "DBT_TYPE": "snowflake",
    "DBT_PROFILES_DIR": DBT_PROJECT_DIR
}

# Define the DAG
with DAG(
    "BuildELT_dbt",
    start_date=datetime(2025, 3, 19),
    description="A sample Airflow DAG to invoke dbt runs using a BashOperator",
    schedule=None,
    catchup=False,
) as dag:

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"/home/airflow/.local/bin/dbt run --profiles-dir {DBT_PROJECT_DIR} --project-dir {DBT_PROJECT_DIR}",
        env=env_vars,
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"/home/airflow/.local/bin/dbt test --profiles-dir {DBT_PROJECT_DIR} --project-dir {DBT_PROJECT_DIR}",
        env=env_vars,
    )

    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=f"/home/airflow/.local/bin/dbt snapshot --profiles-dir {DBT_PROJECT_DIR} --project-dir {DBT_PROJECT_DIR}",
        env=env_vars,
    )

    # Task sequence
    dbt_run >> dbt_test >> dbt_snapshot
