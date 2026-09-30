from sqlalchemy import select

from app.db.database import SessionLocal

# Important:
# importing models ensures SQLAlchemy knows
# about all ORM mappings.
import app.models

from app.models.customer import Customer
from app.models.product import Product
from app.models.order import Order


def main():

    with SessionLocal() as db:

        print("\n--- CUSTOMERS ---")

        customers = db.scalars(
            select(Customer)
        ).all()

        for customer in customers:
            print(
                customer.customer_id,
                customer.name,
            )

        print("\n--- PRODUCTS ---")

        products = db.scalars(
            select(Product)
        ).all()

        for product in products:
            print(
                product.product_id,
                product.product_name,
                product.mrp,
            )

        print("\n--- ORDERS ---")

        orders = db.scalars(
            select(Order)
        ).all()

        for order in orders:

            print(
                "Order:",
                order.order_id,
                order.status,
            )

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
                    item.quantity,
                    item.unit_price,
                    item.line_total,
                )


if __name__ == "__main__":
    main()