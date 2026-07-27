from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import HTTPException
from supabase_client import supabase

router = APIRouter(tags=["Public & Protected"])


# Reusable dependency for token verification
async def verify_token(request: Request):
    """
    Dependency that verifies the Authorization header contains a valid token.
    Raises 401 if token is missing, invalid, or expired.
    Returns the authenticated user.
    """
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Access token required")
    
    token = auth_header[7:]
    
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
