from datetime import datetime, timezone
from pathlib import Path
import json

import pandas as pd
from sqlalchemy import create_engine, text

from app.core.config import get_settings

RAW_DIRECTORY = Path("data/raw/orders")

WATERMARK_FILE = Path("data/metadata/orders_watermark.json")


def load_watermark() -> datetime | None:

    if not WATERMARK_FILE.exists():
        return None

    with WATERMARK_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        metadata = json.load(file)

    return datetime.fromisoformat(metadata["watermark"])


def save_watermark(
    watermark: datetime,
) -> None:

    WATERMARK_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata = {"watermark": watermark.isoformat()}

    with WATERMARK_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2,
        )


def extract_orders(
    engine,
    watermark: datetime | None,
    extraction_upper_bound: datetime,
) -> pd.DataFrame:

    if watermark is None:

        query = text("""
            SELECT *
            FROM orders
            WHERE updated_at <= :upper_bound
            ORDER BY updated_at
            """)

        parameters = {"upper_bound": extraction_upper_bound}

    else:

        query = text("""
            SELECT *
            FROM orders
            WHERE updated_at > :watermark
              AND updated_at <= :upper_bound
            ORDER BY updated_at
            """)

        parameters = {
            "watermark": watermark,
            "upper_bound": extraction_upper_bound,
        }

    return pd.read_sql(
        query,
        engine,
        params=parameters,
    )


def write_parquet(
    dataframe: pd.DataFrame,
    extraction_time: datetime,
) -> Path:

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = extraction_time.strftime("%Y%m%dT%H%M%SZ")

    output_path = RAW_DIRECTORY / f"orders_{timestamp}.parquet"

    dataframe.to_parquet(
        output_path,
        engine="pyarrow",
        index=False,
        compression="snappy",
    )

    return output_path


def main() -> None:

    settings = get_settings()

    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
    )

    watermark = load_watermark()

    extraction_upper_bound = datetime.now(timezone.utc)

    print(
        "Previous watermark:",
        watermark,
    )

    print(
        "Extraction upper bound:",
        extraction_upper_bound,
    )

    dataframe = extract_orders(
        engine,
        watermark,
        extraction_upper_bound,
    )

    print(f"Rows extracted: {len(dataframe):,}")

    if dataframe.empty:

        print("No changed orders found.")

        # We intentionally do not need a data file.
        # Advancing to the upper bound is safe because the
        # query covered the interval through that timestamp.
        save_watermark(extraction_upper_bound)

        print(
            "Watermark updated:",
            extraction_upper_bound,
        )

        return

    output_path = write_parquet(
        dataframe,
        extraction_upper_bound,
    )

    print(
        "Written:",
        output_path,
    )

    # Only checkpoint AFTER the Parquet write succeeds.
    save_watermark(extraction_upper_bound)

    print(
        "Watermark updated:",
        extraction_upper_bound,
    )


if __name__ == "__main__":
    main()
