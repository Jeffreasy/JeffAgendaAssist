from fastapi import APIRouter, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import supabase, logger
from app.schemas import Event, EventUpdate, SearchResult, EventCategory, EventLabel, UpdateLabelsRequest, EventWithLabels

router = APIRouter()

@router.get("/", response_model=List[Event])
async def get_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    calendar_name: Optional[str] = None
):
    """Haal events op uit Supabase met optionele filters"""
    try:
        query = supabase.table('calendar_events').select('*')

        if start_date:
            query = query.gte('start_time', start_date)
        if end_date:
            query = query.lte('end_time', end_date)
        if calendar_name:
            query = query.eq('calendar_name', calendar_name)

        query = query.order('start_time', desc=False)
        result = query.execute()

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

@router.get("/calendars")
async def get_calendars():
    """Haal lijst van unieke agenda-namen op"""
    try:
        result = supabase.table('calendar_events').select('calendar_name').execute()
        calendars = list(set(event['calendar_name'] for event in result.data))
        return {"calendars": calendars}
    except Exception as e:
        logger.error(f"Error fetching calendars: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{event_id}")
async def delete_event(event_id: str):
    """Verwijder een event uit Supabase"""
    try:
        supabase.table('calendar_events').delete().eq('google_event_id', event_id).execute()
        return {"message": f"Event {event_id} verwijderd"}
    except Exception as e:
        logger.error(f"Error deleting event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{event_id}")
async def update_event(event_id: str, event: EventUpdate):
    """Update een event in Supabase"""
    try:
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

@router.get("/today")
async def get_today_events():
    """Haal events van vandaag op"""
    try:
        amsterdam_tz = ZoneInfo("Europe/Amsterdam")
        now = datetime.now(amsterdam_tz)
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

@router.get("/upcoming")
async def get_upcoming_events(days: int = 7):
    """Haal events voor de komende X dagen op"""
    try:
        amsterdam_tz = ZoneInfo("Europe/Amsterdam")
        now = datetime.now(amsterdam_tz)
        end_date = now + timedelta(days=days)

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

@router.get("/search", response_model=SearchResult)
async def search_events(
    query: str,
    calendar_name: Optional[str] = None,
    include_description: bool = True
):
    """Zoek in events op basis van query"""
    try:
        db_query = supabase.table('calendar_events').select('*')
        if calendar_name:
            db_query = db_query.eq('calendar_name', calendar_name)

        result = db_query.execute()
        events = result.data

        matched_events = []
        lower_query = query.lower()

        for event in events:
            if lower_query in event['summary'].lower():
                matched_events.append(event)
            elif include_description and event['description'] and lower_query in event['description'].lower():
                matched_events.append(event)
            elif event['location'] and lower_query in event['location'].lower():
                matched_events.append(event)

        event_objects = [Event(**event) for event in matched_events]

        return SearchResult(
            events=event_objects,
            total_count=len(event_objects),
            query=query
        )
    except Exception as e:
        logger.error(f"Error searching events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{event_id}/labels")
async def update_event_labels(
    event_id: str, 
    update: UpdateLabelsRequest
):
    """Update category en labels van een event"""
    try:
        # Update data voorbereiden
        update_data = {}
        if update.category is not None:
            update_data['category'] = update.category
        if update.labels is not None:
            update_data['labels'] = update.labels

        result = supabase.table('calendar_events')\
            .update(update_data)\
            .eq('google_event_id', event_id)\
            .execute()

        return result.data[0] if result.data else None

    except Exception as e:
        logger.error(f"Error updating event labels: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/filter")
async def filter_events(
    category: Optional[EventCategory] = None,
    labels: Optional[List[EventLabel]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Filter events op category en labels"""
    try:
        query = supabase.table('calendar_events').select('*')

        if category:
            query = query.eq('category', category)
        if labels:
            query = query.contains('labels', labels)
        if start_date:
            query = query.gte('start_time', start_date)
        if end_date:
            query = query.lte('end_time', end_date)

        result = query.execute()
        return [EventWithLabels(**event) for event in result.data]

    except Exception as e:
        logger.error(f"Error filtering events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
