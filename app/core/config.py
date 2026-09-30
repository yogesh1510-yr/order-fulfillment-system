import os

from dotenv import load_dotenv


load_dotenv()


def get_required_env(name: str) -> str:
    """
    Get a required environment variable.

    Raises an error during application startup
    if the variable is missing or empty.
    """

    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"{name} environment variable is not configured"
        )

    return value


DATABASE_URL: str = get_required_env(
    "DATABASE_URL"
)