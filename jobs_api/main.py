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
    topic: str


@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context) -> str:
    await ctx.step.sleep("wait-5-seconds", datetime.timedelta(seconds=5))
    return "Hello from the background!"


@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
)
async def make_report(ctx: inngest.Context) -> None:
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    await ctx.step.sleep("do-the-slow-work", datetime.timedelta(seconds=8))

    def _build_report() -> dict:
        return {"summary": f"Report about {topic}", "topic": topic}

    result = await ctx.step.run("build-report", _build_report)

    reports[report_id] = {
        "id": report_id,
        "topic": topic,
        "status": "done",
        "result": result,
    }


inngest.fast_api.serve(app, inngest_client, [say_hello, make_report])


@app.get("/health", summary="Health check")
def health():
    """Confirms the server is alive."""
    return {"status": "ok"}


@app.post("/reports", status_code=202, summary="Request a new report")
async def create_report(payload: ReportRequest):
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
