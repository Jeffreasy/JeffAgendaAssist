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
