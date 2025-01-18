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
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
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
    
    now = datetime.datetime.utcnow()
    end_date = now + datetime.timedelta(days=30)
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now.isoformat() + 'Z',
        timeMax=end_date.isoformat() + 'Z',
        maxResults=100,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    for event in events:
        await save_event_to_supabase(event)

async def save_event_to_supabase(event):
    """Save event to Supabase"""
    event_data = {
        'google_event_id': event['id'],
        'summary': event.get('summary', 'Geen titel'),
        'description': event.get('description', ''),
        'start_time': event['start'].get('dateTime', event['start'].get('date')),
        'end_time': event['end'].get('dateTime', event['end'].get('date')),
        'location': event.get('location', ''),
        'status': event.get('status', 'confirmed'),
        'calendar_id': event.get('organizer', {}).get('email', 'primary'),
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
        print(f"Event opgeslagen: {event_data['summary']}")
        return result
    except Exception as e:
        print(f"Fout bij opslaan event: {e}")
        return None
