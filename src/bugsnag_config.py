"""
Bugsnag configuration module for error tracking.
"""

import os
import logging
import bugsnag
from bugsnag.handlers import BugsnagHandler
from bugsnag.asgi import BugsnagMiddleware

# Get API key from environment variable with fallback to the provided key
BUGSNAG_API_KEY = os.environ.get("BUGSNAG_API_KEY")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
RELEASE_VERSION = os.environ.get("RELEASE_VERSION", "dev")

if not BUGSNAG_API_KEY:
    logging.warning("BUGSNAG_API_KEY is not set - error reporting will be disabled")
    BUGSNAG_ENABLED = False
else:
    BUGSNAG_ENABLED = True

def configure_bugsnag():
    """Configure Bugsnag for error tracking."""
    if not BUGSNAG_ENABLED:
        logging.warning("Bugsnag is disabled - skipping configuration")
        return
        
    bugsnag.configure(
        api_key=BUGSNAG_API_KEY,
        project_root=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        release_stage=ENVIRONMENT,
        app_version=RELEASE_VERSION,
        notify_release_stages=["production", "staging", "development"],
        app_type="fastapi",
    )
    
    logging.info(f"Bugsnag configured - environment: {ENVIRONMENT}, version: {RELEASE_VERSION}")

def setup_bugsnag_logging(level=logging.ERROR):
    """
    Set up Bugsnag to capture logs at specified level.
    
    Parameters
    ----------
    level : int
        Minimum log level to send to Bugsnag
    """
    if not BUGSNAG_ENABLED:
        return
        
    logger = logging.getLogger()
    handler = BugsnagHandler()
    handler.setLevel(level)
    logger.addHandler(handler)
    
    logging.info(f"Bugsnag logging handler added at level {level}")

def get_bugsnag_middleware(app):
    """
    Wrap an ASGI app with Bugsnag middleware.
    
    Parameters
    ----------
    app : ASGI application
        The FastAPI application instance
    
    Returns
    -------
    ASGI application
        The application wrapped with Bugsnag middleware
    """
    if not BUGSNAG_ENABLED:
        logging.warning("Bugsnag middleware not added - Bugsnag is disabled")
        return app
        
    return BugsnagMiddleware(app) 