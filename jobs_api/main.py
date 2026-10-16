import datetime
import logging
import uuid

from sqlalchemy import func
from sqlmodel import select
from sqlmodel import Session
from database import engine
from jobs_api.models import ReportJob, OutboxEvent

import inngest
import inngest.fast_api
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Jobs API", version="1.0")

inngest_client = inngest.Inngest(
    app_id="report-api",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
)


class ReportRequest(BaseModel):
    topic: str | None = None


@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context) -> str:
    await ctx.step.sleep("wait-5-seconds", datetime.timedelta(seconds=5))
    return "Hello from the background!"


async def _mark_report_failed(ctx: inngest.Context) -> None:
    original_event = ctx.event.data.get("event", {})
    report_id = original_event.get("data", {}).get("id")

    if not report_id:
        ctx.logger.error("Failure event missing report ID")
        return

    with Session(engine) as session:
        report = session.get(ReportJob, report_id)

        if report is None:
            ctx.logger.error("Report %s not found", report_id)
            return

        report.status = "failed"
        report.updated_at = datetime.datetime.now(
            datetime.timezone.utc
        )

        session.add(report)
        session.commit()

    ctx.logger.info(
        "Report %s marked as failed",
        report_id
    )


@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2,
    on_failure=_mark_report_failed,
)
async def make_report(ctx: inngest.Context) -> None:
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    await ctx.step.sleep(
        "do-the-slow-work",
        datetime.timedelta(seconds=8)
    )

    def _build_report() -> dict:
        if topic == "fail":
            raise Exception("The report oven is broken!")

        return {
            "summary": f"Report about {topic}",
            "topic": topic,
        }

    result = await ctx.step.run(
        "build-report",
        _build_report
    )

    # Save the completed report to PostgreSQL
    with Session(engine) as session:
        report = session.get(ReportJob, report_id)

        if report is None:
            raise ValueError(f"Report {report_id} not found")

        report.status = "done"
        report.result = result
        report.updated_at = datetime.datetime.now(
            datetime.timezone.utc
        )

        session.add(report)
        session.commit()

    ctx.logger.info(
        "Report %s completed successfully",
        report_id
    )


@inngest_client.create_function(
    fn_id="heartbeat",
    trigger=inngest.TriggerCron(cron="* * * * *"),
)
async def heartbeat(ctx: inngest.Context) -> None:

    with Session(engine) as session:
        pending = session.exec(
            select(func.count())
            .select_from(ReportJob)
            .where(ReportJob.status == "pending")
        ).one()

        done = session.exec(
            select(func.count())
            .select_from(ReportJob)
            .where(ReportJob.status == "done")
        ).one()

        failed = session.exec(
            select(func.count())
            .select_from(ReportJob)
            .where(ReportJob.status == "failed")
        ).one()

    ctx.logger.info(
        "heartbeat: pending=%s done=%s failed=%s",
        pending,
        done,
        failed,
    )

inngest.fast_api.serve(app, inngest_client, [say_hello, make_report, heartbeat])


@app.get("/health", summary="Health check")
def health():
    """Confirms the server is alive."""
    return {"status": "ok"}


@app.post("/reports", status_code=202, summary="Request a new report")
async def create_report(payload: ReportRequest):
    if not payload.topic or not payload.topic.strip():
        raise HTTPException(
            status_code=400,
            detail="topic is required",
        )

    report_id = str(uuid.uuid4())

    report = ReportJob(
        id=report_id,
        topic=payload.topic,
        status="pending",
    )

    outbox_event = OutboxEvent(
        event_name="report/requested",
        payload={
            "id": report_id,
            "topic": payload.topic,
        },
        status="pending",
    )

    # Save both records in one transaction
    with Session(engine) as session:
        session.add(report)
        session.add(outbox_event)
        session.commit()

    return {
        "id": report_id,
        "status": "pending",
    }


@app.get("/reports/{report_id}", summary="Get a report's status/result")
def get_report(report_id: str):
    with Session(engine) as session:
        report = session.get(ReportJob, report_id)

        if report is None:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        return report
