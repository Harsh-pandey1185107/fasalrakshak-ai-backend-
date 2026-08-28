from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    evidence_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("evidence.evidence_id"),
        nullable=False,
        index=True,
    )

    crop: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    damage_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    damage_percentage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    evidence_valid: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    risk_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
