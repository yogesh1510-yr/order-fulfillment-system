from pathlib import Path

import pandas as pd

ANALYTICS_DIRECTORY = Path("data/analytics")


def test_order_totals_reconcile() -> None:

    orders = pd.read_parquet(ANALYTICS_DIRECTORY / "fact_orders.parquet")

    items = pd.read_parquet(ANALYTICS_DIRECTORY / "fact_order_items.parquet")

    item_summary = (
        items.groupby("order_id")
        .agg(
            item_subtotal=(
                "line_amount",
                "sum",
            )
        )
        .reset_index()
    )

    check = orders.merge(
        item_summary,
        on="order_id",
        how="left",
    )

    check["calculated_total"] = (
        check["item_subtotal"]
        - check["discount_amount"]
        + check["tax_amount"]
        + check["handling_amount"]
    ).clip(lower=0)

    check["difference"] = check["total_amount"] - check["calculated_total"]

    tolerance = 0.01

    bad_orders = check[check["difference"].abs() > tolerance]

    assert bad_orders.empty, (
        "\nOrder financial reconciliation failed.\n"
        f"Orders outside tolerance: "
        f"{len(bad_orders)}\n"
        f"Tolerance: {tolerance}\n\n"
        f"{bad_orders.head(10).to_string()}"
    )
