import json

from django.core.cache import cache
<<<<<<< HEAD:backend/tasks/views.py

from rest_framework import viewsets
=======
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status, viewsets
>>>>>>> 8c201bfeefa40177a9044714891cc0f7c9ec53f4:backend/todo_list/views.py
from rest_framework.response import Response
from rest_framework.views import APIView

<<<<<<< HEAD:backend/tasks/views.py
from .cache import TASK_LIST_CACHE_KEY, TASK_LIST_CACHE_TTL, clear_task_list_cache
=======
from . import agent
>>>>>>> 8c201bfeefa40177a9044714891cc0f7c9ec53f4:backend/todo_list/views.py
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
<<<<<<< HEAD:backend/tasks/views.py
        clear_task_list_cache()
=======
        self.clear_cache()

    @staticmethod
    def clear_cache():
        cache.delete(TASK_LIST_CACHE_KEY)


@ensure_csrf_cookie
def csrf(request):
    """Make Django set the csrftoken cookie so the React SPA can send it back."""
    return JsonResponse({'detail': 'CSRF cookie set'})


class ChatView(APIView):
    """Chat with the Gemini-backed assistant. All LLM traffic goes through here.

    POST /api/chat/  {"message": "...", "history": [{"role": "user", "text": "..."}]}
    -> {"reply": "...", "actions": [{"tool": "create_task", "result": {...}}]}

    The browser never sees GEMINI_API_KEY - it stays server-side in backend/.env.
    """

    def post(self, request):
        message = str(request.data.get('message', '')).strip()
        if not message:
            return Response({'detail': 'A message is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(message) > 2000:
            return Response(
                {'detail': 'Message must be at most 2000 characters.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        history = request.data.get('history', [])
        if not isinstance(history, list):
            return Response(
                {'detail': 'History must be a list.'}, status=status.HTTP_400_BAD_REQUEST
            )
        clean_history = [
            {'role': t.get('role'), 'text': str(t.get('text', ''))[:2000]}
            for t in history[-6:]
            if isinstance(t, dict)
        ]
        try:
            reply, actions = agent.chat(message, history=clean_history)
        except agent.AgentError as exc:
            return Response({'detail': str(exc)}, status=exc.status)
        return Response({'reply': reply, 'actions': actions})


# Voice clips are short (seconds), so a generous-but-bounded cap is enough.
MAX_AUDIO_BYTES = 15 * 1024 * 1024


class VoiceChatView(APIView):
    """Spoken chat: the browser records audio, Gemini transcribes it server-side.

    POST /api/chat/voice/   multipart form with an "audio" file part
    -> {"transcript": "...", "reply": "...", "actions": [...]}

    Used instead of the browser's SpeechRecognition API, whose speech service
    fails with a "network" error when Google's endpoint is unreachable and
    which only exists in Chromium browsers. MediaRecorder works in every
    modern browser and the clip travels the same trusted backend path as text
    messages - the API key and the transcription stay server-side.
    """

    def post(self, request):
        audio = request.FILES.get('audio')
        if audio is None:
            return Response(
                {'detail': 'An "audio" file is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if audio.size > MAX_AUDIO_BYTES:
            return Response(
                {'detail': 'Audio recording is too large (max 15 MB).'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        mime = audio.content_type or 'audio/webm'
        if not mime.startswith('audio/'):
            return Response(
                {'detail': 'Only audio uploads are accepted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        history = []
        history_raw = request.data.get('history', '')
        if history_raw:
            try:
                parsed = json.loads(history_raw)
                if isinstance(parsed, list):
                    history = parsed
            except (json.JSONDecodeError, TypeError):
                return Response(
                    {'detail': 'History must be a JSON list.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            transcript, reply, actions = agent.voice_chat(audio.read(), mime, history=history)
        except agent.AgentError as exc:
            return Response({'detail': str(exc)}, status=exc.status)
        return Response({'transcript': transcript, 'reply': reply, 'actions': actions})
>>>>>>> 8c201bfeefa40177a9044714891cc0f7c9ec53f4:backend/todo_list/views.py
