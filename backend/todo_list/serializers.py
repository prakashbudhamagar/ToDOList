from rest_framework import serializers

from .models import Todo


class TodoSerializer(serializers.ModelSerializer):
    """JSON representation of a task used by the /api/ endpoints."""

    class Meta:
        model = Todo
        fields = ['id', 'title', 'create_at']
        read_only_fields = ['id', 'create_at']
