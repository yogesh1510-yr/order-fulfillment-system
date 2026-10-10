import os
from collections.abc import Generator

import pytest
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.db.base import Base

# Import models so SQLAlchemy knows about every table.
import app.models  # noqa: F401

load_dotenv(".env.test")


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    """
    Create the SQLAlchemy Engine used by the integration test suite.
    """

    TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", None)

    if not TEST_DATABASE_URL:
        raise RuntimeError("TEST_DATABASE_URL environment variable is not configured")

    engine = create_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)

    engine.dispose()


@pytest.fixture
def db_session(
    test_engine: Engine,
) -> Generator[Session, None, None]:
    """
    Give each test its own database transaction.

    Everything performed during the test is rolled back afterward.
    """

    connection = test_engine.connect()

    transaction = connection.begin()

    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()

        transaction.rollback()

        connection.close()
