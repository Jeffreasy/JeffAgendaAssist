from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

class Event(BaseModel):
    summary: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    location: Optional[str] = None
    calendar_name: str
    is_recurring: bool = False

class EventUpdate(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None

class SearchResult(BaseModel):
    events: List[Event]
    total_count: int
    query: str

class CalendarStats(BaseModel):
    total_events: int
    events_per_calendar: dict
    busy_days: List[dict]
    common_locations: List[dict]

class NotificationSettings(BaseModel):
    email: str
    before_minutes: int = 30
    calendars: List[str] = []
    enabled: bool = True

class EventCategory(str, Enum):
    VROEG = "vroeg"
    LAAT = "laat"
    WEEKEND = "weekend"

class EventLabel(str, Enum):
    WERK = "werk"
    PRIVE = "prive"
    BELANGRIJK = "belangrijk"

class EventWithLabels(Event):  # Extends bestaande Event model
    category: Optional[EventCategory] = None
    labels: List[EventLabel] = []

class UpdateLabelsRequest(BaseModel):
    category: Optional[EventCategory] = None
    labels: Optional[List[EventLabel]] = None

class ChatMessage(BaseModel):
    content: str
    
class ChatResponse(BaseModel):
    response: str
    events_analyzed: int

class AIRequest(BaseModel):
    content: str = Field(..., description="De vraag of het verzoek aan de AI")

class AIResponse(BaseModel):
    response: str = Field(..., description="Het antwoord van de AI")
    events_analyzed: int = Field(..., description="Aantal geanalyseerde events")

class AIAnalysis(BaseModel):
    analysis: str = Field(..., description="De analyse van de agenda")
    events_analyzed: int = Field(..., description="Aantal geanalyseerde events")
    period_days: int = Field(..., description="Aantal dagen geanalyseerd")

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
    status: int = Field(..., description="HTTP status code")
