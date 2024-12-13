"""
Router definitions for API endpoints.
"""

from .choices import router as choice_router
from .favourites import router as favourites_router
from .signals import router as signal_router
from .trends import router as trend_router
from .users import router as user_router

ALL = [
    choice_router,
    favourites_router,
    signal_router,
    trend_router,
    user_router,
]
