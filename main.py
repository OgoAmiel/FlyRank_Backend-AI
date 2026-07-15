from fastapi import FastAPI

app = FastAPI()

@app.get("/", summary="API info")
def root():
    """Describes what this API is and what it offers."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health", summary="Health check")
def health():
    """Confirms the server is alive."""
    return {"status": "ok"}
