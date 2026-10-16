
import logging
from datetime import datetime, timedelta, timezone

import inngest
from sqlalchemy import or_
from sqlmodel import Session, select

from database import engine
from jobs_api.models import OutboxEvent
from jobs_api.main import inngest_client


logger = logging.getLogger(__name__)

BASE_RETRY_DELAY = 10
MAX_RETRY_DELAY = 300


def calculate_retry_delay(attempts: int) -> int:
    """
    Calculate exponential retry delay in seconds.
    Maximum delay: 5 minutes.
    """
    return min(
        BASE_RETRY_DELAY * (2 ** (attempts - 1)),
        MAX_RETRY_DELAY,
    )


async def dispatch_pending_events():
    """
    Deliver pending events that are eligible for processing.
    """

    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        events = session.exec(
            select(OutboxEvent).where(
                OutboxEvent.status == "pending",
                or_(
                    OutboxEvent.next_retry_at.is_(None),
                    OutboxEvent.next_retry_at <= now,
                ),
            )
        ).all()

        for event in events:
            try:
                await inngest_client.send(
                    inngest.Event(
                        id=event.id,
                        name=event.event_name,
                        data=event.payload,
                    )
                )

                event.status = "delivered"
                event.delivered_at = datetime.now(timezone.utc)
                event.next_retry_at = None

                session.add(event)
                session.commit()

                logger.info(
                    "Delivered outbox event %s",
                    event.id,
                )

            except Exception:
                session.rollback()

                stored_event = session.get(
                    OutboxEvent,
                    event.id,
                )

                if stored_event is not None:
                    stored_event.attempts += 1

                    delay = calculate_retry_delay(
                        stored_event.attempts
                    )

                    stored_event.next_retry_at = (
                        datetime.now(timezone.utc)
                        + timedelta(seconds=delay)
                    )

                    session.add(stored_event)
                    session.commit()

                    logger.warning(
                        "Event %s failed. Retrying in %s seconds.",
                        stored_event.id,
                        delay,
                    )

                logger.exception(
                    "Failed to deliver outbox event %s",
                    event.id,
                )