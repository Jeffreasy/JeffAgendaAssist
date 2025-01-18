from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import sys
import os

# Voeg de root directory toe aan sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importeer de app van main.py
from main import app

# Dit is nodig voor Vercel
handler = app 