import os
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import logging
from datetime import timezone, timedelta
from zoneinfo import ZoneInfo  # Voor tijdzone ondersteuning

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
    # Converteer tijden naar Amsterdam tijdzone
    amsterdam_tz = ZoneInfo("Europe/Amsterdam")
    
    # Helper functie voor tijd conversie
    def convert_time(time_str):
        if not time_str:
            return time_str
        # Als het een datetime is (met 'T' en 'Z')
        if 'T' in time_str:
            if time_str.endswith('Z'):
                # Als de tijd in UTC (Z) is
                dt = datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            else:
                # Als de tijd al een timezone heeft
                dt = datetime.datetime.fromisoformat(time_str)
            
            # Converteer naar Amsterdam tijd en voeg 1 uur toe voor correctie
            amsterdam_time = dt.astimezone(amsterdam_tz) + timedelta(hours=1)
            return amsterdam_time.isoformat()
        return time_str  # Als het een datum is (zonder tijd)

    event_data = {
        'google_event_id': event['id'],
        'summary': event.get('summary', 'Geen titel'),
        'description': event.get('description', ''),
        'start_time': convert_time(event['start'].get('dateTime', event['start'].get('date'))),
        'end_time': convert_time(event['end'].get('dateTime', event['end'].get('date'))),
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
