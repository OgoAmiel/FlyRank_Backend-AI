import asyncio
from unittest.mock import AsyncMock

from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from jobs_api import outbox
from jobs_api.models import OutboxEvent
from jobs_api.outbox import calculate_retry_delay
from datetime import datetime, timezone, timedelta


def test_dispatch_pending_events_success(monkeypatch, tmp_path):
    # Create an isolated SQLite database
    test_db = tmp_path / "test_outbox.db"

    test_engine = create_engine(
        f"sqlite:///{test_db}",
        connect_args={"check_same_thread": False},
    )

    SQLModel.metadata.create_all(test_engine)

    # Make the dispatcher use our test database
    monkeypatch.setattr(outbox, "engine", test_engine)

    # Create a pending outbox event
    event = OutboxEvent(
        event_name="report/requested",
        payload={
            "id": "report-123",
            "topic": "Testing Outbox Delivery",
        },
        status="pending",
    )

    with Session(test_engine) as session:
        session.add(event)
        session.commit()
        session.refresh(event)
        event_id = event.id

    # Mock Inngest so no real event is sent
    mock_send = AsyncMock()

    monkeypatch.setattr(
        outbox.inngest_client,
        "send",
        mock_send,
    )

    # Run the asynchronous dispatcher
    asyncio.run(outbox.dispatch_pending_events())

    # Confirm Inngest was called once
    mock_send.assert_awaited_once()

    # Verify the database was updated
    with Session(test_engine) as session:
        stored_event = session.get(OutboxEvent, event_id)

        assert stored_event is not None
        assert stored_event.status == "delivered"
        assert stored_event.attempts == 0
        assert stored_event.delivered_at is not None



def test_dispatch_pending_events_failure(monkeypatch, tmp_path):
    # Create an isolated SQLite database
    test_db = tmp_path / "test_outbox_failure.db"

    test_engine = create_engine(
        f"sqlite:///{test_db}",
        connect_args={"check_same_thread": False},
    )

    SQLModel.metadata.create_all(test_engine)

    # Use the test database instead of PostgreSQL
    monkeypatch.setattr(outbox, "engine", test_engine)

    # Create a pending event
    event = OutboxEvent(
        event_name="report/requested",
        payload={
            "id": "report-456",
            "topic": "Inngest Failure Test",
        },
        status="pending",
    )

    with Session(test_engine) as session:
        session.add(event)
        session.commit()
        session.refresh(event)
        event_id = event.id

    # Simulate Inngest being unavailable
    mock_send = AsyncMock(
        side_effect=Exception("Inngest unavailable")
    )

    monkeypatch.setattr(
        outbox.inngest_client,
        "send",
        mock_send,
    )

    # Run the dispatcher
    asyncio.run(outbox.dispatch_pending_events())

    # Verify delivery was attempted
    mock_send.assert_awaited_once()

    # Check that the event was preserved for retry
    with Session(test_engine) as session:
        stored_event = session.get(OutboxEvent, event_id)

        assert stored_event is not None
        assert stored_event.status == "pending"
        assert stored_event.attempts == 1
        assert stored_event.delivered_at is None

        assert stored_event.next_retry_at is not None

        retry_delay = (
            stored_event.next_retry_at
            .replace(tzinfo=timezone.utc)
            - datetime.now(timezone.utc)
        ).total_seconds()

        assert 0 < retry_delay <= 10



def test_calculate_retry_delay():
    # First failed attempt: 10 seconds
    assert calculate_retry_delay(1) == 10

    # Second failed attempt: 20 seconds
    assert calculate_retry_delay(2) == 20

    # Third failed attempt: 40 seconds
    assert calculate_retry_delay(3) == 40

    # Fourth failed attempt: 80 seconds
    assert calculate_retry_delay(4) == 80

    # Fifth failed attempt: 160 seconds
    assert calculate_retry_delay(5) == 160

    # Sixth failed attempt: capped at 300 seconds
    assert calculate_retry_delay(6) == 300

    # Further attempts remain capped
    assert calculate_retry_delay(10) == 300



def test_dispatch_skips_events_before_retry_time(monkeypatch, tmp_path):

    test_db = tmp_path / "test_future_retry.db"

    test_engine = create_engine(
        f"sqlite:///{test_db}",
        connect_args={"check_same_thread": False},
    )

    SQLModel.metadata.create_all(test_engine)

    monkeypatch.setattr(outbox, "engine", test_engine)

    # Create an event whose next retry is one hour away
    event = OutboxEvent(
        event_name="report/requested",
        payload={
            "id": "report-789",
            "topic": "Future Retry Test",
        },
        status="pending",
        attempts=1,
        next_retry_at=(
            datetime.now(timezone.utc)
            + timedelta(hours=1)
        ),
    )

    with Session(test_engine) as session:
        session.add(event)
        session.commit()
        event_id = event.id

    # Mock the Inngest client
    mock_send = AsyncMock()

    monkeypatch.setattr(
        outbox.inngest_client,
        "send",
        mock_send,
    )

    # Run the dispatcher
    asyncio.run(outbox.dispatch_pending_events())

    # Inngest should NOT receive this event
    mock_send.assert_not_awaited()

    # Event should remain unchanged
    with Session(test_engine) as session:
        stored_event = session.get(OutboxEvent, event_id)

        assert stored_event is not None
        assert stored_event.status == "pending"
        assert stored_event.attempts == 1
        assert stored_event.delivered_at is None
        assert stored_event.next_retry_at is not None