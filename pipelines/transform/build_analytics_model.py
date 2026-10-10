from pathlib import Path

import pandas as pd

PROCESSED_ORDERS = Path("data/processed/orders/orders.parquet")

RAW_CUSTOMERS_DIRECTORY = Path("data/raw/customers")

RAW_PRODUCTS_DIRECTORY = Path("data/raw/products")

RAW_WAREHOUSES_DIRECTORY = Path("data/raw/warehouses")

RAW_PAYMENTS_DIRECTORY = Path("data/raw/payments")

RAW_ORDER_ITEMS_DIRECTORY = Path("data/raw/order_items")

ANALYTICS_DIRECTORY = Path("data/analytics")


def read_latest_snapshot(
    directory: Path,
) -> pd.DataFrame:

    files = sorted(directory.glob("*.parquet"))

    if not files:
        raise FileNotFoundError(f"No Parquet files found in {directory}")

    latest_file = files[-1]

    print(f"Reading snapshot: {latest_file}")

    return pd.read_parquet(latest_file)


def build_customer_dimension(
    customers: pd.DataFrame,
) -> pd.DataFrame:

    dimension = customers.copy()

    dimension = dimension.drop_duplicates(subset=["customer_id"]).reset_index(drop=True)

    dimension.insert(
        0,
        "customer_key",
        range(1, len(dimension) + 1),
    )

    return dimension


def build_warehouse_dimension(
    warehouses: pd.DataFrame,
) -> pd.DataFrame:

    dimension = warehouses.copy()

    dimension = dimension.drop_duplicates(subset=["warehouse_id"]).reset_index(
        drop=True
    )

    dimension.insert(
        0,
        "warehouse_key",
        range(1, len(dimension) + 1),
    )

    return dimension


def build_date_dimension(
    orders: pd.DataFrame,
) -> pd.DataFrame:

    dates = pd.date_range(
        start="2020-01-01",
        end="2035-12-31",
        freq="D",
    )

    dimension = pd.DataFrame({"full_date": dates})

    dimension["date_key"] = dimension["full_date"].dt.strftime("%Y%m%d").astype(int)

    dimension["year"] = dimension["full_date"].dt.year

    dimension["quarter"] = dimension["full_date"].dt.quarter

    dimension["month"] = dimension["full_date"].dt.month

    dimension["month_name"] = dimension["full_date"].dt.month_name()

    dimension["day"] = dimension["full_date"].dt.day

    dimension["day_of_week"] = dimension["full_date"].dt.day_name()

    dimension["is_weekend"] = dimension["full_date"].dt.dayofweek.isin([5, 6])

    return dimension[
        [
            "date_key",
            "full_date",
            "year",
            "quarter",
            "month",
            "month_name",
            "day",
            "day_of_week",
            "is_weekend",
        ]
    ]


def build_product_dimension(
    products: pd.DataFrame,
) -> pd.DataFrame:

    dimension = products.copy()

    dimension = dimension.drop_duplicates(subset=["product_id"]).reset_index(drop=True)

    dimension.insert(
        0,
        "product_key",
        range(1, len(dimension) + 1),
    )

    return dimension[
        [
            "product_key",
            "product_id",
            "sku",
            "product_name",
            "size",
            "mrp",
        ]
    ]


def build_fact_orders(
    orders: pd.DataFrame,
    customers: pd.DataFrame,
    warehouses: pd.DataFrame,
) -> pd.DataFrame:

    fact = orders.copy()

    fact = fact.merge(
        customers[
            [
                "customer_key",
                "customer_id",
            ]
        ],
        on="customer_id",
        how="left",
    )

    fact = fact.merge(
        warehouses[
            [
                "warehouse_key",
                "warehouse_id",
            ]
        ],
        on="warehouse_id",
        how="left",
    )

    fact["created_at"] = pd.to_datetime(
        fact["created_at"],
        utc=True,
    )

    fact["order_date_key"] = fact["created_at"].dt.strftime("%Y%m%d").astype(int)

    return fact[
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
    ]


def build_fact_order_items(
    order_items: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:

    fact = order_items.copy()

    fact = fact.merge(
        products[
            [
                "product_key",
                "product_id",
            ]
        ],
        on="product_id",
        how="left",
    )

    fact["line_amount"] = fact["quantity"] * fact["unit_price"]

    return fact[
        [
            "order_item_id",
            "order_id",
            "product_key",
            "quantity",
            "unit_price",
            "line_amount",
            "created_at",
        ]
    ]


def build_fact_payments(
    payments: pd.DataFrame,
) -> pd.DataFrame:

    fact = payments.copy()

    fact["created_at"] = pd.to_datetime(
        fact["created_at"],
        utc=True,
    )

    fact["updated_at"] = pd.to_datetime(
        fact["updated_at"],
        utc=True,
    )

    fact["payment_date_key"] = fact["created_at"].dt.strftime("%Y%m%d").astype(int)

    return fact[
        [
            "payment_id",
            "order_id",
            "payment_date_key",
            "status",
            "amount",
            "provider_transaction_id",
            "failure_reason",
            "created_at",
            "updated_at",
        ]
    ]


def validate_analytics_model(
    fact_orders: pd.DataFrame,
) -> None:

    if fact_orders["order_id"].duplicated().any():
        raise ValueError("fact_orders grain violation: " "duplicate order_id.")

    if fact_orders["customer_key"].isna().any():
        raise ValueError("fact_orders contains unknown customers.")

    if fact_orders["warehouse_key"].isna().any():
        raise ValueError("fact_orders contains unknown warehouses.")


def validate_fact_order_items(
    fact_order_items: pd.DataFrame,
) -> None:

    if fact_order_items["order_item_id"].isna().any():
        raise ValueError("fact_order_items contains " "NULL order_item_id.")

    if fact_order_items["order_item_id"].duplicated().any():
        raise ValueError(
            "fact_order_items grain violation: " "duplicate order_item_id."
        )

    if fact_order_items["product_key"].isna().any():
        raise ValueError("fact_order_items contains " "unknown products.")

    if (fact_order_items["quantity"] <= 0).any():
        raise ValueError("fact_order_items contains " "invalid quantity.")

    if (fact_order_items["unit_price"] < 0).any():
        raise ValueError("fact_order_items contains " "negative unit_price.")


def validate_fact_payments(
    fact_payments: pd.DataFrame,
) -> None:

    if fact_payments["payment_id"].isna().any():
        raise ValueError("fact_payments contains NULL payment_id.")

    if fact_payments["payment_id"].duplicated().any():
        raise ValueError("fact_payments grain violation: " "duplicate payment_id.")

    if fact_payments["order_id"].isna().any():
        raise ValueError("fact_payments contains NULL order_id.")

    if (fact_payments["amount"] < 0).any():
        raise ValueError("fact_payments contains negative amount.")

    valid_statuses = {
        "SUCCESS",
        "FAILED",
    }

    invalid_statuses = set(fact_payments["status"].dropna().unique()) - valid_statuses

    if invalid_statuses:
        raise ValueError(f"Unknown payment statuses: " f"{invalid_statuses}")


def validate_relationship(
    child: pd.DataFrame,
    child_column: str,
    parent: pd.DataFrame,
    parent_column: str,
    relationship_name: str,
) -> None:

    child_values = set(child[child_column].dropna().unique())

    parent_values = set(parent[parent_column].dropna().unique())

    orphan_values = child_values - parent_values

    if orphan_values:
        sample = list(orphan_values)[:10]

        raise ValueError(
            f"{relationship_name} failed. "
            f"Found {len(orphan_values)} "
            f"orphan values. "
            f"Sample: {sample}"
        )


def validate_analytics_relationships(
    fact_orders: pd.DataFrame,
    fact_order_items: pd.DataFrame,
    fact_payments: pd.DataFrame,
    dim_customer: pd.DataFrame,
    dim_product: pd.DataFrame,
    dim_warehouse: pd.DataFrame,
    dim_date: pd.DataFrame,
) -> None:

    validate_relationship(
        fact_payments,
        "order_id",
        fact_orders,
        "order_id",
        "fact_payments -> fact_orders",
    )

    validate_relationship(
        fact_order_items,
        "order_id",
        fact_orders,
        "order_id",
        "fact_order_items -> fact_orders",
    )

    validate_relationship(
        fact_order_items,
        "product_key",
        dim_product,
        "product_key",
        "fact_order_items -> dim_product",
    )

    validate_relationship(
        fact_orders,
        "customer_key",
        dim_customer,
        "customer_key",
        "fact_orders -> dim_customer",
    )

    validate_relationship(
        fact_orders,
        "warehouse_key",
        dim_warehouse,
        "warehouse_key",
        "fact_orders -> dim_warehouse",
    )

    validate_relationship(
        fact_orders,
        "order_date_key",
        dim_date,
        "date_key",
        "fact_orders -> dim_date",
    )

    validate_relationship(
        fact_payments,
        "payment_date_key",
        dim_date,
        "date_key",
        "fact_payments -> dim_date",
    )


def main() -> None:

    orders = pd.read_parquet(PROCESSED_ORDERS)

    customers = read_latest_snapshot(RAW_CUSTOMERS_DIRECTORY)

    warehouses = read_latest_snapshot(RAW_WAREHOUSES_DIRECTORY)

    products = read_latest_snapshot(RAW_PRODUCTS_DIRECTORY)

    order_items = read_latest_snapshot(RAW_ORDER_ITEMS_DIRECTORY)

    payments = read_latest_snapshot(RAW_PAYMENTS_DIRECTORY)

    dim_customer = build_customer_dimension(customers)

    dim_warehouse = build_warehouse_dimension(warehouses)

    dim_date = build_date_dimension(orders)

    dim_product = build_product_dimension(products)

    fact_orders = build_fact_orders(
        orders,
        dim_customer,
        dim_warehouse,
    )

    fact_order_items = build_fact_order_items(
        order_items,
        dim_product,
    )

    fact_payments = build_fact_payments(payments)

    # ==========================================
    #  DATA VALIDATION CHECKS
    # ==========================================

    validate_analytics_model(fact_orders)

    validate_fact_order_items(fact_order_items)

    validate_fact_payments(fact_payments)

    validate_analytics_relationships(
        fact_orders,
        fact_order_items,
        fact_payments,
        dim_customer,
        dim_product,
        dim_warehouse,
        dim_date,
    )
    ANALYTICS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    dim_customer.to_parquet(
        ANALYTICS_DIRECTORY / "dim_customer.parquet",
        index=False,
    )

    dim_warehouse.to_parquet(
        ANALYTICS_DIRECTORY / "dim_warehouse.parquet",
        index=False,
    )

    dim_date.to_parquet(
        ANALYTICS_DIRECTORY / "dim_date.parquet",
        index=False,
    )

    dim_product.to_parquet(
        ANALYTICS_DIRECTORY / "dim_product.parquet",
        index=False,
    )

    fact_orders.to_parquet(
        ANALYTICS_DIRECTORY / "fact_orders.parquet",
        index=False,
    )

    fact_order_items.to_parquet(
        ANALYTICS_DIRECTORY / "fact_order_items.parquet",
        index=False,
    )

    fact_payments.to_parquet(
        ANALYTICS_DIRECTORY / "fact_payments.parquet",
        index=False,
    )

    print(f"dim_customer:  {len(dim_customer):,}")

    print(f"dim_warehouse: {len(dim_warehouse):,}")

    print(f"dim_date:      {len(dim_date):,}")

    print(f"dim_product:    {len(dim_product)}")

    print(f"fact_orders:   {len(fact_orders):,}")

    print(f"fact_order_items:   {len(fact_order_items)}")

    print(f"fact_payments: {len(fact_payments):,}")

    print("Cross-table relationship " "validation passed.")

    print("Analytics model built successfully.")


if __name__ == "__main__":
    main()
