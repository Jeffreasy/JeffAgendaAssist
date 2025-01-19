import datetime
from zoneinfo import ZoneInfo
from datetime import timedelta
from googleapiclient.discovery import build

from app.config import supabase, logger
from app.utils.time_utils import convert_time

def determine_category(event_data):
    """Bepaal category based op tijd en dag"""
    # Parse de tijd met timezone
    start_time_str = event_data['start_time']
    try:
        # Als er een + in de string staat, gaan we ervan uit dat de offset correct meegegeven is
        if '+' in start_time_str:
            start_time = datetime.datetime.strptime(
                start_time_str,
                '%Y-%m-%d %H:%M:%S%z'
            )
            # Converteer daarna expliciet naar Amsterdam
            start_time = start_time.astimezone(ZoneInfo("Europe/Amsterdam"))
        else:
            # Hier komt de 'naïeve' tijd binnen (zonder offset).
            # We gaan ervan uit dat deze in UTC is en converteren vervolgens naar Amsterdam-tijd.
            naive_start = datetime.datetime.strptime(
                start_time_str, 
                '%Y-%m-%d %H:%M:%S'
            )
            # Label de tijd eerst als UTC
            start_time_utc = naive_start.replace(tzinfo=ZoneInfo("UTC"))
            # Converteer nu naar Europe/Amsterdam
            start_time = start_time_utc.astimezone(ZoneInfo("Europe/Amsterdam"))

        # Log voor debugging
        logger.info(f"Determining category for time: {start_time} (hour: {start_time.hour})")
        
        # Weekend check
        if start_time.weekday() >= 5:  # 5=Zaterdag, 6=Zondag
            return "weekend"
        
        # Tijd check (aangepaste tijden)
        hour = start_time.hour
        if 6 <= hour < 14:  # Vroeg: 6:00 tot 13:59
            return "vroeg"
        elif 14 <= hour < 23:  # Laat: 14:00 tot 22:59
            return "laat"
        
        # In alle andere gevallen (bijv. nacht)
        return None
    except Exception as e:
        logger.error(f"Error determining category: {e}")
        return None

async def save_event_to_supabase(event):
    """Save event to Supabase"""
    try:
        # Parse Google Calendar tijd
        start_time_raw = event.get('start', {}).get('dateTime')
        end_time_raw = event.get('end', {}).get('dateTime')

        # Parse en converteer naar Amsterdam tijd
        amsterdam_tz = ZoneInfo("Europe/Amsterdam")
        
        if start_time_raw:
            # Parse ISO format en converteer naar Amsterdam
            start_time = datetime.datetime.fromisoformat(start_time_raw)
            if start_time.tzinfo is None:
                # Als geen timezone, neem aan UTC
                start_time = start_time.replace(tzinfo=datetime.UTC)
            # Converteer naar Amsterdam
            start_time = start_time.astimezone(amsterdam_tz)
            # Format voor database (met Amsterdam offset)
            start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S%z')
            
            # Debug logging
            logger.info(f"Raw start: {start_time_raw}")
            logger.info(f"Parsed start: {start_time}")
            logger.info(f"Final start: {start_time_str}")
        else:
            start_time_str = None
            start_time = None

        # Zelfde voor end time
        if end_time_raw:
            end_time = datetime.datetime.fromisoformat(end_time_raw)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=datetime.UTC)
            end_time = end_time.astimezone(amsterdam_tz)
            end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S%z')
        else:
            end_time_str = None
            end_time = None

        # Bepaal categorie direct met het datetime object
        category = None
        if start_time:
            hour = start_time.hour
            if start_time.weekday() >= 5:
                category = "weekend"
            elif 6 <= hour < 14:
                category = "vroeg"
            elif 14 <= hour < 23:
                category = "laat"

        # Event data
        event_data = {
            'google_event_id': event['id'],
            'summary': event.get('summary', 'Geen titel'),
            'description': event.get('description', ''),
            'start_time': start_time_str,
            'end_time': end_time_str,
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
            'updated_at': datetime.datetime.now(amsterdam_tz).isoformat(),
            'category': category,
            'labels': []
        }

        # Debug logging
        logger.info(f"Saving event: {event_data['summary']}")
        logger.info(f"Time: {start_time_str}")
        logger.info(f"Category: {category}")

        result = supabase.table('calendar_events').upsert(event_data).execute()
        return result

    except Exception as e:
        logger.error(f"Error saving event: {str(e)}")
        logger.error(f"Event data: {event}")
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
