import datetime
import logging

import inngest
import inngest.fast_api
from fastapi import FastAPI

app = FastAPI(title="Jobs API", version="1.0")

inngest_client = inngest.Inngest(
    app_id="report-api",
    logger=logging.getLogger("uvicorn"),
)


@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context) -> str:
    await ctx.step.sleep("wait-5-seconds", datetime.timedelta(seconds=5))
    return "Hello from the background!"


inngest.fast_api.serve(app, inngest_client, [say_hello])


@app.get("/health", summary="Health check")
def health():
    """Confirms the server is alive."""
    return {"status": "ok"}
