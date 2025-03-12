from honeyhive import HoneyHiveTracer, trace, atrace
from functools import wraps
from typing import Callable, Any, Optional, Dict
import os
import logging

# Import the config
from app.config import config

# Set up logging
logger = logging.getLogger(__name__)

# Initialize the HoneyHive tracer
def init_honeyhive():
    """Initialize the HoneyHive tracer for OpenManus."""
    try:
        # Try to get API key from environment variable first
        api_key = os.environ.get("HH_API_KEY")
        
        # If not in environment, try to get from config
        if not api_key and config.honeyhive:
            api_key = config.honeyhive.api_key
        
        if not api_key:
            # Fallback to hardcoded key with warning
            api_key = 'your honeyhive api key'
            logger.warning("HH_API_KEY not found in environment variables or config. Using default key.")
        
        # Initialize with parameters from config if available
        if config.honeyhive:
            HoneyHiveTracer.init(
                api_key=api_key,
                project=config.honeyhive.project,
                source=config.honeyhive.source,
                session_name=config.honeyhive.session_name
            )
        else:
            # Fallback to default values
            HoneyHiveTracer.init(
                api_key=api_key,
                project='openmanus-trace',
                source='development',
                session_name='OpenManus Session'
            )
        logger.info("HoneyHive tracer initialized successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize HoneyHive tracer: {e}")
        # Don't raise to avoid breaking the application

# Create pydantic-compatible trace decorators
def pydantic_compatible_trace(func: Callable) -> Callable:
    """A trace decorator that's compatible with Pydantic models."""
    traced_func = trace(func)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        return traced_func(*args, **kwargs)
    
    return wrapper

def pydantic_compatible_atrace(func: Callable) -> Callable:
    """An async trace decorator that's compatible with Pydantic models."""
    traced_func = atrace(func)
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await traced_func(*args, **kwargs)
    
    return wrapper

# Export the decorators for use in other modules
__all__ = ['init_honeyhive', 'trace', 'atrace', 'pydantic_compatible_trace', 'pydantic_compatible_atrace'] 