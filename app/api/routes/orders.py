from fastapi import (
    APIRouter,
    Depends,
    status,
)

from sqlalchemy.orm import Session

from app.api.dependencies import get_db

from app.schemas.orders import (
    CreateOrderRequest,
    CreateOrderResponse,
    OrderResponse,
    CancelOrderResponse,
)

from app.services.orders import (
    OrderService,
)

router = APIRouter(
    prefix="/api/v1/orders",
    tags=["Orders"],
)


# =========================================================
# CREATE ORDER
# =========================================================


@router.post(
    "",
    response_model=CreateOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    request: CreateOrderRequest,
    db: Session = Depends(get_db),
):
    service = OrderService(db)

    return service.create_order(request)


# =========================================================
# GET ORDER
# =========================================================


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
):
    service = OrderService(db)

    return service.get_order(order_id)


# =========================================================
# CANCEL ORDER
# =========================================================


@router.post(
    "/{order_id}/cancel",
    response_model=CancelOrderResponse,
)
def cancel_order(
    order_id: str,
    db: Session = Depends(get_db),
):
    service = OrderService(db)

    return service.cancel_order(order_id)
