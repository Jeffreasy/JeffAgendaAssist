from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import sys
import os
import logging
import httpx
from fastapi.middleware.cors import CORSMiddleware

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Verwijder eventuele proxy configuratie in httpx
httpx.USE_CLIENT_DEFAULT = True

# Importeer de app van main.py
from app.main import app

# CORS configuratie voor de frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://jeff-agenda-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dit is nodig voor Vercel
def handler(request):
    return app 