from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Create one SQLAlchemy Session for an API request.

    This dependency owns the lifetime of the Session.

    Business operations decide when transactions
    should commit or rollback.
    """

    with SessionLocal() as db:
        yield db