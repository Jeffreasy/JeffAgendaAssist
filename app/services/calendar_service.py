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
    # Eerst de tijden converteren
    start_time = convert_time(event.get('start'))
    end_time = convert_time(event.get('end'))
    
    # Dan event_data maken
    event_data = {
        'google_event_id': event['id'],
        'summary': event.get('summary', 'Geen titel'),
        'description': event.get('description', ''),
        'start_time': start_time,
        'end_time': end_time,
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
        'updated_at': datetime.datetime.utcnow().isoformat()
    }

    # Categorie bepalen met de geconverteerde tijd
    category_data = {'start_time': start_time}
    event_data['category'] = determine_category(category_data)
    event_data['labels'] = []  # Default empty labels

    logger.info(f"Saving event: {event_data['summary']} at {start_time} with category {event_data['category']}")

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
