from rest_framework import serializers

from .models import Todo


class TodoSerializer(serializers.ModelSerializer):
    """JSON representation of a task used by the /api/ endpoints."""

    # Write the stored number, read back a word too, so the API is readable
    # without knowing the priority scale.
    priority_label = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Todo
        fields = ['id', 'title', 'priority', 'priority_label', 'create_at']
        read_only_fields = ['id', 'create_at', 'priority_label']