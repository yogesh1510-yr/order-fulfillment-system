from sqlalchemy import select
from sqlalchemy.orm import (
    joinedload,
    selectinload,
)

from app.db.database import SessionLocal
from app.models.order import (
    Order,
    OrderItem,
)


def main() -> None:
    with SessionLocal() as db:

        statement = (
            select(Order)
            .options(
                joinedload(Order.customer),
                joinedload(Order.warehouse),
                joinedload(Order.shipping_address),
                selectinload(Order.items).joinedload(
                    OrderItem.product
                ),
                selectinload(Order.status_history),
            )
        )

        orders = db.scalars(statement).all()

        for order in orders:
            print("=" * 60)

            print("Order:", order.order_id)
            print("Status:", order.status)

            print(
                "Customer:",
                order.customer.name,
            )

            print(
                "Warehouse:",
                order.warehouse.warehouse_name,
            )

            print("Items:")

            for item in order.items:
                print(
                    "  ",
                    item.product.product_name,
                    "x",
                    item.quantity,
                    "=",
                    item.line_total,
                )

            if order.shipping_address:
                print(
                    "Shipping city:",
                    order.shipping_address.city,
                )

            print("Status history:")

            for history in order.status_history:
                print(
                    "  ",
                    history.status,
                    history.status_open_date,
                )


if __name__ == "__main__":
    main()