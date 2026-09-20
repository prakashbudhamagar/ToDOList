from django.db import models


class Todo(models.Model):
    """A single task shown in the todo list."""

    title = models.CharField(max_length=100)
    create_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
