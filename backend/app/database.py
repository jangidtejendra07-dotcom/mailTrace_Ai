import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Defaults to local SQLite so the project runs instantly with zero setup.
# For production/SIH demo with Postgres, set DATABASE_URL, e.g.:
#   postgresql+psycopg2://mailtrace:mailtrace@localhost:5432/mailtrace
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mailtrace.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
