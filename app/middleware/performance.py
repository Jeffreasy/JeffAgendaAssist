from fastapi import Request
import time
from app.config import logger

async def performance_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    logger.info(f"Path: {request.url.path} | Time: {process_time:.2f}ms")
    
    return response 