import asyncio
import logging

from jobs_api.outbox import dispatch_pending_events

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10


async def main():
    logger.info("Outbox worker started")

    while True:
        try:
            await dispatch_pending_events()

        except Exception:
            logger.exception("Outbox dispatcher encountered an error")

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())