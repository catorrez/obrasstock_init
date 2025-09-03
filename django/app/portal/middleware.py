from django.shortcuts import redirect

class NoStaffOnAppMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        if request.path.startswith("/app/") and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return redirect("/admin/")
        return self.get_response(request)
