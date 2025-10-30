"""
Logging configuration for the MCP proxy server
"""
import logging
import os
import sys


def setup_logging() -> logging.Logger:
    """
    Set up logging for the application.
    Log level is controlled by the DEBUG environment variable.
    """
    # Determine log level from environment
    debug_value = os.getenv("DEBUG", "").lower()
    is_debug = debug_value in ("1", "true", "yes", "on")
    
    log_level = logging.DEBUG if is_debug else logging.INFO
    
    # Create logger
    logger = logging.getLogger("mcp_proxy")
    logger.setLevel(log_level)
    
    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger
    
    # Create console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger


# Create a singleton logger instance
logger = setup_logging()

