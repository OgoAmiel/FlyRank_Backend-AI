import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, JSON, String, Text
from sqlmodel import Field, SQLModel


class ReportJob(SQLModel, table=True):
    __tablename__ = "report_jobs"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )

    topic: str = Field(
        sa_column=Column(Text, nullable=False),
    )

    status: str = Field(
        default="pending",
        sa_column=Column(String(20), nullable=False),
    )

    result: dict | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class OutboxEvent(SQLModel, table=True):
    __tablename__ = "outbox_events"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )

    event_name: str = Field(
        sa_column=Column(String(100), nullable=False)
    )

    payload: dict = Field(
        sa_column=Column(JSON, nullable=False)
    )

    status: str = Field(
        default="pending",
        sa_column=Column(String(20), nullable=False)
    )

    attempts: int = Field(default=0)

    next_retry_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=True,
        ),
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
        ),
    )

    delivered_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=True,
        ),
    )