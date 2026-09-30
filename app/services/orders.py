from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import OrderStatus

from app.core.exceptions import (
    CustomerNotFoundError,
    ProductNotFoundError,
    InsufficientInventoryError,
    OrderNotFoundError,
    OrderCannotBeCancelledError,
    InventoryConsistencyError,
)

from app.models.order import (
    Order,
    OrderItem,
    OrderShippingAddress,
    OrderStatusHistory,
)

from app.repositories.customers import (
    CustomerRepository,
)

from app.repositories.products import (
    ProductRepository,
)

from app.repositories.inventory import (
    InventoryRepository,
)

from app.repositories.warehouse import (
    WarehouseRepository,
)

from app.repositories.orders import (
    OrderRepository,
)

from app.schemas.orders import (
    CreateOrderRequest,
    CreateOrderResponse,
    OrderResponse,
    OrderItemResponse,
    ShippingAddressResponse,
    OrderPricingResponse,
    OrderStatusHistoryResponse,
    CancelOrderResponse,
)


class OrderService:
    """
    Contains NovaCart order business logic.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

        # Every repository shares the SAME Session.
        self.customers = CustomerRepository(db)
        self.products = ProductRepository(db)
        self.inventory = InventoryRepository(db)
        self.warehouses = WarehouseRepository(db)
        self.orders = OrderRepository(db)

    # =====================================================
    # CREATE ORDER
    # =====================================================

    def create_order(
        self,
        request: CreateOrderRequest,
    ) -> CreateOrderResponse:

        try:

            # -------------------------------------------------
            # 1. IDEMPOTENCY
            # -------------------------------------------------

            existing_order = self.orders.get_by_idempotency_key(request.idempotency_key)

            if existing_order is not None:

                return CreateOrderResponse(
                    order_id=existing_order.order_id,
                    status=existing_order.status,
                    warehouse_id=(existing_order.warehouse_id),
                    total_amount=(existing_order.total_amount),
                    message="Order already exists",
                )

            # -------------------------------------------------
            # 2. CUSTOMER
            # -------------------------------------------------

            customer = self.customers.get_by_id(request.customer_id)

            if customer is None:
                raise CustomerNotFoundError(request.customer_id)

            # -------------------------------------------------
            # 3. AGGREGATE PRODUCT QUANTITIES
            # -------------------------------------------------

            requested_quantities: dict[
                str,
                int,
            ] = {}

            for item in request.items:

                requested_quantities[item.product_id] = (
                    requested_quantities.get(
                        item.product_id,
                        0,
                    )
                    + item.quantity
                )

            product_ids = list(requested_quantities.keys())

            # -------------------------------------------------
            # 4. PRODUCTS
            # -------------------------------------------------

            products = self.products.get_by_ids(product_ids)

            products_by_id = {product.product_id: product for product in products}

            missing_product_ids = [
                product_id
                for product_id in product_ids
                if product_id not in products_by_id
            ]

            if missing_product_ids:
                raise ProductNotFoundError(missing_product_ids)

            # -------------------------------------------------
            # 5. LOCK INVENTORY
            # -------------------------------------------------

            inventory_records = self.inventory.get_for_products_for_update(product_ids)

            # -------------------------------------------------
            # 6. GROUP INVENTORY BY WAREHOUSE
            # -------------------------------------------------

            warehouse_inventory = {}

            for inventory in inventory_records:

                if inventory.warehouse_id not in warehouse_inventory:
                    warehouse_inventory[inventory.warehouse_id] = {}

                warehouse_inventory[inventory.warehouse_id][
                    inventory.product_id
                ] = inventory

            # -------------------------------------------------
            # 7. ELIGIBLE WAREHOUSES
            # -------------------------------------------------

            eligible_warehouse_ids = []

            for (
                warehouse_id,
                warehouse_products,
            ) in warehouse_inventory.items():

                can_fulfill = all(
                    product_id in warehouse_products
                    and warehouse_products[product_id].can_fulfill(
                        requested_quantities[product_id]
                    )
                    for product_id in requested_quantities
                )

                if can_fulfill:
                    eligible_warehouse_ids.append(warehouse_id)

            if not eligible_warehouse_ids:
                raise InsufficientInventoryError()

            # -------------------------------------------------
            # 8. WAREHOUSES
            # -------------------------------------------------

            warehouses = self.warehouses.get_by_ids(eligible_warehouse_ids)

            warehouses_by_id = {
                warehouse.warehouse_id: warehouse for warehouse in warehouses
            }

            # -------------------------------------------------
            # 9. WAREHOUSE SCORING
            # -------------------------------------------------

            shipping = request.shipping_address

            warehouse_scores = {}

            for warehouse_id in eligible_warehouse_ids:

                warehouse = warehouses_by_id[warehouse_id]

                if warehouse.postal_code.lower() == shipping.postal_code.lower():
                    location_score = 3

                elif warehouse.city.lower() == shipping.city.lower():
                    location_score = 2

                elif warehouse.state.lower() == shipping.state.lower():
                    location_score = 1

                else:
                    location_score = 0

                remaining_stock = sum(
                    warehouse_inventory[warehouse_id][product_id].available_quantity
                    - requested_quantity
                    for (
                        product_id,
                        requested_quantity,
                    ) in requested_quantities.items()
                )

                warehouse_scores[warehouse_id] = (
                    location_score,
                    remaining_stock,
                )

            # -------------------------------------------------
            # 10. SELECT WAREHOUSE
            # -------------------------------------------------

            selected_warehouse_id = max(
                eligible_warehouse_ids,
                key=lambda warehouse_id: warehouse_scores[warehouse_id],
            )

            # -------------------------------------------------
            # 11. PRICING
            # -------------------------------------------------

            subtotal_amount = sum(
                (products_by_id[product_id].mrp * quantity)
                for (
                    product_id,
                    quantity,
                ) in requested_quantities.items()
            )

            tax_amount = Decimal("0.00")

            handling_amount = Decimal("0.00")

            discount_amount = Decimal("0.00")

            total_amount = (
                subtotal_amount + tax_amount + handling_amount - discount_amount
            )

            # -------------------------------------------------
            # 12. IDs + TIMESTAMP
            # -------------------------------------------------

            order_id = f"ORD-" f"{uuid4().hex[:12].upper()}"

            now = datetime.now(timezone.utc)

            # -------------------------------------------------
            # 13. ORDER
            # -------------------------------------------------

            order = Order(
                order_id=order_id,
                customer_id=request.customer_id,
                warehouse_id=(selected_warehouse_id),
                idempotency_key=(request.idempotency_key),
                status=(OrderStatus.CONFIRMED.value),
                subtotal_amount=(subtotal_amount),
                tax_amount=tax_amount,
                handling_amount=(handling_amount),
                discount_amount=(discount_amount),
                total_amount=total_amount,
                created_at=now,
                updated_at=now,
            )

            self.orders.add(order)

            # -------------------------------------------------
            # 14. ORDER ITEMS
            # -------------------------------------------------

            for (
                product_id,
                quantity,
            ) in requested_quantities.items():

                product = products_by_id[product_id]

                order_item = OrderItem(
                    order_item_id=(f"OI-" f"{uuid4().hex[:12].upper()}"),
                    order_id=order_id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=product.mrp,
                    created_at=now,
                )

                self.orders.add_item(order_item)

            # -------------------------------------------------
            # 15. SHIPPING ADDRESS SNAPSHOT
            # -------------------------------------------------

            shipping_address = OrderShippingAddress(
                order_id=order_id,
                recipient_name=(shipping.recipient_name),
                phone_number=(shipping.phone_number),
                address_line1=(shipping.address_line1),
                address_line2=(shipping.address_line2),
                street=shipping.street,
                city=shipping.city,
                state=shipping.state,
                postal_code=(shipping.postal_code),
                country=shipping.country,
            )

            self.orders.add_shipping_address(shipping_address)

            # -------------------------------------------------
            # 16. STATUS HISTORY
            # -------------------------------------------------

            status_history = OrderStatusHistory(
                status_history_id=(f"OSH-" f"{uuid4().hex[:12].upper()}"),
                order_id=order_id,
                status=(OrderStatus.CONFIRMED.value),
                status_open_date=now,
                status_close_date=None,
            )

            self.orders.add_status_history(status_history)

            # -------------------------------------------------
            # 17. RESERVE INVENTORY
            # -------------------------------------------------

            for (
                product_id,
                quantity,
            ) in requested_quantities.items():

                inventory = warehouse_inventory[selected_warehouse_id][product_id]

                inventory.reserved_quantity += quantity

            # -------------------------------------------------
            # 18. COMMIT
            # -------------------------------------------------

            self.db.commit()

            return CreateOrderResponse(
                order_id=order.order_id,
                status=order.status,
                warehouse_id=(order.warehouse_id),
                total_amount=(order.total_amount),
                message=("Order created successfully"),
            )

        except IntegrityError:

            self.db.rollback()

            # Possible concurrent request using
            # the same idempotency key.
            existing_order = self.orders.get_by_idempotency_key(request.idempotency_key)

            if existing_order is not None:

                return CreateOrderResponse(
                    order_id=(existing_order.order_id),
                    status=(existing_order.status),
                    warehouse_id=(existing_order.warehouse_id),
                    total_amount=(existing_order.total_amount),
                    message=("Order already exists"),
                )

            raise

        except Exception:

            self.db.rollback()
            raise

    # =====================================================
    # GET ORDER
    # =====================================================

    def get_order(
        self,
        order_id: str,
    ) -> OrderResponse:

        order = self.orders.get_complete_order(order_id)

        if order is None:
            raise OrderNotFoundError(order_id)

        # -------------------------------------------------
        # ITEMS
        # -------------------------------------------------

        items = [
            OrderItemResponse(
                product_id=item.product_id,
                product_name=(item.product.product_name),
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
            )
            for item in order.items
        ]

        # -------------------------------------------------
        # SHIPPING ADDRESS
        # -------------------------------------------------

        shipping_response = None

        if order.shipping_address is not None:

            shipping = order.shipping_address

            shipping_response = ShippingAddressResponse(
                recipient_name=(shipping.recipient_name),
                phone_number=(shipping.phone_number),
                address_line1=(shipping.address_line1),
                address_line2=(shipping.address_line2),
                street=shipping.street,
                city=shipping.city,
                state=shipping.state,
                postal_code=(shipping.postal_code),
                country=shipping.country,
            )

        # -------------------------------------------------
        # STATUS HISTORY
        # -------------------------------------------------

        history = [
            OrderStatusHistoryResponse(
                status=entry.status,
                opened_at=(entry.status_open_date),
                closed_at=(entry.status_close_date),
            )
            for entry in sorted(
                order.status_history,
                key=lambda entry: entry.status_open_date,
            )
        ]

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return OrderResponse(
            order_id=order.order_id,
            customer_id=(order.customer_id),
            warehouse_id=(order.warehouse_id),
            status=order.status,
            items=items,
            shipping_address=(shipping_response),
            pricing=(
                OrderPricingResponse(
                    subtotal_amount=(order.subtotal_amount),
                    tax_amount=(order.tax_amount),
                    handling_amount=(order.handling_amount),
                    discount_amount=(order.discount_amount),
                    total_amount=(order.total_amount),
                )
            ),
            status_history=history,
            created_at=order.created_at,
        )

    # =====================================================
    # CANCEL ORDER
    # =====================================================

    def cancel_order(
        self,
        order_id: str,
    ) -> CancelOrderResponse:

        try:

            # -------------------------------------------------
            # 1. LOCK ORDER
            # -------------------------------------------------

            order = self.orders.get_by_id_for_update(order_id)

            if order is None:
                raise OrderNotFoundError(order_id)

            # -------------------------------------------------
            # 2. ALREADY CANCELLED
            # -------------------------------------------------

            if order.status == OrderStatus.CANCELLED.value:

                return CancelOrderResponse(
                    order_id=order.order_id,
                    status=order.status,
                    message=("Order is already cancelled"),
                )

            # -------------------------------------------------
            # 3. VALIDATE STATUS
            # -------------------------------------------------

            if order.status not in {
                OrderStatus.CONFIRMED.value,
            }:
                raise (
                    OrderCannotBeCancelledError(
                        order_id=(order.order_id),
                        current_status=(order.status),
                    )
                )

            # -------------------------------------------------
            # 4. ORDER ITEMS
            # -------------------------------------------------

            items = list(order.items)

            product_ids = [item.product_id for item in items]

            # -------------------------------------------------
            # 5. LOCK INVENTORY
            # -------------------------------------------------

            inventory_records = self.inventory.get_for_order_cancellation(
                warehouse_id=(order.warehouse_id),
                product_ids=product_ids,
            )

            inventory_by_product = {
                inventory.product_id: inventory for inventory in inventory_records
            }

            # -------------------------------------------------
            # 6. RELEASE INVENTORY
            # -------------------------------------------------

            for item in items:

                inventory = inventory_by_product.get(item.product_id)

                if inventory is None:
                    raise (
                        InventoryConsistencyError(
                            "Inventory record "
                            "required for cancellation "
                            "was not found"
                        )
                    )

                if inventory.reserved_quantity < item.quantity:
                    raise (
                        InventoryConsistencyError(
                            "Reserved inventory is "
                            "lower than the quantity "
                            "being cancelled"
                        )
                    )

                inventory.reserved_quantity -= item.quantity

            # -------------------------------------------------
            # 7. CLOSE CURRENT STATUS
            # -------------------------------------------------

            now = datetime.now(timezone.utc)

            current_history = self.orders.get_open_status_history(order_id)

            if current_history is not None:
                current_history.status_close_date = now

            # -------------------------------------------------
            # 8. UPDATE ORDER
            # -------------------------------------------------

            order.status = OrderStatus.CANCELLED.value

            order.updated_at = now

            # -------------------------------------------------
            # 9. NEW STATUS HISTORY
            # -------------------------------------------------

            cancelled_history = OrderStatusHistory(
                status_history_id=(f"OSH-" f"{uuid4().hex[:12].upper()}"),
                order_id=(order.order_id),
                status=(OrderStatus.CANCELLED.value),
                status_open_date=now,
                status_close_date=None,
            )

            self.orders.add_status_history(cancelled_history)

            # -------------------------------------------------
            # 10. COMMIT
            # -------------------------------------------------

            self.db.commit()

            return CancelOrderResponse(
                order_id=order.order_id,
                status=order.status,
                message=("Order cancelled successfully"),
            )

        except Exception:

            self.db.rollback()
            raise
