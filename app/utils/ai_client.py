from openai import OpenAI
from fastapi import HTTPException
from app.config import OPENAI_API_KEY, logger

def get_openai_client():
    """Initialize OpenAI client with API key"""
    try:
        # Initialize with base_url to ensure correct API endpoint
        return OpenAI(
            api_key=OPENAI_API_KEY,
            base_url="https://api.openai.com/v1",
            timeout=30.0  # Add timeout to prevent hanging
        )
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")
        raise HTTPException(status_code=500, detail="Error initializing AI service") 