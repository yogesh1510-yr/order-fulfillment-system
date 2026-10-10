from datetime import datetime

from airflow.sdk import DAG, task


with DAG(
    dag_id="hello_airflow",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["learning"],
) as dag:

    @task
    def extract():
        print("Extracting data...")

    @task(retries=2, retry_delay=10)
    def transform():
        print("Transforming data...")

    @task
    def load():
        print("Loading data...")

    extracted = extract()
    transformed = transform()
    loaded = load()

    extracted >> transformed >> loaded