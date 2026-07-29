from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase_client import supabase

router = APIRouter(tags=["Public & Protected"])
bearer_scheme = HTTPBearer(auto_error=False)


# Reusable dependency for token verification
async def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """
    Dependency that verifies the Authorization header contains a valid token.
    Raises 401 if token is missing, invalid, or expired.
    Returns the authenticated user.
    """
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Access token required")

    token = credentials.credentials
    
    try:
        user_response = supabase.auth.get_user(token)
        return user_response.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


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
def get_protected_profile(user = Depends(verify_token)):
    """
    Protected endpoint - requires valid access token.
    Returns the authenticated user's profile information.
    Token verification is handled by verify_token dependency.
    """
    return {
        "message": "Profile retrieved",
        "user": {
            "id": user.id,
            "email": user.email
        }
    }


@router.get("/protected/dashboard", summary="Get user dashboard")
def get_protected_dashboard(user = Depends(verify_token)):
    """
    Protected endpoint - requires valid access token.
    Returns the authenticated user's dashboard data.
    Token verification is handled by verify_token dependency (reused).
    """
    return {
        "message": "Dashboard retrieved",
        "user_id": user.id,
        "email": user.email,
        "dashboard": {
            "stats": "Your dashboard stats here",
            "recent_activity": "Activity logs"
        }
    }


@router.post("/auth/logout", summary="Logout user")
def logout(user = Depends(verify_token)):
    """
    Protected logout endpoint - signs out the authenticated user.
    Requires valid access token.
    Returns 204 No Content on success.
    """
    try:
        supabase.auth.sign_out()
        return Response(status_code=204)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Logout failed"}
        )
