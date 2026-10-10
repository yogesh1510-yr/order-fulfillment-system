from fastapi import FastAPI

from app.api.routes.health import (
    router as health_router,
)
from app.api.routes.orders import (
    router as orders_router,
)
from app.core.exceptions import (
    CustomerNotFoundError,
    ProductNotFoundError,
    InsufficientInventoryError,
    OrderNotFoundError,
    OrderCannotBeCancelledError,
    InventoryConsistencyError,
)

from app.api.exception_handlers import (
    customer_not_found_handler,
    product_not_found_handler,
    insufficient_inventory_handler,
    order_not_found_handler,
    order_cannot_be_cancelled_handler,
    inventory_consistency_handler,
)

from app.core.logging import configure_logging
from app.middleware.request_id import RequestIDMiddleware

configure_logging()

app = FastAPI(
    title=("E-Commerce Order and Order Fulfillment Platform"),
    version="1.0.0",
)

app.add_middleware(RequestIDMiddleware)

app.add_exception_handler(
    CustomerNotFoundError,
    customer_not_found_handler,
)

app.add_exception_handler(
    ProductNotFoundError,
    product_not_found_handler,
)

app.add_exception_handler(
    InsufficientInventoryError,
    insufficient_inventory_handler,
)

app.add_exception_handler(
    OrderNotFoundError,
    order_not_found_handler,
)

app.add_exception_handler(
    OrderCannotBeCancelledError,
    order_cannot_be_cancelled_handler,
)

app.add_exception_handler(
    InventoryConsistencyError,
    inventory_consistency_handler,
)

app.include_router(health_router)
app.include_router(orders_router)
