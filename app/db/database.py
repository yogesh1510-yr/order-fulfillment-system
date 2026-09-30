from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import DATABASE_URL


# ---------------------------------------------------------
# SQLAlchemy Engine
# ---------------------------------------------------------
# The Engine manages database connectivity and the
# underlying connection pool used to communicate with
# PostgreSQL.
engine = create_engine(
    DATABASE_URL,
    echo=False,
)


# ---------------------------------------------------------
# Session factory
# ---------------------------------------------------------
# SessionLocal is a factory. Calling SessionLocal()
# creates a new SQLAlchemy Session.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)