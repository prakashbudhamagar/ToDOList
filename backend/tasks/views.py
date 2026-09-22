from django.core.cache import cache

from rest_framework import viewsets
from rest_framework.response import Response

from .cache import TASK_LIST_CACHE_KEY, TASK_LIST_CACHE_TTL, clear_task_list_cache
from .models import Todo
from .serializers import TodoSerializer


class TodoViewSet(viewsets.ModelViewSet):
    """REST endpoint for tasks.

    GET/POST        /api/todos/
    GET/PUT/PATCH   /api/todos/<id>/
    DELETE          /api/todos/<id>/

    The list response is cached (Redis in Docker, see config/settings.py) and every
    write clears that key, so a change is always visible on the next read. Tasks
    come back ordered by priority (high first, then oldest first - see Todo.Meta).
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
        clear_task_list_cache()

    def perform_update(self, serializer):
        serializer.save()
        clear_task_list_cache()

    def perform_destroy(self, instance):
        instance.delete()
        clear_task_list_cache()