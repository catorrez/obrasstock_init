from django.http import HttpResponseRedirect

class ForceDomainPerAreaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]
        path = request.path

        # For localhost/testing, don't redirect admin/app paths
        if host in ("localhost", "127.0.0.1"):
            return self.get_response(request)
            
        # For production domains, use HTTPS
        if path.startswith("/admin") and host != "adminos.etvholding.com":
            return HttpResponseRedirect(f"https://adminos.etvholding.com{path}")

        if path.startswith("/app") and host != "appos.etvholding.com":
            return HttpResponseRedirect(f"https://appos.etvholding.com{path}")

        return self.get_response(request)


class NoStaffOnAppMiddleware:
    """Si un staff/superuser intenta usar /app, lo expulsamos al /admin."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/app"):
            u = getattr(request, "user", None)
            if u and u.is_authenticated and (u.is_staff or u.is_superuser):
                # For localhost/testing, redirect to /admin/ 
                if request.get_host().split(":")[0] in ("localhost", "127.0.0.1"):
                    return HttpResponseRedirect("/admin/")
                else:
                    return HttpResponseRedirect("https://adminos.etvholding.com/admin/")
        return self.get_response(request)
