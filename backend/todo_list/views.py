from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import viewsets
from rest_framework.response import Response

from .models import Todo
from .serializers import TodoSerializer

# Cache key and lifetime for the task list - the only read-heavy endpoint.
TASK_LIST_CACHE_KEY = 'todo_list:task-list'
TASK_LIST_CACHE_TTL = 60


class TodoViewSet(viewsets.ModelViewSet):
    """REST endpoint for tasks.

    GET/POST        /api/todos/
    GET/PUT/PATCH   /api/todos/<id>/
    DELETE          /api/todos/<id>/

    The list response is cached (Redis in Docker, see config/settings.py) and every
    write clears that key, so a change is always visible on the next read.
    """

    queryset = Todo.objects.all()
    serializer_class = TodoSerializer

    def list(self, request, *args, **kwargs):
        data = cache.get(TASK_LIST_CACHE_KEY)
        if data is None:
            data = self.get_serializer(self.get_queryset(), many=True).data
            cache.set(TASK_LIST_CACHE_KEY, data, TASK_LIST_CACHE_TTL)
        return Response(data)

    def perform_create(self, serializer):
        serializer.save()
        self.clear_cache()

    def perform_update(self, serializer):
        serializer.save()
        self.clear_cache()

    def perform_destroy(self, instance):
        instance.delete()
        self.clear_cache()

    @staticmethod
    def clear_cache():
        cache.delete(TASK_LIST_CACHE_KEY)


@ensure_csrf_cookie
def csrf(request):
    """Make Django set the csrftoken cookie so the React SPA can send it back."""
    return JsonResponse({'detail': 'CSRF cookie set'})
