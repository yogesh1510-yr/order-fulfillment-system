from sqlalchemy import select

from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.models.order import (
    Order,
    OrderItem,
    OrderShippingAddress,
    OrderStatusHistory,
)


class OrderRepository:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    # =====================================================
    # BASIC GET
    # =====================================================

    def get_by_id(
        self,
        order_id: str,
    ) -> Order | None:

        return self.db.get(
            Order,
            order_id,
        )

    # =====================================================
    # COMPLETE ORDER
    # =====================================================

    def get_complete_order(
        self,
        order_id: str,
    ) -> Order | None:

        statement = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.shipping_address),
                selectinload(Order.status_history),
                selectinload(Order.warehouse),
            )
            .where(Order.order_id == order_id)
        )

        return self.db.scalar(statement)

    # =====================================================
    # LOCK ORDER
    # =====================================================

    def get_by_id_for_update(
        self,
        order_id: str,
    ) -> Order | None:

        statement = select(Order).where(Order.order_id == order_id).with_for_update()

        return self.db.scalar(statement)

    # =====================================================
    # IDEMPOTENCY
    # =====================================================

    def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Order | None:

        statement = select(Order).where(Order.idempotency_key == idempotency_key)

        return self.db.scalar(statement)

    # =====================================================
    # OPEN STATUS
    # =====================================================

    def get_open_status_history(
        self,
        order_id: str,
    ) -> OrderStatusHistory | None:

        statement = (
            select(OrderStatusHistory)
            .where(
                OrderStatusHistory.order_id == order_id,
                OrderStatusHistory.status_close_date.is_(None),
            )
            .with_for_update()
        )

        return self.db.scalar(statement)

    # =====================================================
    # INSERT/STAGE METHODS
    # =====================================================

    def add(
        self,
        order: Order,
    ) -> None:

        self.db.add(order)

    def add_item(
        self,
        order_item: OrderItem,
    ) -> None:

        self.db.add(order_item)

    def add_shipping_address(
        self,
        shipping_address: OrderShippingAddress,
    ) -> None:

        self.db.add(shipping_address)

    def add_status_history(
        self,
        history: OrderStatusHistory,
    ) -> None:

        self.db.add(history)
