from fastapi import APIRouter
from fastapi.responses import JSONResponse

from schemas import SignUpRequest, LoginRequest
from supabase_client import supabase


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post("/signup", status_code=201, summary="Create a new user account")
def signup(request: SignUpRequest):
    """
    Create a new user account with the provided email and password.
    """
    if not request.email or not request.password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required"}
        )

    try:
        response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })

        return response.user

    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "Unable to create account"}
        )


@router.post("/login", summary="Login a user")
def login(request: LoginRequest):
    """
    Login a user with the provided email and password.
    """

    if not request.email or not request.password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required"}
        )

    try:
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })

        if not response.session:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid login credentials"}
            )

        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }

    except Exception:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid login credentials"}
        )