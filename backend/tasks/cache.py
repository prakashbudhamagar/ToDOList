"""Cache contract shared by the tasks API and the chat assistant.

The task list is the only read-heavy endpoint, so its JSON response is cached.
Every task write - through the REST API or the assistant's tools - must clear
this key, otherwise a change stays invisible until the TTL expires.
"""
from django.core.cache import cache

TASK_LIST_CACHE_KEY = 'tasks:task-list'
TASK_LIST_CACHE_TTL = 60


def clear_task_list_cache():
    """Forget the cached task list so the next read hits the database."""
    cache.delete(TASK_LIST_CACHE_KEY)