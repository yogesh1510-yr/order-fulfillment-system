from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.services.orders import OrderService


def get_db() -> Generator[Session, None, None]:
    """
    Create one SQLAlchemy Session for an API request.

    The session is automatically closed when the
    request finishes.
    """

    with SessionLocal() as db:
        yield db


def get_order_service(
    db: Session = Depends(get_db),
) -> OrderService:
    """
    Create an OrderService using the database session
    associated with the current request.
    """

    return OrderService(db)