from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def csrf(request):
    """Make Django set the csrftoken cookie so the React SPA can send it back."""
    return JsonResponse({'detail': 'CSRF cookie set'})