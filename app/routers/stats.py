from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.config import supabase, logger
from app.schemas import CalendarStats

router = APIRouter()

@router.get("/", response_model=CalendarStats)
async def get_stats():
    """Haal statistieken op over alle events"""
    try:
        result = supabase.table('calendar_events').select('*').execute()
        events = result.data

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
                day = datetime.fromisoformat(event['start_time']).strftime('%A')
                day_counts[day] = day_counts.get(day, 0) + 1

        stats['busy_days'] = [
            {"day": day, "count": count}
            for day, count in sorted(day_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        ]

        # Meest voorkomende locaties (top 5)
        location_counts = {}
        for event in events:
            if event.get('location'):
                location_counts[event['location']] = location_counts.get(event['location'], 0) + 1

        stats['common_locations'] = [
            {"location": loc, "count": cnt}
            for loc, cnt in sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        return CalendarStats(**stats)

    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
