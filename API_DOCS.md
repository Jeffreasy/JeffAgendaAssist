# Jeff Agenda Assistant API Documentation

## Overview
RESTful API voor het beheren van Google Calendar events met Supabase database integratie.

## Base URL
https://jeff-agenda-assist.vercel.app

## Endpoints

### 1. Health Check Endpoints
GET /                   # Basis health check
GET /api/health        # Uitgebreide health check met Supabase en Google status

### 2. Authenticatie Endpoints
GET /api/auth/login     # Start Google OAuth flow
GET /api/auth/callback  # Handelt OAuth callback af en sync agenda

### 3. Event Management Endpoints
# Ophalen van events
GET /api/events                    # Alle events ophalen
GET /api/events?start_date=2024-01-20&end_date=2024-02-20  # Events binnen datumbereik
GET /api/events?calendar_name=SDB%20Planning  # Events van specifieke agenda

# Event management
GET /api/events/today             # Events van vandaag
GET /api/events/upcoming?days=7   # Events voor komende X dagen
DELETE /api/events/{event_id}     # Event verwijderen
PUT /api/events/{event_id}        # Event updaten

### 4. Calendar Management Endpoints
GET /api/calendars     # Lijst van alle beschikbare agenda's

### 5. Statistics Endpoints
GET /api/stats         # Statistieken over events en agenda's

### 6. Search Endpoints
GET /api/events/search?query=string&calendar_name=optional  # Zoek in events

### 7. Notification Endpoints
POST /api/notifications/setup    # Setup email notificaties
GET /api/notifications/settings?email=user@example.com  # Haal notificatie instellingen op

### 8. Event Categories & Labels
GET /api/events/filter  # Filter events op categorie en labels

Parameters:
- category: "vroeg" | "laat" | "weekend"
- labels: ["werk", "prive", "belangrijk"]
- start_date: "YYYY-MM-DD" (optional)
- end_date: "YYYY-MM-DD" (optional)

### Event Categories
- vroeg: 6:00-13:59 (werkdagen)
- laat: 14:00-22:59 (werkdagen)
- weekend: Alle events op zaterdag/zondag

### Event Labels
Events kunnen één of meerdere labels hebben:
- werk
- prive
- belangrijk

### Event Category Response Model
{
    "summary": "string",
    "description": "string | null",
    "start_time": "string (ISO datetime)",
    "end_time": "string (ISO datetime)",
    "location": "string | null",
    "calendar_name": "string",
    "is_recurring": "boolean",
    "category": "vroeg" | "laat" | "weekend" | null,
    "labels": ["werk" | "prive" | "belangrijk"]
}

## Request & Response Models

### Event Response Model
{
    "summary": "string",
    "description": "string | null",
    "start_time": "string (ISO datetime)",
    "end_time": "string (ISO datetime)",
    "location": "string | null",
    "calendar_name": "string",
    "is_recurring": "boolean"
}

### Event Update Request Model
{
    "summary": "string | null",
    "description": "string | null",
    "start_time": "string | null",
    "end_time": "string | null",
    "location": "string | null"
}

## Voorbeelden

### 1. Events ophalen
curl https://jeff-agenda-assist.vercel.app/api/events

### 2. Events filteren op datum
curl "https://jeff-agenda-assist.vercel.app/api/events?start_date=2024-01-20&end_date=2024-02-20"

### 3. Event updaten
curl -X PUT https://jeff-agenda-assist.vercel.app/api/events/[event_id] \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Nieuwe titel",
    "location": "Nieuwe locatie"
  }'

### 4. Agenda's ophalen
curl https://jeff-agenda-assist.vercel.app/api/calendars

Response:
{
    "calendars": [
        "SDB Planning",
        "Feestdagen in Nederland",
        "Projecten/Prive agenda"
    ]
}

### 1. Filter events op categorie
curl "https://jeff-agenda-assist.vercel.app/api/events/filter?category=laat"

### 2. Filter events op categorie en labels
curl "https://jeff-agenda-assist.vercel.app/api/events/filter?category=vroeg&labels=werk"

### 3. Update event labels
curl -X POST https://jeff-agenda-assist.vercel.app/api/events/{event_id}/labels \
  -H "Content-Type: application/json" \
  -d '{
    "category": "vroeg",
    "labels": ["werk", "belangrijk"]
  }'

## Error Responses
Alle endpoints retourneren een 500 status code bij fouten met een detail message:

{
    "detail": "Error message beschrijving"
}

### Performance Headers
Alle responses bevatten de volgende headers:
- `X-Cache-Status`: "HIT" of "MISS" (geeft aan of het resultaat uit cache kwam)
- `X-Response-Time`: Tijd in milliseconden voor het verwerken van het request

### Voorbeeld Response Headers

### Cache Management
GET /api/events/cache/status     # Check cache status
POST /api/events/cache/clear     # Clear cache entries

Parameters:
- pattern: Optional pattern to clear specific cache entries
  Example: "events:*" clears all event caches

## CORS Configuration
The API supports Cross-Origin Resource Sharing (CORS) with the following settings:

### Allowed Origins
- http://localhost:3000 (React development)
- http://localhost:5173 (Vite development)
- https://jeff-agenda-assist.vercel.app (Production)

### CORS Headers
All endpoints include the following CORS headers:
- Access-Control-Allow-Credentials: true
- Access-Control-Allow-Methods: *
- Access-Control-Allow-Headers: *