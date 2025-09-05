from django.http import HttpResponseRedirect

class ForceDomainPerAreaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]
        path = request.path

        # Ajusta a https si ya usas TLS. Hoy estamos en http y puerto 8181.
        if path.startswith("/admin") and host != "adminos.etvholding.com":
            return HttpResponseRedirect(f"http://adminos.etvholding.com:8181{path}")

        if path.startswith("/app") and host != "appos.etvholding.com":
            return HttpResponseRedirect(f"http://appos.etvholding.com:8181{path}")

        return self.get_response(request)


class NoStaffOnAppMiddleware:
    """Si un staff/superuser intenta usar /app, lo expulsamos al /admin."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/app"):
            u = getattr(request, "user", None)
            if u and u.is_authenticated and (u.is_staff or u.is_superuser):
                return HttpResponseRedirect("http://adminos.etvholding.com:8181/admin/")
        return self.get_response(request)
