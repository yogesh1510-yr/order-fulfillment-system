from pathlib import Path

import pandas as pd

ANALYTICS_DIRECTORY = Path("data/analytics")


def main() -> None:

    # --------------------------------------------------
    # Load analytics tables
    # --------------------------------------------------

    orders = pd.read_parquet(ANALYTICS_DIRECTORY / "fact_orders.parquet")

    items = pd.read_parquet(ANALYTICS_DIRECTORY / "fact_order_items.parquet")

    payments = pd.read_parquet(ANALYTICS_DIRECTORY / "fact_payments.parquet")

    # --------------------------------------------------
    # Row counts
    # --------------------------------------------------

    print()
    print("=== ROW COUNTS ===")

    print(f"Orders:   {len(orders):,}")
    print(f"Items:    {len(items):,}")
    print(f"Payments: {len(payments):,}")

    # --------------------------------------------------
    # Overall order values
    # --------------------------------------------------

    print()
    print("=== ORDER VALUES ===")

    order_total = orders["total_amount"].sum()
    item_total = items["line_amount"].sum()

    print(f"Order total:     " f"{order_total:,.2f}")

    print(f"Item line total: " f"{item_total:,.2f}")

    print(f"Raw difference:  " f"{order_total - item_total:,.2f}")

    # --------------------------------------------------
    # Per-order financial reconciliation
    # --------------------------------------------------

    print()
    print("=== ORDER RECONCILIATION ===")

    item_summary = (
        items.groupby("order_id")
        .agg(
            item_subtotal=(
                "line_amount",
                "sum",
            ),
            total_units=(
                "quantity",
                "sum",
            ),
            item_lines=(
                "order_item_id",
                "count",
            ),
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

    print(
        "Maximum absolute difference:",
        check["difference"].abs().max(),
    )

    print(
        "Average absolute difference:",
        check["difference"].abs().mean(),
    )

    print(
        f"Orders with difference > " f"₹{tolerance:.2f}:",
        len(bad_orders),
    )

    if not bad_orders.empty:
        print()
        print("BAD ORDERS:")

        print(
            bad_orders[
                [
                    "order_id",
                    "item_subtotal",
                    "discount_amount",
                    "tax_amount",
                    "handling_amount",
                    "calculated_total",
                    "total_amount",
                    "difference",
                ]
            ]
            .head(10)
            .to_string(index=False)
        )

    # --------------------------------------------------
    # Payment values
    # --------------------------------------------------

    print()
    print("=== PAYMENT VALUES ===")

    successful_payments = payments[payments["status"] == "SUCCESS"]

    failed_payments = payments[payments["status"] == "FAILED"]

    payment_count = len(payments)
    success_count = len(successful_payments)

    success_rate = success_count / payment_count * 100

    print(f"Payment success rate: " f"{success_rate:.2f}%")

    print(f"Successful payments: " f"{len(successful_payments):,}")

    print(f"Failed payments:     " f"{len(failed_payments):,}")

    print(f"Successful amount:   " f"{successful_payments['amount'].sum():,.2f}")

    print(f"Failed amount:       " f"{failed_payments['amount'].sum():,.2f}")

    # --------------------------------------------------
    # Payment attempts
    # --------------------------------------------------

    print()
    print("=== PAYMENT ATTEMPTS PER ORDER ===")

    attempts = payments.groupby("order_id").size()

    print(f"Orders with payment records: " f"{attempts.size:,}")

    print(f"Maximum attempts for one order: " f"{attempts.max():,}")

    print(f"Orders with >1 payment attempt: " f"{(attempts > 1).sum():,}")


if __name__ == "__main__":
    main()
