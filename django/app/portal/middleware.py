# saas/middleware.py
from django.conf import settings
from django.shortcuts import redirect

ADMIN_HOSTS = {"adminos.etvholding.com"}
APP_HOSTS   = {"appos.etvholding.com"}

class DualSessionCookieMiddleware:
    """
    Usa cookies de sesión distintas por host para aislar /admin y /app.
    (sess_admin vs sess_app). A nivel de proceso es seguro con workers sync.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]
        original = settings.SESSION_COOKIE_NAME
        try:
            if host in ADMIN_HOSTS:
                settings.SESSION_COOKIE_NAME = "sess_admin"
            elif host in APP_HOSTS:
                settings.SESSION_COOKIE_NAME = "sess_app"
            response = self.get_response(request)
        finally:
            settings.SESSION_COOKIE_NAME = original
        return response


class NoStaffOnAppMiddleware:
    """
    Si un staff/superuser entra a /app, lo mandamos a /admin.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""
        if path.startswith("/app") and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return redirect("/admin/")
        return self.get_response(request)


class RedirectClientsFromAdminMiddleware:
    """
    Si un cliente (no staff) intenta /admin/login, redirige al login de /app.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""
        if path.startswith("/admin/login"):
            u = request.user
            if u.is_authenticated and not (u.is_staff or u.is_superuser):
                return redirect("/app/")
        return self.get_response(request)
