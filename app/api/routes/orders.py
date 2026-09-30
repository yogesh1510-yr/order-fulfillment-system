from fastapi import (
    APIRouter,
    Depends,
    status,
)

from app.api.dependencies import get_order_service

from app.schemas.orders import (
    CancelOrderResponse,
    CreateOrderRequest,
    CreateOrderResponse,
    OrderResponse,
)

from app.services.orders import OrderService

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
    service: OrderService = Depends(get_order_service),
) -> CreateOrderResponse:

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
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:

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
    service: OrderService = Depends(get_order_service),
) -> CancelOrderResponse:

    return service.cancel_order(order_id)
