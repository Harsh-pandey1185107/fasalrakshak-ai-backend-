from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./fasalrakshak.db"


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# Import all database models so SQLAlchemy knows about them
from app.models import user
from app.models import evidence
from app.models import assessment


# Automatically create missing tables when the backend starts
Base.metadata.create_all(bind=engine)