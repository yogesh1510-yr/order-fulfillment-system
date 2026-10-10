from fastapi import Request, status
from fastapi.responses import JSONResponse
from typing import Any

from app.core.exceptions import (
    CustomerNotFoundError,
    ProductNotFoundError,
    InsufficientInventoryError,
    OrderNotFoundError,
    OrderCannotBeCancelledError,
    InventoryConsistencyError,
)


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
    }

    if details is not None:
        error["details"] = details

    return JSONResponse(
        status_code=status_code,
        content={"error": error},
    )


async def customer_not_found_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, CustomerNotFoundError):
        raise exc

    return error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        code="CUSTOMER_NOT_FOUND",
        message=str(exc),
    )


async def product_not_found_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, ProductNotFoundError):
        raise exc

    return error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        code="PRODUCT_NOT_FOUND",
        message=str(exc),
        details={
            "product_ids": exc.product_ids,
        },
    )


async def insufficient_inventory_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, InsufficientInventoryError):
        raise exc

    return error_response(
        status_code=status.HTTP_409_CONFLICT,
        code="INSUFFICIENT_INVENTORY",
        message=str(exc),
    )


async def order_not_found_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, OrderNotFoundError):
        raise exc

    return error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        code="ORDER_NOT_FOUND",
        message=str(exc),
    )


async def order_cannot_be_cancelled_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, OrderCannotBeCancelledError):
        raise exc

    return error_response(
        status_code=status.HTTP_409_CONFLICT,
        code="ORDER_CANNOT_BE_CANCELLED",
        message=str(exc),
    )


async def inventory_consistency_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, InventoryConsistencyError):
        raise exc

    return error_response(
        status_code=status.HTTP_409_CONFLICT,
        code="INVENTORY_CONSISTENCY_ERROR",
        message=str(exc),
    )