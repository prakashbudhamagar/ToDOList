from django.contrib import admin
from django.urls import include, path

# The Django project only serves JSON: the user interface is the React app in
# ../frontend (see README). The todo_list app owns the /api/ routes.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('todo_list.urls')),
]
