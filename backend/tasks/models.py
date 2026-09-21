from django.db import models


class Todo(models.Model):
    """A single task shown in the todo list."""

    class Priority(models.IntegerChoices):
        """How urgent a task is. Stored as a number so the database can sort."""

        LOW = 1, 'Low'
        MEDIUM = 2, 'Medium'
        HIGH = 3, 'High'

    title = models.CharField(max_length=100)
    priority = models.IntegerField(choices=Priority.choices, default=Priority.MEDIUM)
    create_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Urgent first, oldest first within a priority, so the list is a plan and
        # not just a log - the frontend renders the order as it comes from the API.
        ordering = ('-priority', 'create_at')

    def __str__(self):
        return self.title

    @classmethod
    def parse_priority(cls, value):
        """Turn 'high'/'High'/'3' into a ``Priority`` value; None when unknown.

        The chat assistant receives the level as a word from the model, while the
        REST API sends the stored number, so both spellings have to work.
        """
        if value is None or value == '':
            return None
        if isinstance(value, bool):  # bool is an int, but 'true' is not a priority
            return None
        if isinstance(value, int):
            return value if value in cls.Priority.values else None
        text = str(value).strip().lower()
        for member in cls.Priority:
            if text in (member.name.lower(), member.label.lower(), str(member.value)):
                return member.value
        return None