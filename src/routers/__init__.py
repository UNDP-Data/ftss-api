"""
Router definitions for API endpoints.
"""

from .choices import router as choice_router
from .signals import router as signal_router
from .trends import router as trend_router
from .users import router as user_router
from .email import router as email_router

ALL = [
    choice_router,
    signal_router,
    trend_router,
    user_router,
    email_router,
]
