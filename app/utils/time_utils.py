import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo

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

    # Converteer naar Amsterdam-tijd en voeg expliciet 1 uur toe
    amsterdam_tz = ZoneInfo("Europe/Amsterdam")
    local_dt = dt.astimezone(amsterdam_tz) + timedelta(hours=1)

    # Formatteer met expliciete timezone offset (wintertijd hardcoded)
    return local_dt.strftime('%Y-%m-%d %H:%M:%S+0100')
