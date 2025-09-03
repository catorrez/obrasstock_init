# saas/middleware.py
from django.conf import settings
from django.shortcuts import redirect

APP_PREFIX = "/app/"
ADMIN_PREFIX = "/admin/"

class DualSessionCookieMiddleware:
    """Usa 'app_sessionid' bajo /app y 'sessionid' en el resto."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        prev = settings.SESSION_COOKIE_NAME
        try:
            settings.SESSION_COOKIE_NAME = (
                "app_sessionid" if request.path.startswith(APP_PREFIX) else "sessionid"
            )
            return self.get_response(request)
        finally:
            settings.SESSION_COOKIE_NAME = prev


class NoStaffOnAppMiddleware:
    """Bloquea staff/superuser en /app (pero deja /app/login y /app/logout)."""
    def __init__(self, get_response):
        self.get_response = get_response
        self.allow = {f"{APP_PREFIX}login/", f"{APP_PREFIX}logout/"}

    def __call__(self, request):
        if request.path.startswith(APP_PREFIX) and request.path not in self.allow:
            u = getattr(request, "user", None)
            if u and u.is_authenticated and (u.is_staff or u.is_superuser):
                return redirect("/admin/")
        return self.get_response(request)


class RedirectClientsFromAdminMiddleware:
    """Si un usuario NO staff entra a /admin, mándalo a /app."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(ADMIN_PREFIX):
            u = getattr(request, "user", None)
            if u and u.is_authenticated and not (u.is_staff or u.is_superuser):
                return redirect("/app/")
        return self.get_response(request)
