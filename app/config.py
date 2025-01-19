import os
import json
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
from google_auth_oauthlib.flow import Flow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Laad omgevingsvariabelen uit .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS')

# Voeg toe aan environment variables
REDIS_URL = os.getenv('REDIS_URL', None)  # Geen default, zodat we weten als het mist
CACHE_ENABLED = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))

# Log de effectieve configuratie
logger.info("="*50)
logger.info("CONFIGURATION")
logger.info(f"REDIS_URL configured: {bool(REDIS_URL)}")
logger.info(f"CACHE_ENABLED: {CACHE_ENABLED}")
logger.info(f"CACHE_TTL: {CACHE_TTL}")
logger.info("="*50)

# Maak de Supabase-client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Google Calendar scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events.readonly'
]

# Voor de OAuth2 Flow
if CREDENTIALS_FILE:
    # Als CREDENTIALS_FILE in JSON-vorm in de environment staat
    credentials_dict = json.loads(CREDENTIALS_FILE)
    flow = Flow.from_client_config(
        credentials_dict,
        scopes=SCOPES,
        redirect_uri='https://jeff-agenda-assist.vercel.app/api/auth/callback'
    )
else:
    # Lokaal uit een secret-bestand
    flow = Flow.from_client_secrets_file(
        'client_secret_1030699582107-krrjnsu8i5vutkoukb8c5kiou1etmurg.apps.googleusercontent.com.json',
        scopes=SCOPES,
        redirect_uri='https://jeff-agenda-assist.vercel.app/api/auth/callback'
    )
