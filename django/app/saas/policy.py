# django/app/saas/policy.py
from .models import AdminPolicy
from .roles import user_is_owner, user_is_system_admin

def can_manage_groups(user):
    if user_is_owner(user):
        return True
    return user_is_system_admin(user) and AdminPolicy.get().allow_system_admin_groups

def can_manage_modules(user):
    if user_is_owner(user):
        return True
    return user_is_system_admin(user) and AdminPolicy.get().allow_system_admin_modules
