from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import logger, supabase, CREDENTIALS_FILE, CORS_ORIGINS
from app.routers import auth, events, notifications, stats, ai
from app.middleware.performance import performance_middleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting up...")
    yield
    # Shutdown
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.middleware("http")(performance_middleware)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "API is running"}

@app.get("/api/health")
async def health():
    """Detailed health check"""
    try:
        # Test Supabase-verbinding
        supabase_ok = bool(supabase.table('calendar_events').select("*").limit(1).execute())

        return {
            "status": "ok",
            "supabase": "connected" if supabase_ok else "error",
            "google_credentials": "configured" if CREDENTIALS_FILE else "missing"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "error", "message": str(e)}

# Routers koppelen met hun prefix
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
