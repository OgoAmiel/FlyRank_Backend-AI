from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from supabase_client import supabase

router = APIRouter(tags=["Public & Protected"])


@router.get("/public/info", summary="Get public info")
def get_public_info():
    """
    Public endpoint - no auth required.
    Returns public information accessible to everyone.
    """
    return {
        "message": "Welcome stranger! This info is public."
    }


@router.get("/protected/profile", summary="Get user profile")
def get_protected_profile(request: Request):
    """
    Protected endpoint - requires valid access token.
    Returns the authenticated user's profile information.
    """
    # Extract the Authorization header
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"error": "Access token required"}
        )
    
    token = auth_header[7:]

    try:
        # Verify the token with Supabase
        user = supabase.auth.get_user(token)
        return {
            "message": "Profile retrieved",
            "user": {
                "id": user.user.id,
                "email": user.user.email
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid or expired token"}
        )
