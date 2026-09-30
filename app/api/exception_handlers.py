from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    CustomerNotFoundError,
    ProductNotFoundError,
    InsufficientInventoryError,
    OrderNotFoundError,
    OrderCannotBeCancelledError,
    InventoryConsistencyError,
)


# =========================================================
# CUSTOMER NOT FOUND
# =========================================================


async def customer_not_found_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:

    if not isinstance(exc, CustomerNotFoundError):
        raise exc

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": str(exc),
        },
    )


# =========================================================
# PRODUCT NOT FOUND
# =========================================================


async def product_not_found_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:

    if not isinstance(exc, ProductNotFoundError):
        raise exc

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": {
                "message": str(exc),
                "product_ids": exc.product_ids,
            }
        },
    )


# =========================================================
# INSUFFICIENT INVENTORY
# =========================================================


async def insufficient_inventory_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:

    if not isinstance(exc, InsufficientInventoryError):
        raise exc

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": str(exc),
        },
    )


# =========================================================
# ORDER NOT FOUND
# =========================================================


async def order_not_found_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:

    if not isinstance(exc, OrderNotFoundError):
        raise exc

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": str(exc),
        },
    )


# =========================================================
# ORDER CANNOT BE CANCELLED
# =========================================================


async def order_cannot_be_cancelled_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:

    if not isinstance(exc, OrderCannotBeCancelledError):
        raise exc

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": str(exc),
        },
    )


# =========================================================
# INVENTORY CONSISTENCY
# =========================================================


async def inventory_consistency_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:

    if not isinstance(exc, InventoryConsistencyError):
        raise exc

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": str(exc),
        },
    )