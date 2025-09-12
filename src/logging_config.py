# === File: src/logging_config.py ===

import logging
import os
from config import LOG_LEVEL, LOG_FILE, LOG_FORMAT

def setup_logging():
    """
    Configure logging for the application.
    Creates log directory if it doesn't exist and sets up file and console logging.
    """
    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper()),
        format=LOG_FORMAT,
        handlers=[
            # File handler
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            # Console handler
            logging.StreamHandler()
        ]
    )
    
    # Set specific loggers
    logging.getLogger('langchain').setLevel(logging.WARNING)  # Reduce LangChain verbosity
    logging.getLogger('httpx').setLevel(logging.WARNING)      # Reduce HTTP verbosity
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {LOG_LEVEL}, File: {LOG_FILE}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
