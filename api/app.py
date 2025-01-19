from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import sys
import os
import logging
import httpx
from http.server import BaseHTTPRequestHandler

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
class handler(BaseHTTPRequestHandler):
    def __init__(self, req, res, **kwargs):
        self.req = req
        self.send = res
        
    def handle(self):
        response = app(self.req, self.send)
        return response 