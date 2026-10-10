from datetime import datetime, timezone
from pathlib import Path
import shutil

import pandas as pd

RAW_DIRECTORY = Path("data/raw/orders")

PROCESSED_DIRECTORY = Path("data/processed/orders")

PROCESSED_FILE = PROCESSED_DIRECTORY / "orders.parquet"

ARCHIVE_DIRECTORY = Path("data/archive/orders")


def archive_file(
    source_file: Path,
    status: str,
) -> Path:

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    destination_directory = ARCHIVE_DIRECTORY / status / today

    destination_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination_file = destination_directory / source_file.name

    shutil.move(
        str(source_file),
        str(destination_file),
    )

    return destination_file


def validate_orders(
    dataframe: pd.DataFrame,
) -> None:

    if dataframe["order_id"].isna().any():
        raise ValueError("order_id contains NULL values")

    if dataframe["order_id"].duplicated().any():
        raise ValueError("Duplicate order_id found")

    if dataframe["status"].isna().any():
        raise ValueError("status contains NULL values")

    if (dataframe["total_amount"] < 0).any():
        raise ValueError("Negative total_amount found")


def process_batch(
    batch_file: Path,
) -> None:

    print()
    print(f"Processing: {batch_file.name}")

    incoming = pd.read_parquet(batch_file)

    print(f"Incoming rows: {len(incoming):,}")

    incoming["created_at"] = pd.to_datetime(
        incoming["created_at"],
        utc=True,
    )

    incoming["updated_at"] = pd.to_datetime(
        incoming["updated_at"],
        utc=True,
    )

    # -----------------------------------------
    # Existing processed data?
    # -----------------------------------------

    if PROCESSED_FILE.exists():

        existing = pd.read_parquet(PROCESSED_FILE)

        existing["created_at"] = pd.to_datetime(
            existing["created_at"],
            utc=True,
        )

        existing["updated_at"] = pd.to_datetime(
            existing["updated_at"],
            utc=True,
        )

        print(f"Existing rows: {len(existing):,}")

        combined = pd.concat(
            [
                existing,
                incoming,
            ],
            ignore_index=True,
        )

    else:

        print("No existing processed dataset.")

        print("Initializing from first batch.")

        combined = incoming.copy()

    # -----------------------------------------
    # UPSERT
    # -----------------------------------------

    combined = combined.sort_values(
        [
            "order_id",
            "updated_at",
        ]
    )

    processed = combined.drop_duplicates(
        subset=["order_id"],
        keep="last",
    )

    processed = processed.sort_values("order_id").reset_index(drop=True)

    # -----------------------------------------
    # Validation
    # -----------------------------------------

    validate_orders(processed)

    print(f"Processed rows: {len(processed):,}")

    # -----------------------------------------
    # Write processed state
    # -----------------------------------------

    PROCESSED_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = PROCESSED_FILE.with_suffix(".tmp.parquet")

    processed.to_parquet(
        temporary_file,
        engine="pyarrow",
        index=False,
        compression="snappy",
    )

    temporary_file.replace(PROCESSED_FILE)


def main() -> None:

    RAW_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    batch_files = sorted(RAW_DIRECTORY.glob("*.parquet"))

    if not batch_files:

        print("No order batches waiting " "for processing.")

        return

    print(f"Batches waiting: " f"{len(batch_files)}")

    for batch_file in batch_files:

        try:

            process_batch(batch_file)

            archived_file = archive_file(
                batch_file,
                "success",
            )

            print(
                "SUCCESS:",
                archived_file,
            )

        except Exception as error:

            archived_file = archive_file(
                batch_file,
                "failed",
            )

            print(
                "FAILED:",
                batch_file.name,
            )

            print(
                "Reason:",
                error,
            )

            print(
                "Moved to:",
                archived_file,
            )


if __name__ == "__main__":
    main()
