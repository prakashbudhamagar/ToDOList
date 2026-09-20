"""URL routes owned by the todo_list app (mounted at the site root)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TodoViewSet, csrf

router = DefaultRouter()
router.register('todos', TodoViewSet, basename='todo')

urlpatterns = [
    path('api/csrf/', csrf, name='api-csrf'),
    path('api/', include(router.urls)),
]
