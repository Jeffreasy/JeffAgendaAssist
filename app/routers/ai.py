from fastapi import APIRouter, HTTPException
from typing import List, Optional
import openai
from datetime import datetime, timedelta

from app.config import OPENAI_API_KEY, supabase, logger
from app.schemas import ChatMessage, ChatResponse

router = APIRouter()

async def get_relevant_events(days: int = 7):
    """Haal relevante events op voor context"""
    try:
        now = datetime.now()
        end_date = now + timedelta(days=days)
        
        result = supabase.table('calendar_events')\
            .select('*')\
            .gte('start_time', now.isoformat())\
            .lte('start_time', end_date.isoformat())\
            .execute()
            
        return result.data
    except Exception as e:
        logger.error(f"Error fetching events for AI context: {str(e)}")
        return []

@router.post("/chat")
async def chat_with_assistant(message: ChatMessage):
    """Chat met de AI over je agenda"""
    try:
        # Haal relevante events op
        events = await get_relevant_events()
        
        # Bouw de context
        context = "Je bent een behulpzame agenda assistent. "
        context += "Dit zijn de komende events:\n"
        
        for event in events:
            context += f"- {event['summary']} op {event['start_time']}\n"
        
        # OpenAI chat completion
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": message.content}
            ]
        )
        
        return ChatResponse(
            response=response.choices[0].message.content,
            events_analyzed=len(events)
        )
        
    except Exception as e:
        logger.error(f"AI chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def analyze_schedule(days: Optional[int] = 7):
    """Analyseer je agenda en geef inzichten"""
    try:
        events = await get_relevant_events(days)
        
        prompt = f"""
        Analyseer deze agenda voor de komende {days} dagen en geef inzichten over:
        1. Drukke/rustige periodes
        2. Werk/privé balans
        3. Suggesties voor timemanagement
        
        Events:
        """
        
        for event in events:
            prompt += f"- {event['summary']} ({event['category']}) op {event['start_time']}\n"
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Je bent een agenda analyst die helpt bij timemanagement."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return {
            "analysis": response.choices[0].message.content,
            "events_analyzed": len(events),
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"AI analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 