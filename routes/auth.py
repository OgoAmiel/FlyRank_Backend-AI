from fastapi import APIRouter, HTTPException

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
        raise HTTPException(
            status_code=400,
            detail="Email and password are required"
        )

    try:
        response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })

        return response.user

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Unable to create account"
        )


@router.post("/login", summary="Login a user")
def login(request: LoginRequest):
    """
    Login a user with the provided email and password.
    """

    if not request.email or not request.password:
        raise HTTPException(
            status_code=400,
            detail="Email and password are required"
        )

    try:
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })

        if not response.session:
            raise HTTPException(
                status_code=401,
                detail="Invalid login credentials"
            )

        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid login credentials"
        )