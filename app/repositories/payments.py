from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment import Payment


class PaymentRepository:
    """
    Database access for payments.
    """

    def __init__(self, db: Session):
        self.db = db

    def add(self, payment: Payment) -> None:
        self.db.add(payment)

    def get_by_id(
        self,
        payment_id: str,
    ) -> Payment | None:

        statement = select(Payment).where(Payment.payment_id == payment_id)

        return self.db.scalar(statement)

    def get_for_order(
        self,
        order_id: str,
    ) -> list[Payment]:

        statement = (
            select(Payment)
            .where(Payment.order_id == order_id)
            .order_by(Payment.created_at)
        )

        return list(self.db.scalars(statement).all())
