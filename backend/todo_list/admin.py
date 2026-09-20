from django.contrib import admin

from .models import Todo

class TodoAdmin(admin.ModelAdmin):
    """What makes the task list usable instead of the bare default."""

    # Columns on the changelist, newest first so recent tasks stay on top.
    list_display = ('title', 'create_at')
    ordering = ('-create_at',)
    # Sidebar filters, a search box, and a date drill-down.
    list_filter = ('create_at',)
    search_fields = ('title',)
    date_hierarchy = 'create_at'
    # 50 rows per page keeps a long todo list manageable.
    list_per_page = 50

admin.site.register(Todo, TodoAdmin)

admin.site.site_header = 'ToDoList admin'
admin.site.site_title = 'ToDoList admin'
admin.site.index_title = 'Task management'
