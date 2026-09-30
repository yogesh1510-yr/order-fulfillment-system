from sqlalchemy.orm import Session

from app.models.customer import Customer


class CustomerRepository:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def get_by_id(
        self,
        customer_id: str,
    ) -> Customer | None:

        return self.db.get(
            Customer,
            customer_id,
        )
