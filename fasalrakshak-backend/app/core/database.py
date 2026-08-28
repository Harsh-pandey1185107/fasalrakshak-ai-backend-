import os

from passlib.context import CryptContext
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


# ============================================================================
# IMPORT DATABASE MODELS
# ============================================================================

from app.models.user import User
from app.models import evidence
from app.models import assessment


# ============================================================================
# CREATE DATABASE TABLES
# ============================================================================

Base.metadata.create_all(bind=engine)


# ============================================================================
# DEFAULT OFFICER SEED
# ============================================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def create_default_officer():
    username = os.getenv("OFFICER_USERNAME")
    password = os.getenv("OFFICER_PASSWORD")

    if not username or not password:
        print(
            "Officer seed skipped: "
            "OFFICER_USERNAME or OFFICER_PASSWORD is not configured."
        )
        return

    db = SessionLocal()

    try:
        existing_officer = (
            db.query(User)
            .filter(User.username == username)
            .first()
        )

        if existing_officer:
            print(
                f"Officer '{username}' already exists."
            )
            return

        officer = User(
            username=username,
            password_hash=pwd_context.hash(password),
            role="officer",
            full_name="FasalRakshak Field Officer",
            phone=None,
            address=None,
        )

        db.add(officer)
        db.commit()

        print(
            f"Officer '{username}' created successfully."
        )

    except Exception as exc:
        db.rollback()

        print(
            f"Officer creation failed: {exc}"
        )

    finally:
        db.close()


create_default_officer()