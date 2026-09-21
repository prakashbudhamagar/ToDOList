from django.contrib import admin
from django.urls import include, path

from .views import csrf

# The Django project only serves JSON: the user interface is the React app in
# ../frontend (see README). Each backend feature owns its own /api/ routes:
# tasks (task CRUD) and chat (the AI assistant).
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/csrf/', csrf, name='api-csrf'),
    path('api/', include('tasks.urls')),
    path('api/', include('chat.urls')),
]
