import datetime
from zoneinfo import ZoneInfo
from datetime import timedelta
from googleapiclient.discovery import build

from app.config import supabase, logger
from app.utils.time_utils import convert_time

def determine_category(event_data):
    """Bepaal category based op tijd en dag"""
    start_time = datetime.fromisoformat(event_data['start_time'])
    
    # Weekend check
    if start_time.weekday() >= 5:  # 5=Zaterdag, 6=Zondag
        return 'weekend'
    
    # Tijd check
    hour = start_time.hour
    if 6 <= hour < 14:
        return 'vroeg'
    elif 14 <= hour < 23:
        return 'laat'
    
    return None

async def save_event_to_supabase(event):
    """Save event to Supabase"""
    event_data = {
        'google_event_id': event['id'],
        'summary': event.get('summary', 'Geen titel'),
        'description': event.get('description', ''),
        'start_time': convert_time(event.get('start')),
        'end_time': convert_time(event.get('end')),
        'location': event.get('location', ''),
        'status': event.get('status', 'confirmed'),
        'calendar_id': event.get('organizer', {}).get('email', 'primary'),
        'calendar_name': event.get('calendar_name', 'Primary'),
        'recurring_event_id': event.get('recurringEventId', None),
        'is_recurring': bool(event.get('recurringEventId')),
        'attendees': event.get('attendees', []),
        'conference_data': event.get('conferenceData', {}),
        'color_id': event.get('colorId'),
        'visibility': event.get('visibility', 'default'),
        'updated_at': datetime.datetime.utcnow().isoformat(),
        'category': determine_category(event_data),
        'labels': []  # Default empty labels
    }

    try:
        result = supabase.table('calendar_events').upsert(event_data).execute()
        logger.info(f"Event opgeslagen: {event_data['summary']} ({event_data['calendar_name']})")
        return result
    except Exception as e:
        logger.error(f"Fout bij opslaan event: {e}")
        return None

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
                timeMin=now.isoformat(),
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
