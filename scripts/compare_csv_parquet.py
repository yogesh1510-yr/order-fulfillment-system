from pathlib import Path
from time import perf_counter

import pandas as pd

CSV_PATH = Path("data/raw/orders.csv")

PARQUET_PATH = Path("data/processed/orders_typed.parquet")


def size_mb(path: Path) -> float:
    return path.stat().st_size / 1024 / 1024


def main() -> None:

    print("FILE SIZE")
    print("---------")

    print(f"CSV:     {size_mb(CSV_PATH):.2f} MB")

    print(f"Parquet: {size_mb(PARQUET_PATH):.2f} MB")

    print()

    start = perf_counter()

    csv_df = pd.read_csv(CSV_PATH)

    csv_time = perf_counter() - start

    start = perf_counter()

    parquet_df = pd.read_parquet(PARQUET_PATH)

    parquet_time = perf_counter() - start

    print("FULL READ")
    print("---------")

    print(f"CSV:     {csv_time:.4f} seconds")

    print(f"Parquet: {parquet_time:.4f} seconds")

    print()

    start = perf_counter()

    parquet_subset = pd.read_parquet(
        PARQUET_PATH,
        columns=[
            "order_id",
            "total_amount",
        ],
    )

    subset_time = perf_counter() - start

    print("PARQUET COLUMN PRUNING")
    print("----------------------")

    print(f"2 columns: {subset_time:.4f} seconds")

    print()

    print(f"CSV rows: {len(csv_df):,}")

    print(f"Parquet rows: {len(parquet_df):,}")

    print(f"Subset shape: {parquet_subset.shape}")


if __name__ == "__main__":
    main()
