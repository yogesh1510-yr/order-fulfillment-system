from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.payments.fake_gateway import FakePaymentGateway
from app.payments.gateway import PaymentGateway
from app.services.orders import OrderService

# =========================================================
# DATABASE
# =========================================================


def get_db() -> Generator[Session, None, None]:
    """
    Create one SQLAlchemy Session for an API request.

    The session is automatically closed when the
    request finishes.
    """

    with SessionLocal() as db:
        yield db


# =========================================================
# PAYMENT GATEWAY
# =========================================================


def get_payment_gateway() -> PaymentGateway:
    """
    Return the payment gateway used by the application.

    For now we use FakePaymentGateway so that we can
    develop and test the complete payment workflow
    without contacting a real external payment provider.

    Later this dependency can return a real gateway
    implementation without changing OrderService.
    """

    return FakePaymentGateway(
        should_succeed=True,
    )


# =========================================================
# ORDER SERVICE
# =========================================================


def get_order_service(
    db: Session = Depends(get_db),
    payment_gateway: PaymentGateway = Depends(get_payment_gateway),
) -> OrderService:
    """
    Create an OrderService with all of its dependencies.

    FastAPI resolves both:
        - database session
        - payment gateway

    and injects them into OrderService.
    """

    return OrderService(
        db=db,
        payment_gateway=payment_gateway,
    )
