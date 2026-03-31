from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

PROJECT_DIR = "/opt/airflow/boe-stats-pipeline"
DBT_DIR = f"{PROJECT_DIR}/boe_stats_pipeline"

default_args = {
    "owner": "daud",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="boe_stats_pipeline",
    description="BoE statistics pipeline — extract, load, dbt transform",
    schedule_interval="0 6 1 * *",  # 6am on 1st of every month
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["boe", "finance", "de-portfolio"],
) as dag:

    extract = BashOperator(
        task_id="extract",
        bash_command=f"cd {PROJECT_DIR} && python3 -m etl.extract",
    )

    transform = BashOperator(
        task_id="transform",
        bash_command=f"cd {PROJECT_DIR} && python3 -m etl.transform",
    )

    load = BashOperator(
        task_id="load",
        bash_command=f"cd {PROJECT_DIR} && python3 -m etl.load",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt run --profiles-dir /root/.dbt",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test --profiles-dir /root/.dbt",
    )

    extract >> transform >> load >> dbt_run >> dbt_test
