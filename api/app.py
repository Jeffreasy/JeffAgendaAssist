from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import sys
import os
import logging
import httpx

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Verwijder eventuele proxy configuratie in httpx
httpx.USE_CLIENT_DEFAULT = True

# Importeer de app van main.py
from app.main import app

# Dit is nodig voor Vercel
def handler(request: Request):
    if request.url.path.endswith("/"):
        return RedirectResponse(request.url.path[:-1])
    return app 