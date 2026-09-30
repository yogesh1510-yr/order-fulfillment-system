from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.warehouse import Warehouse


class WarehouseRepository:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def get_by_ids(
        self,
        warehouse_ids: list[str],
    ) -> list[Warehouse]:

        statement = select(Warehouse).where(Warehouse.warehouse_id.in_(warehouse_ids))

        return list(self.db.scalars(statement).all())
