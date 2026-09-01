import os

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from llm.schemas import TriageInput, TriageOutput
from llm.triage_service import TriageProcessingError, generate_triage_output


router = APIRouter(prefix="/triage", tags=["Triage"])


def _invalid_field_response(error: ValidationError) -> JSONResponse:
    first_error = error.errors()[0]
    field_path = [str(part) for part in first_error.get("loc", []) if part != "body"]
    field_name = ".".join(field_path) if field_path else "body"
    return JSONResponse(
        status_code=400,
        content={"error": f"Invalid field: {field_name}"},
    )


@router.post("/", response_model=TriageOutput, summary="Classify a support message")
def triage_message(payload: dict = Body(...)):
    """Stage 3 endpoint: validate input, parse/validate model output, repair once, then return schema JSON."""
    try:
        request = TriageInput.model_validate(payload)
    except ValidationError as exc:
        return _invalid_field_response(exc)

    if os.getenv("LLM_STUB", "0") == "1":
        return TriageOutput(
            category="other",
            urgency="normal",
            confidence=0.25,
            reason="Stub mode enabled: model call skipped.",
        )

    try:
        output = generate_triage_output(request.text)
    except TriageProcessingError as exc:
        return JSONResponse(status_code=422, content={"error": exc.message})
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=502, content={"error": f"Model call failed: {exc}"})

    return output
