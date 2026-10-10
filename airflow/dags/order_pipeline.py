from datetime import datetime

from airflow.sdk import DAG, task

with DAG(
    dag_id="order_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["orders", "production-pipeline"],
) as dag:

    @task(retries=2, retry_delay=10)
    def extract_orders():
        import subprocess

        subprocess.run(
            [
                "python",
                "pipelines/extract/extract_orders_incremental.py",
            ],
            check=True,
        )

    @task
    def process_orders():
        import subprocess

        subprocess.run(
            [
                "python",
                "pipelines/transform/process_orders.py",
            ],
            check=True,
        )

    @task
    def update_fact_orders():
        import subprocess

        subprocess.run(
            [
                "python",
                "pipelines/transform/update_fact_orders_incremental.py",
            ],
            check=True,
        )

    extracted = extract_orders()
    processed = process_orders()
    fact_updated = update_fact_orders()

    extracted >> processed >> fact_updated
