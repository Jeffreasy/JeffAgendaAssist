from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.config import flow, logger
from app.services.calendar_service import sync_calendar

router = APIRouter()

@router.get("/login")
async def login():
    """Start de OAuth flow"""
    authorization_url, state = flow.authorization_url()
    return RedirectResponse(authorization_url)

@router.get("/callback")
async def callback(request: Request):
    """Handle de OAuth callback"""
    try:
        flow.fetch_token(authorization_response=str(request.url))
        credentials = flow.credentials
        await sync_calendar(credentials)
        return {"message": "Calendar synchronized successfully"}
    except Exception as e:
        logger.error(f"Error in callback: {str(e)}")
        return {"error": str(e)}, 500
