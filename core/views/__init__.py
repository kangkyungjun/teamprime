"""
HTML Views Module
웹 인터페이스를 위한 HTML 응답 뷰들
"""

from .main_views import main_views_router
from .dashboard_views import dashboard_views_router
from .auth_views import auth_views_router
from .task_views import task_views_router
from .analytics_views import analytics_views_router
from .reports_views import reports_views_router

__all__ = [
    "main_views_router",
    "dashboard_views_router", 
    "auth_views_router",
    "task_views_router",
    "analytics_views_router",
    "reports_views_router"
]