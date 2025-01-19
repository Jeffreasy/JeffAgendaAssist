from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime, timedelta

from app.config import supabase, logger
from app.schemas import ChatMessage, ChatResponse, AIRequest, AIResponse, AIAnalysis, ErrorResponse
from app.utils.ai_client import get_openai_client

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

@router.post("/chat", response_model=AIResponse, responses={500: {"model": ErrorResponse}})
async def chat_with_assistant(request: AIRequest):
    """Chat met de AI over je agenda"""
    try:
        events = await get_relevant_events()
        
        context = "Je bent een behulpzame agenda assistent. "
        context += "Dit zijn de komende events:\n"
        
        for event in events:
            context += f"- {event['summary']} op {event['start_time']}\n"
        
        # New OpenAI syntax
        response = get_openai_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": request.content}
            ]
        )
        
        return AIResponse(
            response=response.choices[0].message.content,
            events_analyzed=len(events)
        )
        
    except Exception as e:
        logger.error(f"AI chat error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail={"detail": str(e), "status": 500}
        )

@router.post("/analyze", response_model=AIAnalysis, responses={500: {"model": ErrorResponse}})
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
        
        try:
            client = get_openai_client()
            # New OpenAI syntax with better error handling
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Je bent een agenda analyst die helpt bij timemanagement."},
                    {"role": "user", "content": prompt}
                ],
                timeout=30.0
            )
            
            return AIAnalysis(
                analysis=response.choices[0].message.content,
                events_analyzed=len(events),
                period_days=days
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={"detail": f"OpenAI API error: {str(e)}", "status": 500}
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"AI analysis error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail={"detail": str(e), "status": 500}
        ) 