class NovaCartError(Exception):
    """
    Base exception for NovaCart application errors.
    """

    pass


class CustomerNotFoundError(NovaCartError):

    def __init__(
        self,
        customer_id: str,
    ):
        self.customer_id = customer_id

        super().__init__(f"Customer '{customer_id}' was not found")


class ProductNotFoundError(NovaCartError):

    def __init__(
        self,
        product_ids: list[str],
    ):
        self.product_ids = product_ids

        super().__init__("One or more products were not found")


class InsufficientInventoryError(NovaCartError):

    def __init__(self):
        super().__init__("No warehouse can fulfill the entire order")


class OrderNotFoundError(NovaCartError):

    def __init__(
        self,
        order_id: str,
    ):
        self.order_id = order_id

        super().__init__(f"Order '{order_id}' was not found")


class OrderCannotBeCancelledError(NovaCartError):

    def __init__(
        self,
        order_id: str,
        current_status: str,
    ):
        self.order_id = order_id
        self.current_status = current_status

        super().__init__(
            f"Order '{order_id}' cannot be cancelled " f"from status '{current_status}'"
        )


class InventoryConsistencyError(NovaCartError):

    def __init__(
        self,
        message: str,
    ):
        super().__init__(message)
