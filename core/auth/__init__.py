"""
Authentication and Authorization System
"""

from .owner_system import owner_system, OwnerRecognitionSystem
from .middleware import (
    auth_middleware,
    get_current_user,
    require_auth,
    optional_auth,
    require_owner, 
    require_vip_access,
    require_promotion_permission,
    require_expense_approval,
    require_crypto_trading,
    require_task_management,
    require_income_management
)

__all__ = [
    "owner_system",
    "OwnerRecognitionSystem",
    "auth_middleware",
    "get_current_user",
    "require_auth",
    "optional_auth",
    "require_owner",
    "require_vip_access", 
    "require_promotion_permission",
    "require_expense_approval",
    "require_crypto_trading",
    "require_task_management", 
    "require_income_management"
]