import logging

from app.core.config import get_settings
from app.core.request_context import get_request_id


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def configure_logging() -> None:
    settings = get_settings()

    log_level = (
        logging.DEBUG
        if settings.debug
        else logging.INFO
    )

    handler = logging.StreamHandler()

    handler.addFilter(RequestIDFilter())

    formatter = logging.Formatter(
        "%(asctime)s "
        "%(levelname)s "
        "request_id=%(request_id)s "
        "%(name)s "
        "%(message)s"
    )

    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    root_logger.handlers.clear()
    root_logger.addHandler(handler)