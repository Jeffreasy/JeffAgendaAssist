import os
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import logging
from datetime import timezone, timedelta
from zoneinfo import ZoneInfo  # Voor tijdzone ondersteuning
from typing import Optional, List
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Load environment variables
load_dotenv()

# Supabase setup
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Google Calendar setup
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar.events.readonly']
CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS')
if CREDENTIALS_FILE:
    # Als we in Vercel draaien, gebruik de environment variable
    import json
    credentials_dict = json.loads(CREDENTIALS_FILE)
    flow = Flow.from_client_config(
        credentials_dict,
        scopes=SCOPES,
        redirect_uri='https://jeff-agenda-assist.vercel.app/api/auth/callback'
    )
else:
    # Lokaal development, gebruik het bestand
    flow = Flow.from_client_secrets_file(
        'client_secret_1030699582107-krrjnsu8i5vutkoukb8c5kiou1etmurg.apps.googleusercontent.com.json',
        scopes=SCOPES,
        redirect_uri='https://jeff-agenda-assist.vercel.app/api/auth/callback'
    )

# Event model voor de response
class Event(BaseModel):
    summary: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    location: Optional[str] = None
    calendar_name: str
    is_recurring: bool = False

class EventUpdate(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None

# Nieuwe models toevoegen bovenaan bij de andere models
class SearchResult(BaseModel):
    events: List[Event]
    total_count: int
    query: str

class CalendarStats(BaseModel):
    total_events: int
    events_per_calendar: dict
    busy_days: List[str]
    common_locations: List[str]

class NotificationSettings(BaseModel):
    email: str
    before_minutes: int = 30
    calendars: List[str] = []
    enabled: bool = True

@app.get("/api/auth/login")
async def login():
    """Start the OAuth flow"""
    authorization_url, state = flow.authorization_url()
    return RedirectResponse(authorization_url)

@app.get("/api/auth/callback")
async def callback(request: Request):
    """Handle the OAuth callback"""
    try:
        flow.fetch_token(authorization_response=str(request.url))
        credentials = flow.credentials
        await sync_calendar(credentials)
        return {"message": "Calendar synchronized successfully"}
    except Exception as e:
        logger.error(f"Error in callback: {str(e)}")
        return {"error": str(e)}, 500

async def sync_calendar(credentials):
    """Sync calendar events to Supabase"""
    service = build('calendar', 'v3', credentials=credentials)
    
    # Eerst halen we alle agenda's op
    calendar_list = service.calendarList().list().execute()
    
    # Gebruik Amsterdam tijdzone
    amsterdam_tz = ZoneInfo("Europe/Amsterdam")
    now = datetime.datetime.now(amsterdam_tz)
    end_date = now + datetime.timedelta(days=30)
    
    # Loop door alle agenda's
    for calendar_item in calendar_list['items']:
        calendar_id = calendar_item['id']
        calendar_name = calendar_item['summary']
        
        logger.info(f"Syncing calendar: {calendar_name}")
        
        try:
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=now.isoformat(),  # Tijdzone zit nu in de timestamp
                timeMax=end_date.isoformat(),
                maxResults=100,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            for event in events:
                event['calendar_name'] = calendar_name
                await save_event_to_supabase(event)
                
        except Exception as e:
            logger.error(f"Error syncing calendar {calendar_name}: {str(e)}")
            continue

async def save_event_to_supabase(event):
    """Save event to Supabase"""
    # Helper functie voor tijd conversie
    def convert_time(time_dict):
        if not time_dict:
            return None
            
        # Haal de tijd uit de dictionary
        time_str = time_dict.get('dateTime', time_dict.get('date'))
        if not time_str:
            return None
            
        # Als het een hele dag event is (alleen datum)
        if 'T' not in time_str:
            return time_str
            
        # Parse de tijd
        if time_str.endswith('Z'):
            dt = datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        else:
            dt = datetime.datetime.fromisoformat(time_str)
            
        # Converteer naar Amsterdam tijd en voeg expliciet 1 uur toe
        amsterdam_tz = ZoneInfo("Europe/Amsterdam")
        local_dt = dt.astimezone(amsterdam_tz) + timedelta(hours=1)
        
        # Formatteer met expliciete timezone offset
        return local_dt.strftime('%Y-%m-%d %H:%M:%S+0100')  # Hardcoded +0100 voor NL wintertijd

    event_data = {
        'google_event_id': event['id'],
        'summary': event.get('summary', 'Geen titel'),
        'description': event.get('description', ''),
        'start_time': convert_time(event.get('start')),
        'end_time': convert_time(event.get('end')),
        'location': event.get('location', ''),
        'status': event.get('status', 'confirmed'),
        'calendar_id': event.get('organizer', {}).get('email', 'primary'),
        'calendar_name': event.get('calendar_name', 'Primary'),  # Nieuwe veld
        'recurring_event_id': event.get('recurringEventId', None),
        'is_recurring': bool(event.get('recurringEventId')),
        'attendees': event.get('attendees', []),
        'conference_data': event.get('conferenceData', {}),
        'color_id': event.get('colorId'),
        'visibility': event.get('visibility', 'default'),
        'updated_at': datetime.datetime.utcnow().isoformat()
    }
    
    try:
        result = supabase.table('calendar_events').upsert(event_data).execute()
        logger.info(f"Event opgeslagen: {event_data['summary']} ({event_data['calendar_name']})")
        return result
    except Exception as e:
        logger.error(f"Fout bij opslaan event: {e}")
        return None

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "API is running"}

@app.get("/api/health")
async def health():
    """Detailed health check"""
    try:
        # Test Supabase connection
        supabase_ok = bool(supabase.table('calendar_events').select("*").limit(1).execute())
        
        return {
            "status": "ok",
            "supabase": "connected" if supabase_ok else "error",
            "google_credentials": "configured" if CREDENTIALS_FILE else "missing"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/api/events", response_model=List[Event])
async def get_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    calendar_name: Optional[str] = None
):
    """Haal events op uit Supabase met optionele filters"""
    try:
        # Start met een basis query
        query = supabase.table('calendar_events').select('*')
        
        # Voeg filters toe als ze zijn opgegeven
        if start_date:
            query = query.gte('start_time', start_date)
        if end_date:
            query = query.lte('end_time', end_date)
        if calendar_name:
            query = query.eq('calendar_name', calendar_name)
            
        # Sorteer op start tijd
        query = query.order('start_time', desc=False)
        
        # Voer de query uit
        result = query.execute()
        
        # Converteer de ruwe data naar Event objecten
        events = []
        for event in result.data:
            events.append(Event(
                summary=event['summary'],
                description=event.get('description', ''),
                start_time=event['start_time'],
                end_time=event['end_time'],
                location=event.get('location', ''),
                calendar_name=event['calendar_name'],
                is_recurring=event['is_recurring']
            ))
            
        return events
        
    except Exception as e:
        logger.error(f"Error fetching events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Optioneel: endpoint voor beschikbare agenda's
@app.get("/api/calendars")
async def get_calendars():
    """Haal lijst van unieke agenda namen op"""
    try:
        result = supabase.table('calendar_events')\
            .select('calendar_name')\
            .execute()
        
        # Haal unieke calendar names op
        calendars = list(set(event['calendar_name'] for event in result.data))
        return {"calendars": calendars}
        
    except Exception as e:
        logger.error(f"Error fetching calendars: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Nieuwe endpoints voor event management
@app.delete("/api/events/{event_id}")
async def delete_event(event_id: str):
    """Verwijder een event uit Supabase"""
    try:
        result = supabase.table('calendar_events')\
            .delete()\
            .eq('google_event_id', event_id)\
            .execute()
        return {"message": f"Event {event_id} verwijderd"}
    except Exception as e:
        logger.error(f"Error deleting event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/events/{event_id}")
async def update_event(event_id: str, event: EventUpdate):
    """Update een event in Supabase"""
    try:
        # Haal alleen de gevulde velden uit het update object
        update_data = {k: v for k, v in event.dict().items() if v is not None}
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        result = supabase.table('calendar_events')\
            .update(update_data)\
            .eq('google_event_id', event_id)\
            .execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error updating event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/events/today")
async def get_today_events():
    """Haal events van vandaag op"""
    try:
        amsterdam_tz = ZoneInfo("Europe/Amsterdam")
        now = datetime.datetime.now(amsterdam_tz)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        result = supabase.table('calendar_events')\
            .select('*')\
            .gte('start_time', today_start.isoformat())\
            .lte('end_time', today_end.isoformat())\
            .order('start_time')\
            .execute()
            
        return [Event(**event) for event in result.data]
    except Exception as e:
        logger.error(f"Error fetching today's events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/events/upcoming")
async def get_upcoming_events(days: int = 7):
    """Haal events voor de komende X dagen op"""
    try:
        amsterdam_tz = ZoneInfo("Europe/Amsterdam")
        now = datetime.datetime.now(amsterdam_tz)
        end_date = now + datetime.timedelta(days=days)
        
        result = supabase.table('calendar_events')\
            .select('*')\
            .gte('start_time', now.isoformat())\
            .lte('start_time', end_date.isoformat())\
            .order('start_time')\
            .execute()
            
        return [Event(**event) for event in result.data]
    except Exception as e:
        logger.error(f"Error fetching upcoming events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 1. Statistieken
@app.get("/api/stats", response_model=CalendarStats)
async def get_stats():
    """Haal statistieken op over alle events"""
    try:
        # Haal alle events op
        result = supabase.table('calendar_events').select('*').execute()
        events = result.data

        # Bereken statistieken
        stats = {
            'total_events': len(events),
            'events_per_calendar': {},
            'busy_days': [],
            'common_locations': []
        }

        # Events per agenda
        for event in events:
            calendar = event['calendar_name']
            stats['events_per_calendar'][calendar] = stats['events_per_calendar'].get(calendar, 0) + 1

        # Drukste dagen (top 3)
        day_counts = {}
        for event in events:
            if 'T' in event['start_time']:  # Alleen events met tijd
                day = datetime.datetime.fromisoformat(event['start_time']).strftime('%A')
                day_counts[day] = day_counts.get(day, 0) + 1
        
        stats['busy_days'] = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        # Meest voorkomende locaties (top 5)
        location_counts = {}
        for event in events:
            if event.get('location'):
                location_counts[event['location']] = location_counts.get(event['location'], 0) + 1
        
        stats['common_locations'] = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return CalendarStats(**stats)

    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 2. Zoekfunctionaliteit
@app.get("/api/events/search", response_model=SearchResult)
async def search_events(
    query: str,
    calendar_name: Optional[str] = None,
    include_description: bool = True
):
    """Zoek in events op basis van query"""
    try:
        # Start met basis query
        db_query = supabase.table('calendar_events').select('*')

        # Filter op calendar_name als opgegeven
        if calendar_name:
            db_query = db_query.eq('calendar_name', calendar_name)

        # Voer de query uit
        result = db_query.execute()
        events = result.data

        # Filter events op basis van zoekterm
        matched_events = []
        query = query.lower()
        for event in events:
            if query in event['summary'].lower():
                matched_events.append(event)
            elif include_description and event['description'] and query in event['description'].lower():
                matched_events.append(event)
            elif event['location'] and query in event['location'].lower():
                matched_events.append(event)

        # Converteer naar Event objecten
        event_objects = [Event(**event) for event in matched_events]

        return SearchResult(
            events=event_objects,
            total_count=len(event_objects),
            query=query
        )

    except Exception as e:
        logger.error(f"Error searching events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 3. Notificaties
@app.post("/api/notifications/setup")
async def setup_notifications(settings: NotificationSettings):
    """Setup email notificaties voor events"""
    try:
        # Sla notificatie settings op in Supabase
        notification_data = {
            'email': settings.email,
            'before_minutes': settings.before_minutes,
            'calendars': settings.calendars,
            'enabled': settings.enabled,
            'created_at': datetime.datetime.utcnow().isoformat(),
            'updated_at': datetime.datetime.utcnow().isoformat()
        }

        result = supabase.table('notification_settings').upsert(notification_data).execute()
        
        return {
            "message": "Notification settings saved",
            "settings": settings.dict()
        }

    except Exception as e:
        logger.error(f"Error setting up notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/notifications/settings")
async def get_notification_settings(email: str):
    """Haal notificatie instellingen op"""
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
