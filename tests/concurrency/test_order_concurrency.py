from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import InsufficientInventoryError
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.order import (
    Order,
    OrderItem,
    OrderShippingAddress,
    OrderStatusHistory,
)

from app.schemas.orders import (
    CreateOrderRequest,
    OrderItemRequest,
    ShippingAddress,
)
from app.services.orders import OrderService


def test_concurrent_orders_do_not_oversell(
    test_engine,
):
    """
    Two customers simultaneously request 4 units each.

    Inventory:
        total = 5
        reserved = 0

    Both orders cannot succeed.

    Expected final state:
        successful orders = 1
        insufficient inventory failures = 1
        reserved quantity = 4
        total orders = 1
    """

    # =====================================================
    # 1. ARRANGE SHARED COMMITTED DATA
    # =====================================================

    with Session(
        test_engine,
        expire_on_commit=False,
    ) as setup_session:

        customer_1 = Customer(
            customer_id="CUST-CONCURRENT-1",
            name="Customer One",
            phone_number="9999999991",
        )

        customer_2 = Customer(
            customer_id="CUST-CONCURRENT-2",
            name="Customer Two",
            phone_number="9999999992",
        )

        product = Product(
            product_id="PROD-CONCURRENT",
            sku="SKU-CONCURRENT",
            product_name="Concurrency Product",
            size="M",
            mrp=Decimal("100.00"),
        )

        warehouse = Warehouse(
            warehouse_id="WH-CONCURRENT",
            warehouse_name="Concurrency Warehouse",
            warehouse_number="WH-NUM-CONCURRENT",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            country="India",
        )

        inventory = Inventory(
            inventory_id="INV-CONCURRENT",
            product_id="PROD-CONCURRENT",
            warehouse_id="WH-CONCURRENT",
            total_quantity=5,
            reserved_quantity=0,
        )

        setup_session.add_all(
            [
                customer_1,
                customer_2,
                product,
                warehouse,
                inventory,
            ]
        )

        # CRITICAL:
        #
        # Worker sessions use separate database connections.
        # Therefore setup data must be COMMITTED so those
        # transactions can see it.
        setup_session.commit()

    # =====================================================
    # 2. BUILD REQUESTS
    # =====================================================

    def make_request(
        customer_id: str,
        idempotency_key: str,
    ):
        return CreateOrderRequest(
            customer_id=customer_id,
            idempotency_key=idempotency_key,
            items=[
                OrderItemRequest(
                    product_id="PROD-CONCURRENT",
                    quantity=4,
                )
            ],
            shipping_address=ShippingAddress(
                recipient_name=customer_id,
                phone_number="9999999999",
                address_line1="123 Test Road",
                address_line2=None,
                street="MG Road",
                city="Bengaluru",
                state="Karnataka",
                postal_code="560001",
                country="India",
            ),
        )

    request_1 = make_request(
        customer_id="CUST-CONCURRENT-1",
        idempotency_key="IDEMP-CONCURRENT-1",
    )

    request_2 = make_request(
        customer_id="CUST-CONCURRENT-2",
        idempotency_key="IDEMP-CONCURRENT-2",
    )

    # =====================================================
    # 3. WORKER
    # =====================================================

    def place_order(request):
        """
        Every worker creates its OWN SQLAlchemy Session.

        Therefore:

            Thread 1 → Session 1 → DB transaction 1
            Thread 2 → Session 2 → DB transaction 2
        """

        with Session(
            test_engine,
            expire_on_commit=False,
        ) as worker_session:

            service = OrderService(worker_session)

            try:
                response = service.create_order(request)

                return (
                    "success",
                    response.order_id,
                )

            except InsufficientInventoryError:
                return (
                    "insufficient_inventory",
                    None,
                )

    # =====================================================
    # 4. EXECUTE BOTH ORDERS CONCURRENTLY
    # =====================================================

    with ThreadPoolExecutor(max_workers=2) as executor:

        future_1 = executor.submit(
            place_order,
            request_1,
        )

        future_2 = executor.submit(
            place_order,
            request_2,
        )

        result_1 = future_1.result(timeout=10)

        result_2 = future_2.result(timeout=10)

    results = [
        result_1,
        result_2,
    ]

    # =====================================================
    # 5. ASSERT BUSINESS RESULT
    # =====================================================

    successes = [result for result in results if result[0] == "success"]

    failures = [result for result in results if result[0] == "insufficient_inventory"]

    assert len(successes) == 1
    assert len(failures) == 1

    # =====================================================
    # 6. VERIFY FINAL DATABASE STATE
    # =====================================================

    with Session(test_engine) as verify_session:

        inventory_after = verify_session.scalar(
            select(Inventory).where(Inventory.inventory_id == "INV-CONCURRENT")
        )

        assert inventory_after is not None

        assert inventory_after.total_quantity == 5

        assert inventory_after.reserved_quantity == 4

        assert inventory_after.available_quantity == 1

        orders = list(
            verify_session.scalars(
                select(Order).where(
                    Order.customer_id.in_(
                        [
                            "CUST-CONCURRENT-1",
                            "CUST-CONCURRENT-2",
                        ]
                    )
                )
            ).all()
        )

        assert len(orders) == 1


    # =====================================================
    # 7. CLEAN UP COMMITTED CONCURRENCY TEST DATA
    # =====================================================

    with Session(test_engine) as cleanup_session:

        orders = list(
            cleanup_session.scalars(
                select(Order).where(
                    Order.customer_id.in_(
                        [
                            "CUST-CONCURRENT-1",
                            "CUST-CONCURRENT-2",
                        ]
                    )
                )
            ).all()
        )

        order_ids = [
            order.order_id
            for order in orders
        ]

        # ---------------------------------------------
        # Delete children first
        # ---------------------------------------------

        if order_ids:

            status_histories = list(
                cleanup_session.scalars(
                    select(OrderStatusHistory).where(
                        OrderStatusHistory.order_id.in_(
                            order_ids
                        )
                    )
                ).all()
            )

            for history in status_histories:
                cleanup_session.delete(history)

            shipping_addresses = list(
                cleanup_session.scalars(
                    select(OrderShippingAddress).where(
                        OrderShippingAddress.order_id.in_(
                            order_ids
                        )
                    )
                ).all()
            )

            for address in shipping_addresses:
                cleanup_session.delete(address)

            order_items = list(
                cleanup_session.scalars(
                    select(OrderItem).where(
                        OrderItem.order_id.in_(
                            order_ids
                        )
                    )
                ).all()
            )

            for item in order_items:
                cleanup_session.delete(item)

            cleanup_session.flush()

            # ---------------------------------------------
            # Now Orders can safely be deleted
            # ---------------------------------------------

            for order in orders:
                cleanup_session.delete(order)

            cleanup_session.flush()

        # ---------------------------------------------
        # Inventory
        # ---------------------------------------------

        inventory = cleanup_session.get(
            Inventory,
            "INV-CONCURRENT",
        )

        if inventory is not None:
            cleanup_session.delete(inventory)

        cleanup_session.flush()

        # ---------------------------------------------
        # Product
        # ---------------------------------------------

        product = cleanup_session.get(
            Product,
            "PROD-CONCURRENT",
        )

        if product is not None:
            cleanup_session.delete(product)

        # ---------------------------------------------
        # Warehouse
        # ---------------------------------------------

        warehouse = cleanup_session.get(
            Warehouse,
            "WH-CONCURRENT",
        )

        if warehouse is not None:
            cleanup_session.delete(warehouse)

        # ---------------------------------------------
        # Customers
        # ---------------------------------------------

        customer_1 = cleanup_session.get(
            Customer,
            "CUST-CONCURRENT-1",
        )

        if customer_1 is not None:
            cleanup_session.delete(customer_1)

        customer_2 = cleanup_session.get(
            Customer,
            "CUST-CONCURRENT-2",
        )

        if customer_2 is not None:
            cleanup_session.delete(customer_2)

        cleanup_session.commit()