from datetime import datetime, timezone
from pathlib import Path
import shutil

import pandas as pd

INCOMING_DIRECTORY = Path("data/raw/orders_incremental")

PROCESSED_FILE = Path("data/processed/orders/orders.parquet")

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

    destination = destination_directory / source_file.name

    shutil.move(
        str(source_file),
        str(destination),
    )

    return destination


def process_batch(
    batch_file: Path,
) -> None:

    print()
    print(f"Processing: {batch_file.name}")

    existing = pd.read_parquet(PROCESSED_FILE)

    incremental = pd.read_parquet(batch_file)

    print(f"Existing rows:    {len(existing):,}")

    print(f"Incremental rows: {len(incremental):,}")

    # Combine existing data with incoming changes
    combined = pd.concat(
        [existing, incremental],
        ignore_index=True,
    )

    combined["updated_at"] = pd.to_datetime(
        combined["updated_at"],
        utc=True,
    )

    # Sort so the newest version of an order
    # appears last.
    combined = combined.sort_values(["order_id", "updated_at"])

    # UPSERT behaviour:
    # keep only the newest version of each order.
    merged = combined.drop_duplicates(
        subset=["order_id"],
        keep="last",
    )

    merged = merged.sort_values("order_id").reset_index(drop=True)

    # -----------------------------
    # Data-quality validation
    # -----------------------------

    if merged["order_id"].isna().any():
        raise ValueError("order_id contains NULL values")

    if merged["order_id"].duplicated().any():
        raise ValueError("Duplicate order_id found")

    print(f"Rows after merge: {len(merged):,}")

    # -----------------------------
    # Write processed dataset
    # -----------------------------

    merged.to_parquet(
        PROCESSED_FILE,
        engine="pyarrow",
        index=False,
        compression="snappy",
    )


def main() -> None:

    INCOMING_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    batch_files = sorted(INCOMING_DIRECTORY.glob("*.parquet"))

    if not batch_files:
        print("No incremental batches to process.")
        return

    print(f"Batches waiting: {len(batch_files)}")

    for batch_file in batch_files:

        try:

            process_batch(batch_file)

            archived_path = archive_file(
                batch_file,
                "success",
            )

            print(
                "SUCCESS:",
                archived_path,
            )

        except Exception as error:

            archived_path = archive_file(
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
                archived_path,
            )


if __name__ == "__main__":
    main()
