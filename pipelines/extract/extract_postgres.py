from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

from app.core.config import get_settings
import json

RAW_DATA_DIR = Path("data/raw")

ORDERS_WATERMARK_FILE = Path("data/metadata/orders_watermark.json")

SOURCE_TABLES = [
    "customers",
    "products",
    "warehouses",
    "inventory",
    "orders",
    "order_items",
    "order_shipping_addresses",
    "order_status_history",
    "payments",
]


def extract_table(
    table_name: str,
    engine,
) -> pd.DataFrame:

    query = f"SELECT * FROM {table_name}"

    return pd.read_sql(
        query,
        engine,
    )


def save_raw_parquet(
    dataframe: pd.DataFrame,
    table_name: str,
    extraction_time: datetime,
) -> Path:

    table_directory = RAW_DATA_DIR / table_name

    table_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = extraction_time.strftime("%Y%m%dT%H%M%SZ")

    output_path = table_directory / f"{table_name}_{timestamp}.parquet"

    dataframe.to_parquet(
        output_path,
        engine="pyarrow",
        index=False,
        compression="snappy",
    )

    return output_path


def save_orders_watermark(
    watermark: datetime,
) -> None:

    ORDERS_WATERMARK_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata = {"watermark": watermark.isoformat()}

    with ORDERS_WATERMARK_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2,
        )


def main() -> None:

    settings = get_settings()

    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
    )

    extraction_time = datetime.now(timezone.utc)

    print(f"Extraction started: " f"{extraction_time.isoformat()}")

    for table_name in SOURCE_TABLES:

        dataframe = extract_table(
            table_name,
            engine,
        )

        output_path = save_raw_parquet(
            dataframe,
            table_name,
            extraction_time,
        )

        print(f"{table_name:<28} " f"{len(dataframe):>8,} rows " f"-> {output_path}")

    save_orders_watermark(extraction_time)

    print(
        "Orders watermark initialized:",
        extraction_time.isoformat(),
    )
    print("Extraction complete.")


if __name__ == "__main__":
    main()
