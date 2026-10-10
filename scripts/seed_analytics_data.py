from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.order import (
    Order,
    OrderItem,
    OrderShippingAddress,
    OrderStatusHistory,
)
from app.models.payment import Payment
from app.models.product import Product
from app.models.warehouse import Warehouse

# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_SEED = 42

CUSTOMER_COUNT = 5_000
PRODUCT_COUNT = 500
WAREHOUSE_COUNT = 10
ORDER_COUNT = 25_000

BATCH_SIZE = 1_000


random.seed(RANDOM_SEED)


# ============================================================
# REFERENCE DATA
# ============================================================

CITIES = [
    ("Bengaluru", "Karnataka", "560001"),
    ("Mumbai", "Maharashtra", "400001"),
    ("Delhi", "Delhi", "110001"),
    ("Chennai", "Tamil Nadu", "600001"),
    ("Hyderabad", "Telangana", "500001"),
    ("Pune", "Maharashtra", "411001"),
    ("Kolkata", "West Bengal", "700001"),
    ("Ahmedabad", "Gujarat", "380001"),
    ("Jaipur", "Rajasthan", "302001"),
    ("Kochi", "Kerala", "682001"),
]


PRODUCT_NAMES = [
    "Wireless Mouse",
    "Mechanical Keyboard",
    "USB-C Cable",
    "Laptop Stand",
    "Webcam",
    "Bluetooth Speaker",
    "Power Bank",
    "Phone Charger",
    "External SSD",
    "USB Hub",
    "Monitor",
    "Headphones",
    "Smart Watch",
    "Laptop Sleeve",
    "Desk Lamp",
    "Microphone",
    "Portable Hard Drive",
    "Keyboard Wrist Rest",
    "Mouse Pad",
    "Phone Stand",
]


SIZES = [
    None,
    "Small",
    "Medium",
    "Large",
]


# ============================================================
# HELPERS
# ============================================================


def money(value: float) -> Decimal:
    return Decimal(str(round(value, 2)))


def random_datetime(
    start: datetime,
    end: datetime,
) -> datetime:
    seconds = int((end - start).total_seconds())

    return start + timedelta(seconds=random.randint(0, seconds))


def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:16].upper()}"


# ============================================================
# CUSTOMERS
# ============================================================


def create_customers(
    session: Session,
) -> list[Customer]:

    print("Creating customers...")

    customers = []

    for number in range(1, CUSTOMER_COUNT + 1):

        customer = Customer(
            customer_id=f"CUST-{number:06d}",
            name=f"Customer {number}",
            phone_number=f"+91{random.randint(7000000000, 9999999999)}",
        )

        customers.append(customer)

    session.add_all(customers)
    session.commit()

    print(f"Created {len(customers):,} customers")

    return customers


# ============================================================
# PRODUCTS
# ============================================================


def create_products(
    session: Session,
) -> list[Product]:

    print("Creating products...")

    products = []

    for number in range(1, PRODUCT_COUNT + 1):

        base_name = random.choice(PRODUCT_NAMES)

        product = Product(
            product_id=f"PROD-{number:05d}",
            sku=f"SKU-{number:05d}",
            product_name=f"{base_name} {number}",
            size=random.choice(SIZES),
            mrp=money(
                random.uniform(
                    199,
                    50_000,
                )
            ),
        )

        products.append(product)

    session.add_all(products)
    session.commit()

    print(f"Created {len(products):,} products")

    return products


# ============================================================
# WAREHOUSES
# ============================================================


def create_warehouses(
    session: Session,
) -> list[Warehouse]:

    print("Creating warehouses...")

    warehouses = []

    for number, location in enumerate(
        CITIES,
        start=1,
    ):

        city, state, postal_code = location

        warehouse = Warehouse(
            warehouse_id=f"WH-{number:03d}",
            warehouse_name=f"{city} Fulfillment Center",
            warehouse_number=f"WHNUM-{number:03d}",
            city=city,
            state=state,
            postal_code=postal_code,
            country="India",
            latitude=None,
            longitude=None,
        )

        warehouses.append(warehouse)

    session.add_all(warehouses)
    session.commit()

    print(f"Created {len(warehouses):,} warehouses")

    return warehouses


# ============================================================
# INVENTORY
# ============================================================


def create_inventory(
    session: Session,
    products: list[Product],
    warehouses: list[Warehouse],
) -> None:

    print("Creating inventory...")

    records = []

    counter = 1

    for warehouse in warehouses:

        for product in products:

            total_quantity = random.randint(
                50,
                1_000,
            )

            record = Inventory(
                inventory_id=f"INV-{counter:07d}",
                product_id=product.product_id,
                warehouse_id=warehouse.warehouse_id,
                total_quantity=total_quantity,
                # Historical orders below are synthetic.
                # We are not using current inventory to reconstruct
                # historical reservation state.
                reserved_quantity=0,
            )

            records.append(record)

            counter += 1

    session.add_all(records)
    session.commit()

    print(f"Created {len(records):,} inventory records")


# ============================================================
# STATUS GENERATION
# ============================================================


def choose_order_status() -> str:

    return random.choices(
        population=[
            "DELIVERED",
            "SHIPPED",
            "CONFIRMED",
            "CANCELLED",
            "PAYMENT_PENDING",
        ],
        weights=[
            65,
            10,
            10,
            10,
            5,
        ],
        k=1,
    )[0]


def build_status_sequence(
    final_status: str,
) -> list[str]:

    if final_status == "PAYMENT_PENDING":
        return [
            "PENDING",
            "PAYMENT_PENDING",
        ]

    if final_status == "CANCELLED":
        return [
            "PENDING",
            "PAYMENT_PENDING",
            "CANCELLED",
        ]

    if final_status == "CONFIRMED":
        return [
            "PENDING",
            "PAYMENT_PENDING",
            "CONFIRMED",
        ]

    if final_status == "SHIPPED":
        return [
            "PENDING",
            "PAYMENT_PENDING",
            "CONFIRMED",
            "PACKING",
            "READY_FOR_SHIPMENT",
            "SHIPPED",
        ]

    return [
        "PENDING",
        "PAYMENT_PENDING",
        "CONFIRMED",
        "PACKING",
        "READY_FOR_SHIPMENT",
        "SHIPPED",
        "OUT_FOR_DELIVERY",
        "DELIVERED",
    ]


# ============================================================
# ORDERS
# ============================================================


def create_orders(
    session: Session,
    customers: list[Customer],
    products: list[Product],
    warehouses: list[Warehouse],
) -> None:

    print("Creating orders...")

    now = datetime.now(timezone.utc)

    start_date = now - timedelta(
        days=365,
    )

    for batch_start in range(
        0,
        ORDER_COUNT,
        BATCH_SIZE,
    ):

        orders = []
        order_items = []
        addresses = []
        payments = []
        histories = []

        batch_end = min(
            batch_start + BATCH_SIZE,
            ORDER_COUNT,
        )

        for index in range(
            batch_start,
            batch_end,
        ):

            order_number = index + 1

            customer = random.choice(customers)
            warehouse = random.choice(warehouses)

            created_at = random_datetime(
                start_date,
                now,
            )

            final_status = choose_order_status()

            item_count = random.randint(
                1,
                4,
            )

            selected_products = random.sample(
                products,
                k=item_count,
            )

            subtotal = Decimal("0.00")

            order_id = f"ORDER-{order_number:08d}"

            for item_number, product in enumerate(
                selected_products,
                start=1,
            ):

                quantity = random.randint(
                    1,
                    5,
                )

                # Historical selling price varies from MRP.
                price_multiplier = Decimal(
                    str(
                        round(
                            random.uniform(
                                0.70,
                                1.00,
                            ),
                            2,
                        )
                    )
                )

                unit_price = (product.mrp * price_multiplier).quantize(Decimal("0.01"))

                subtotal += unit_price * quantity

                item = OrderItem(
                    order_item_id=(f"ITEM-{order_number:08d}-" f"{item_number:02d}"),
                    order_id=order_id,
                    product_id=product.product_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    created_at=created_at,
                )

                order_items.append(item)

            tax = (subtotal * Decimal("0.18")).quantize(Decimal("0.01"))

            handling = money(
                random.choice(
                    [
                        0,
                        20,
                        40,
                        60,
                        100,
                    ]
                )
            )

            discount = money(
                random.choice(
                    [
                        0,
                        0,
                        0,
                        50,
                        100,
                        200,
                        500,
                    ]
                )
            )

            total = subtotal + tax + handling - discount

            if total < Decimal("0.00"):
                total = Decimal("0.00")

            order = Order(
                order_id=order_id,
                customer_id=customer.customer_id,
                warehouse_id=warehouse.warehouse_id,
                idempotency_key=(f"SEED-IDEMP-{order_number:08d}"),
                status=final_status,
                subtotal_amount=subtotal,
                tax_amount=tax,
                handling_amount=handling,
                discount_amount=discount,
                total_amount=total,
                created_at=created_at,
                updated_at=created_at,
            )

            orders.append(order)

            # ------------------------------------------------
            # SHIPPING ADDRESS
            # ------------------------------------------------

            city, state, postal_code = random.choice(CITIES)

            address = OrderShippingAddress(
                order_id=order_id,
                recipient_name=customer.name,
                phone_number=(customer.phone_number or "+910000000000"),
                address_line1=(f"{random.randint(1, 999)} " f"Building"),
                address_line2=None,
                street=f"Street {random.randint(1, 100)}",
                city=city,
                state=state,
                postal_code=postal_code,
                country="India",
            )

            addresses.append(address)

            # ------------------------------------------------
            # STATUS HISTORY
            # ------------------------------------------------

            status_sequence = build_status_sequence(final_status)

            status_time = created_at

            for status_index, status in enumerate(status_sequence):

                is_last = status_index == len(status_sequence) - 1

                next_time = None

                if not is_last:

                    next_time = status_time + timedelta(
                        minutes=random.randint(
                            5,
                            720,
                        )
                    )

                history = OrderStatusHistory(
                    status_history_id=make_id("OSH"),
                    order_id=order_id,
                    status=status,
                    status_open_date=status_time,
                    status_close_date=next_time,
                )

                histories.append(history)

                if next_time is not None:
                    status_time = next_time

            order.updated_at = status_time

            # ------------------------------------------------
            # PAYMENT
            # ------------------------------------------------

            if final_status != "PAYMENT_PENDING":

                if final_status == "CANCELLED":

                    payment_status = random.choices(
                        ["FAILED", "SUCCESS"],
                        weights=[80, 20],
                        k=1,
                    )[0]

                else:

                    payment_status = "SUCCESS"

                if payment_status == "SUCCESS":

                    transaction_id = f"SEED-TXN-" f"{order_number:08d}"

                    failure_reason = None

                else:

                    transaction_id = None

                    failure_reason = random.choice(
                        [
                            "Card declined",
                            "Insufficient funds",
                            "Payment authentication failed",
                            "Provider rejected payment",
                        ]
                    )

                payment = Payment(
                    payment_id=(f"PAY-{order_number:08d}"),
                    order_id=order_id,
                    status=payment_status,
                    amount=total,
                    provider_transaction_id=(transaction_id),
                    failure_reason=failure_reason,
                    created_at=(created_at + timedelta(minutes=5)),
                    updated_at=(created_at + timedelta(minutes=5)),
                )

                payments.append(payment)

        # ----------------------------------------------------
        # BATCH INSERT
        # ----------------------------------------------------

        session.add_all(orders)

        # Orders must exist before FK children.
        session.flush()

        session.add_all(order_items)
        session.add_all(addresses)
        session.add_all(histories)
        session.add_all(payments)

        session.commit()

        print(f"Inserted orders " f"{batch_start + 1:,} " f"to {batch_end:,}")


# ============================================================
# MAIN
# ============================================================


def main() -> None:

    settings = get_settings()

    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
    )

    with Session(
        engine,
        expire_on_commit=False,
    ) as session:

        customers = create_customers(session)

        products = create_products(session)

        warehouses = create_warehouses(session)

        create_inventory(
            session,
            products,
            warehouses,
        )

        create_orders(
            session,
            customers,
            products,
            warehouses,
        )

    print()
    print("==============================")
    print("DATA GENERATION COMPLETE")
    print("==============================")


if __name__ == "__main__":
    main()
