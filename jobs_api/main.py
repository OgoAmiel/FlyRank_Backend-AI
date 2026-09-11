import datetime
import logging
import uuid

import inngest
import inngest.fast_api
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Jobs API", version="1.0")

inngest_client = inngest.Inngest(
    app_id="report-api",
    logger=logging.getLogger("uvicorn"),
)

# In-memory store for reports. Wiped on every restart - that's fine, not a bug.
reports: dict[str, dict] = {}


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
    if report_id in reports:
        reports[report_id]["status"] = "failed"


@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2,
    on_failure=_mark_report_failed,
)
async def make_report(ctx: inngest.Context) -> None:
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    await ctx.step.sleep("do-the-slow-work", datetime.timedelta(seconds=8))

    def _build_report() -> dict:
        if topic == "fail":
            raise Exception("The report oven is broken!")
        return {"summary": f"Report about {topic}", "topic": topic}

    result = await ctx.step.run("build-report", _build_report)

    reports[report_id] = {
        "id": report_id,
        "topic": topic,
        "status": "done",
        "result": result,
    }


@inngest_client.create_function(
    fn_id="heartbeat",
    trigger=inngest.TriggerCron(cron="* * * * *"),
)
async def heartbeat(ctx: inngest.Context) -> None:
    pending = sum(1 for r in reports.values() if r["status"] == "pending")
    done = sum(1 for r in reports.values() if r["status"] == "done")
    failed = sum(1 for r in reports.values() if r["status"] == "failed")
    ctx.logger.info(
        f"heartbeat: pending={pending} done={done} failed={failed}"
    )


inngest.fast_api.serve(app, inngest_client, [say_hello, make_report, heartbeat])


@app.get("/health", summary="Health check")
def health():
    """Confirms the server is alive."""
    return {"status": "ok"}


@app.post("/reports", status_code=202, summary="Request a new report")
async def create_report(payload: ReportRequest):
    if not payload.topic:
        raise HTTPException(status_code=400, detail="topic is required")

    report_id = str(uuid.uuid4())
    reports[report_id] = {
        "id": report_id,
        "topic": payload.topic,
        "status": "pending",
    }

    await inngest_client.send(
        inngest.Event(
            name="report/requested",
            data={"id": report_id, "topic": payload.topic},
        )
    )

    return {"id": report_id, "status": "pending"}


@app.get("/reports/{report_id}", summary="Get a report's status/result")
def get_report(report_id: str):
    report = reports.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
