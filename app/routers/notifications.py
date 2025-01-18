from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.config import supabase, logger
from app.schemas import NotificationSettings

router = APIRouter()

@router.post("/setup")
async def setup_notifications(settings: NotificationSettings):
    """Setup email notificaties voor events"""
    try:
        notification_data = {
            'email': settings.email,
            'before_minutes': settings.before_minutes,
            'calendars': settings.calendars,
            'enabled': settings.enabled,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        supabase.table('notification_settings').upsert(notification_data).execute()

        return {
            "message": "Notification settings saved",
            "settings": settings.dict()
        }
    except Exception as e:
        logger.error(f"Error setting up notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/settings")
async def get_notification_settings(email: str):
    """Haal notificatie-instellingen op"""
    try:
        result = supabase.table('notification_settings')\
                         .select('*')\
                         .eq('email', email)\
                         .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="No notification settings found")

        return NotificationSettings(**result.data[0])
    except Exception as e:
        logger.error(f"Error fetching notification settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
