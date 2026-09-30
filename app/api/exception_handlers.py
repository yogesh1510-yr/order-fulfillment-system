from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    CustomerNotFoundError,
    ProductNotFoundError,
    InsufficientInventoryError,
    OrderNotFoundError,
    OrderCannotBeCancelledError,
    InventoryConsistencyError,
)


async def customer_not_found_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:

    if not isinstance(
        exc,
        CustomerNotFoundError,
    ):
        raise exc

    return JSONResponse(
        status_code=404,
        content={
            "detail": str(exc),
        },
    )


async def product_not_found_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:

    if not isinstance(
        exc,
        ProductNotFoundError,
    ):
        raise exc

    return JSONResponse(
        status_code=404,
        content={
            "detail": {
                "message": str(exc),
                "product_ids": exc.product_ids,
            }
        },
    )


async def insufficient_inventory_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:

    if not isinstance(
        exc,
        InsufficientInventoryError,
    ):
        raise exc

    return JSONResponse(
        status_code=409,
        content={
            "detail": str(exc),
        },
    )


async def order_not_found_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:

    if not isinstance(
        exc,
        OrderNotFoundError,
    ):
        raise exc

    return JSONResponse(
        status_code=404,
        content={
            "detail": str(exc),
        },
    )


async def order_cannot_be_cancelled_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:

    if not isinstance(
        exc,
        OrderCannotBeCancelledError,
    ):
        raise exc

    return JSONResponse(
        status_code=409,
        content={
            "detail": str(exc),
        },
    )


async def inventory_consistency_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:

    if not isinstance(
        exc,
        InventoryConsistencyError,
    ):
        raise exc

    return JSONResponse(
        status_code=409,
        content={
            "detail": str(exc),
        },
    )
