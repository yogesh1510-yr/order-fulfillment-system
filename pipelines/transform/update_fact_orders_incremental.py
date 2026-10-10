from pathlib import Path
from datetime import datetime
import json

import pandas as pd

PROCESSED_ORDERS = Path("data/processed/orders/orders.parquet")

DIM_CUSTOMER = Path("data/analytics/dim_customer.parquet")
DIM_WAREHOUSE = Path("data/analytics/dim_warehouse.parquet")

FACT_ORDERS = Path("data/analytics/fact_orders.parquet")

WATERMARK_FILE = Path("data/metadata/fact_orders_watermark.json")


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


def main() -> None:

    # -----------------------------------------
    # Load processed orders
    # -----------------------------------------

    orders = pd.read_parquet(PROCESSED_ORDERS)

    orders["created_at"] = pd.to_datetime(
        orders["created_at"],
        utc=True,
    )

    orders["updated_at"] = pd.to_datetime(
        orders["updated_at"],
        utc=True,
    )

    # -----------------------------------------
    # Load analytics watermark
    # -----------------------------------------

    watermark = load_watermark()

    print(
        "Previous analytics watermark:",
        watermark,
    )

    # -----------------------------------------
    # Find changed orders
    # -----------------------------------------

    if watermark is None:

        changed_orders = orders.copy()

    else:

        watermark_timestamp = pd.Timestamp(watermark)

        changed_orders = orders[orders["updated_at"] > watermark_timestamp].copy()

    print(
        "Orders requiring analytics update:",
        f"{len(changed_orders):,}",
    )

    if changed_orders.empty:

        print("No analytics updates required.")

        return

    # -----------------------------------------
    # Freeze this batch's upper bound
    # -----------------------------------------

    analytics_upper_bound = changed_orders["updated_at"].max()

    # -----------------------------------------
    # Load dimensions
    # -----------------------------------------

    customers = pd.read_parquet(DIM_CUSTOMER)[
        [
            "customer_key",
            "customer_id",
        ]
    ]

    warehouses = pd.read_parquet(DIM_WAREHOUSE)[
        [
            "warehouse_key",
            "warehouse_id",
        ]
    ]

    # -----------------------------------------
    # Dimension lookups
    # -----------------------------------------

    changed_orders = changed_orders.merge(
        customers,
        on="customer_id",
        how="left",
    )

    changed_orders = changed_orders.merge(
        warehouses,
        on="warehouse_id",
        how="left",
    )

    # -----------------------------------------
    # Build date key
    # -----------------------------------------

    changed_orders["order_date_key"] = (
        changed_orders["created_at"].dt.strftime("%Y%m%d").astype(int)
    )

    # -----------------------------------------
    # Build fact rows
    # -----------------------------------------

    changed_fact = changed_orders[
        [
            "order_id",
            "customer_key",
            "warehouse_key",
            "order_date_key",
            "status",
            "total_amount",
            "discount_amount",
            "tax_amount",
            "handling_amount",
            "created_at",
            "updated_at",
        ]
    ].copy()

    # -----------------------------------------
    # Validate dimension lookups
    # -----------------------------------------

    if changed_fact["customer_key"].isna().any():

        raise ValueError("Missing customer dimension key")

    if changed_fact["warehouse_key"].isna().any():

        raise ValueError("Missing warehouse dimension key")

    # -----------------------------------------
    # UPSERT fact_orders
    # -----------------------------------------

    if FACT_ORDERS.exists():

        existing_fact = pd.read_parquet(FACT_ORDERS)

        combined = pd.concat(
            [
                existing_fact,
                changed_fact,
            ],
            ignore_index=True,
        )

        combined["updated_at"] = pd.to_datetime(
            combined["updated_at"],
            utc=True,
        )

        combined = combined.sort_values(
            [
                "order_id",
                "updated_at",
            ]
        )

        fact_orders = (
            combined.drop_duplicates(
                subset=["order_id"],
                keep="last",
            )
            .sort_values("order_id")
            .reset_index(drop=True)
        )

    else:

        fact_orders = changed_fact.sort_values("order_id").reset_index(drop=True)

    # -----------------------------------------
    # Validate final fact
    # -----------------------------------------

    if fact_orders["order_id"].duplicated().any():

        raise ValueError("Duplicate order_id in fact_orders")

    # -----------------------------------------
    # Atomic write
    # -----------------------------------------

    FACT_ORDERS.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = FACT_ORDERS.with_suffix(".tmp.parquet")

    fact_orders.to_parquet(
        temporary_file,
        engine="pyarrow",
        index=False,
        compression="snappy",
    )

    temporary_file.replace(FACT_ORDERS)

    # -----------------------------------------
    # Advance analytics watermark LAST
    # -----------------------------------------

    save_watermark(analytics_upper_bound.to_pydatetime())

    print(
        "fact_orders rows:",
        f"{len(fact_orders):,}",
    )

    print(
        "Analytics watermark updated:",
        analytics_upper_bound,
    )

    print("Incremental fact_orders update complete.")


if __name__ == "__main__":
    main()
