"""
This application serves as an API endpoint for the Signals and Trends project that connects
the frontend platform with the backend database.
"""

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import routers
from src.authentication import authenticate_user
from src.config.logging_config import setup_logging

load_dotenv()
setup_logging()

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

# allow cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


for router in routers.ALL:
    app.include_router(router=router, dependencies=[Depends(authenticate_user)])
