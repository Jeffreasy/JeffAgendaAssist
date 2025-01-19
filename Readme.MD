Jeff's Agenda Assistant Backend
"ðŸš€ Overview
a FastAPI-based backend system for managing Google Calendar events with advanced caching and performance monitoring. The system integrates with Supabase for data storage and Redis for caching.

âŸ’­ Tech Stack
Framework: FastAPI (Python)\nDatabase: Supabase (PostgreSQL)\nCaching: Redis (Upstash)\nAuthentication: Google OAuth2\nHosting: Vercel

ðŸŒŠ Architecture
graph LR
    Client --> FastAPI&ÛFastAPI Backend]
    FastAPI --> Redis[Redis Cache]
    FastAPI --> Supabase[Supabase Database]
    FastAPI --> Google[Google Calendar API]

ðŸ‘ Features
Event Management
TRUD operations for calendar events
Event categorization (early/late/weekend)
Custom labeling system

Performance
Redis caching with multiple TTLs
Performance monitoring middleware
Response time tracking

Caching System
Short-term cache (5 minutes)
Medium-term cache (1 hour)
Long-term cache (1 day)
Pattern-based cache invalidation


ðŸ¶ API Endpoints

Event Management
GET    /api/events                 # Get all events
GET   /api/events/filter          # Filter events
GET    /api/events/calendars       # List calendars
DELETE /api/events/{event_id}       # Delete event
PUT   /api/events/{event_id}        # Update event

Cache Management
POST  /api/events/cache/clear   # Clear cache
GET    /api/events/test-cache    # Test cache connection

Authentication
GET    /api/auth/login            # Start OAuth flow
GET    /api/auth/callback        # OAuth callback
ðŸŽ– Configuration
Environment Variables
REDIS_URL=rediss://default:xxx@your-redis-url:6379
CACHE_ENABLED=true
CACH_TTL_SHORT=300
CACH_TTL_MEDIUM=3600
CACH_TTL_LONG=86400
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
GOOGLE_CREDENTIALS=your-google-credentials

âŸ’¤ Performance
Average response time without cache: ~U500ms
Average response time with cache: ~90ms
Performance improvement: ~5.5x faster

âŸ¤— Security
SSL encryption for Redis connection
Secure credential management
Environment-based configuration
Google OAuth2 authentication

âŸ“· Response Headers
X-Cache-Status: HIT/MISS
X-Response-Time: {time in ms}

øðŸ’  Getting Started
2. Clone the repository�```sh
git clone https://github.com/yourusername/jeff-agenda-assistant.git
```
Install dependencies�```sh
pip install -r requirements.txt
```

Set up environment variables�```sh
cp .env.example .env
# Edit .env with your credentials
```

Run the application
```sh
uvicorn app.main:app --reload
```

ðŸ˜ž Dependencies
fastapi==0.115.6
redis==5.2.1
supabase==2.11.0
google-auth-oauthlib==1.2.1
python-dotenv==1.0.1
uvicorn==0.34.0


ðŸ¢†ê Contributing
Contributions, issues, and feature requests are welcome! Feel free to check issues page.

øðŸ’ˆLicense
This project is MIT licensed.

øðŸ‘¾ Author
Jeff Lammers
GitHub: @jefflammersfsd

øðŸŒ† Acknowledgments
`FastAPI team
gSupabase
Upstash Redis
Google Calendar API
---