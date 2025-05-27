"""
This application serves as an API endpoint for the Signals and Trends project that connects
the frontend platform with the backend database.
"""

import os
import logging
import datetime
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src import routers
from src.authentication import authenticate_user
from src.config.logging_config import setup_logging
from src.bugsnag_config import configure_bugsnag, setup_bugsnag_logging, get_bugsnag_middleware, BUGSNAG_ENABLED

# Load environment variables and set up logging
load_dotenv()
setup_logging()

# Get application version
app_version = os.environ.get("RELEASE_VERSION", "dev")
app_env = os.environ.get("ENVIRONMENT", "development")
# Override environment setting if in local mode
if os.environ.get("ENV_MODE") == "local":
    app_env = "local"
logging.info(f"Starting application - version: {app_version}, environment: {app_env}")

# Configure Bugsnag for error tracking
configure_bugsnag()
setup_bugsnag_logging()

app = FastAPI(
    debug=False,
    title="Future Trends and Signals API",
    version="3.0.0-beta",
    summary="""The Future Trends and Signals (FTSS) API powers user experiences on UNDP Future
    Trends and Signals System by providing functionality to to manage signals, trends and users.""",
    description="""The FTSS API serves as a interface for the
    [UNDP Future Trends and Signals System](https://signals.data.undp.org),
    facilitating interaction between the front-end application and the underlying relational database.
    This API enables users to submit, retrieve, and update data related to signals, trends, and user
    profiles within the platform.
    
    As a private API, it mandates authentication for all endpoints to ensure secure access.
    Authentication is achieved by including the `access_token` in the request header, utilising JWT tokens
    issued by [Microsoft Entra](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens).
    This mechanism not only secures the API but also allows for the automatic recording of user information
    derived from the API token. Approved signals and trends can be accesses using a predefined API key for
    integration with other applications.
    """.strip().replace(
        "    ", " "
    ),
    contact={
        "name": "UNDP Data Futures Platform",
        "url": "https://data.undp.org",
        "email": "data@undp.org",
    },
    openapi_tags=[
        {"name": "signals", "description": "CRUD operations on signals."},
        {"name": "trends", "description": "CRUD operations on trends."},
        {"name": "users", "description": "CRUD operations on users."},
        {"name": "choices", "description": "List valid options for forms fields."},
        {"name": "favourites", "description": "Manage user's favorite signals."},
    ],
    docs_url="/",
    redoc_url=None,
)

# Add global exception handler to report errors to Bugsnag
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    if BUGSNAG_ENABLED:
        import bugsnag
        bugsnag.notify(
            exc,
            metadata={
                "request": {
                    "url": str(request.url),
                    "method": request.method,
                    "headers": dict(request.headers),
                    "client": request.client.host if request.client else None,
                }
            }
        )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# Configure CORS - simplified for local development
local_origins = [
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

# Production origins for different environments
production_origins = [
    "https://signals.data.undp.org",
    "https://thankful-forest-05a90a303-staging.westeurope.3.azurestaticapps.net",
    "https://signals-staging.data.undp.org"
]

# Create a custom middleware class for handling CORS
class CORSHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Handle OPTIONS preflight requests
        if request.method == "OPTIONS":
            origin = request.headers.get("origin")
            
            # Allow all origins but handle credentials properly
            if os.environ.get("ENV_MODE") == "local" and origin in local_origins:
                # Local mode: allow specific origins with credentials
                headers = {
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                    "Access-Control-Allow-Headers": "access_token, Authorization, Content-Type, Accept, X-API-Key",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "600",
                }
            else:
                # Production mode: allow all origins without credentials
                headers = {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                    "Access-Control-Allow-Headers": "access_token, Authorization, Content-Type, Accept, X-API-Key",
                    "Access-Control-Allow-Credentials": "false",
                    "Access-Control-Max-Age": "600",
                }
                
            return JSONResponse(content={}, status_code=200, headers=headers)
        
        # Process all other requests normally
        response = await call_next(request)
        return response

# Apply custom CORS middleware BEFORE the standard CORS middleware
app.add_middleware(CORSHandlerMiddleware)

# Standard CORS middleware (as a backup)
if os.environ.get("ENV_MODE") == "local":
    logging.info(f"Local mode: using specific CORS origins: {local_origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=local_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", "access_token", "Authorization", "Content-Type"],
        expose_headers=["*"],
    )
else:
    # Production mode - allow all origins for client flexibility
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,  # Must be False when allow_origins is ["*"]
        allow_methods=["*"],
        allow_headers=["*", "access_token", "Authorization", "Content-Type"],
    )

# Add Bugsnag exception handling middleware
# Important: Add middleware AFTER registering exception handlers
bugsnag_app = get_bugsnag_middleware(app)

for router in routers.ALL:
    app.include_router(router=router, dependencies=[Depends(authenticate_user)])

# Add diagnostic endpoint for health checks and Bugsnag verification
@app.get("/_health", include_in_schema=False)
async def health_check():
    """Health check endpoint that also shows the current environment and version."""
    return {
        "status": "ok",
        "environment": app_env,
        "version": app_version,
        "bugsnag_enabled": BUGSNAG_ENABLED
    }

# Test endpoint to trigger a test error report to Bugsnag if enabled
@app.get("/_test-error", include_in_schema=False)
async def test_error():
    """Trigger a test error to verify Bugsnag is working."""
    if BUGSNAG_ENABLED:
        import bugsnag
        bugsnag.notify(
            Exception("Test error triggered via /_test-error endpoint"),
            metadata={
                "test_info": {
                    "environment": app_env,
                    "version": app_version,
                    "timestamp": str(datetime.datetime.now())
                }
            }
        )
        return {"status": "error_reported", "message": "Test error sent to Bugsnag"}
    else:
        return {"status": "disabled", "message": "Bugsnag is not enabled"}

# Add special route for handling OPTIONS requests to /users/me
@app.options("/users/me", include_in_schema=False)
async def options_users_me():
    """Handle OPTIONS requests to /users/me specifically."""
    return {}

# Use the Bugsnag middleware wrapped app for ASGI
app = bugsnag_app
