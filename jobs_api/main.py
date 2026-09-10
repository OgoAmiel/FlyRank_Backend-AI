from fastapi import FastAPI

app = FastAPI(title="Jobs API", version="1.0")


@app.get("/health", summary="Health check")
def health():
    """Confirms the server is alive."""
    return {"status": "ok"}
