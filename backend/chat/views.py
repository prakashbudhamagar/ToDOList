from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import agent


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