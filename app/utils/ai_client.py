from openai import OpenAI
from fastapi import HTTPException
from app.config import OPENAI_API_KEY, logger

def get_openai_client():
    """Initialize OpenAI client with API key"""
    try:
        # Basic client initialization
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")
        raise HTTPException(status_code=500, detail="Error initializing AI service") 