import base64
import json
import urllib.error
import urllib.request

from django.core.cache import cache

# Gemini REST endpoint (v1beta generateContent). No SDK needed - plain HTTPS,
# so no extra dependency in requirements.txt.
API_BASE = 'https://generativelanguage.googleapis.com/v1beta'
DEFAULT_MODEL = 'gemini-3.6-flash'
MAX_TOOL_ROUNDS = 5

# Same key the list endpoint uses (see views.py) - any task write must clear it.
TASK_LIST_CACHE_KEY = 'todo_list:task-list'

SYSTEM_PROMPT = (
    'You are a friendly assistant for a todo-list app. '
    'Answer briefly in plain text (no markdown tables). '
    'Use the provided tools whenever the user wants to see, add, rename, '
    'or delete tasks - do not invent task IDs, call list_tasks first if you '
    'need them. After a tool result, confirm what happened in one short sentence. '
    'When the user asks what to do next or wants recommendations, call '
    'recommend_tasks first and base your suggestions on it; you may also '
    'propose new tasks, but only create them if the user agrees.'
)

class AgentError(Exception):
    """Raised when the chat backend cannot produce a reply."""

    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def get_config():
    """Read the Gemini key/model from Django settings (env-driven)."""
    from django.conf import settings

    api_key = (getattr(settings, 'GEMINI_API_KEY', '') or '').strip()
    if not api_key:
        raise AgentError(
            'No GEMINI_API_KEY is configured. Put your key in backend/.env '
            '(see backend/.env.example).',
            status=503,
        )
    model = (getattr(settings, 'GEMINI_MODEL', '') or '').strip() or DEFAULT_MODEL
    return api_key, model


def _tools():
    return [
        {
            'functionDeclarations': [
                {
                    'name': 'list_tasks',
                    'description': 'List all tasks with id, title and creation time.',
                },
                {
                    'name': 'create_task',
                    'description': 'Create a new task.',
                    'parameters': {
                        'type': 'OBJECT',
                        'properties': {
                            'title': {'type': 'STRING', 'description': 'Task title.'},
                        },
                        'required': ['title'],
                    },
                },
                {
                    'name': 'update_task',
                    'description': 'Rename an existing task by its id.',
                    'parameters': {
                        'type': 'OBJECT',
                        'properties': {
                            'id': {'type': 'INTEGER', 'description': 'Task id.'},
                            'title': {'type': 'STRING', 'description': 'New title.'},
                        },
                        'required': ['id', 'title'],
                    },
                },
                {
                    'name': 'delete_task',
                    'description': 'Delete a task by its id.',
                    'parameters': {
                        'type': 'OBJECT',
                        'properties': {
                            'id': {'type': 'INTEGER', 'description': 'Task id.'},
                        },
                        'required': ['id'],
                    },
                },
                {
                    'name': 'recommend_tasks',
                    'description': (
                        'Get task stats and the oldest tasks first, to base '
                        'recommendations on when the user asks what to do next.'
                    ),
                },
            ]
        }
    ]


def _execute_tool(name, args):
    """Run one model-requested tool against the local database."""
    from .models import Todo

    args = args or {}
    if name == 'list_tasks':
        rows = Todo.objects.order_by('-create_at').values('id', 'title', 'create_at')
        return {'tasks': [
            {'id': t['id'], 'title': t['title'], 'create_at': t['create_at'].isoformat()}
            for t in rows
        ]}

    if name == 'create_task':
        title = str(args.get('title', '')).strip()
        if not title:
            return {'error': 'Title must not be empty.'}
        if len(title) > 100:
            return {'error': 'Title must be at most 100 characters.'}
        todo = Todo.objects.create(title=title)
        cache.delete(TASK_LIST_CACHE_KEY)
        return {'id': todo.id, 'title': todo.title}

    if name == 'update_task':
        try:
            todo = Todo.objects.get(pk=int(args.get('id')))
        except (Todo.DoesNotExist, TypeError, ValueError):
            return {'error': f"No task with id {args.get('id')}."}
        title = str(args.get('title', '')).strip()
        if not title:
            return {'error': 'Title must not be empty.'}
        if len(title) > 100:
            return {'error': 'Title must be at most 100 characters.'}
        todo.title = title
        todo.save(update_fields=['title'])
        cache.delete(TASK_LIST_CACHE_KEY)
        return {'id': todo.id, 'title': todo.title}

    if name == 'delete_task':
        try:
            todo = Todo.objects.get(pk=int(args.get('id')))
        except (Todo.DoesNotExist, TypeError, ValueError):
            return {'error': f"No task with id {args.get('id')}."}
        todo.delete()
        cache.delete(TASK_LIST_CACHE_KEY)
        return {'deleted': True}

    if name == 'recommend_tasks':
        oldest = Todo.objects.order_by('create_at').values('id', 'title', 'create_at')[:5]
        return {
            'total': Todo.objects.count(),
            'focus_next': [
                {'id': t['id'], 'title': t['title'], 'create_at': t['create_at'].isoformat()}
                for t in oldest
            ],
        }

    return {'error': f'Unknown tool: {name}.'}


def _generate(payload, api_key, model):
    """Single generateContent call. Separated out so tests can stub it."""
    url = f'{API_BASE}/models/{model}:generateContent?key={api_key}'
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode('utf-8'))
            message = detail.get('error', {}).get('message', str(detail))
        except Exception:
            message = f'Gemini API error {exc.code}'
        raise AgentError(f'Gemini rejected the request: {message}', status=502)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise AgentError(f'Could not reach Gemini: {exc}.', status=504)


def chat(message, history=None):
    """Talk to Gemini with todo tools. Returns (reply_text, actions)."""
    api_key, model = get_config()

    contents = []
    for turn in history or []:
        role = 'model' if turn.get('role') == 'model' else 'user'
        text = str(turn.get('text', ''))[:2000]
        if text.strip():
            contents.append({'role': role, 'parts': [{'text': text}]})
    contents.append({'role': 'user', 'parts': [{'text': message}]})

    payload = {
        'system_instruction': {'parts': [{'text': SYSTEM_PROMPT}]},
        'contents': contents,
        'tools': _tools(),
        'toolConfig': {'functionCallingConfig': {'mode': 'AUTO'}},
        'generationConfig': {'temperature': 0.7, 'maxOutputTokens': 512},
    }

    actions = []
    for _ in range(MAX_TOOL_ROUNDS):
        data = _generate(payload, api_key, model)
        try:
            parts = data['candidates'][0]['content']['parts']
        except (KeyError, IndexError, TypeError):
            raise AgentError('Gemini returned an unexpected response.', status=502)

        calls = [p['functionCall'] for p in parts if 'functionCall' in p]
        texts = [p['text'] for p in parts if p.get('text')]
        if not calls:
            reply = '\n'.join(texts).strip()
            return reply or 'No reply - please try again.', actions

        # Echo the ORIGINAL model parts verbatim: gemini-3.x attaches a
        # thoughtSignature to its parts and rejects the follow-up call if any is
        # missing (rebuilding [{'functionCall': c}] drops them - see the
        # thought-signatures docs). Echoing the full turn keeps both text and
        # function-call signatures intact.
        payload['contents'].append({'role': 'model', 'parts': list(parts)})
        responses = []
        for call in calls:
            name = call.get('name', '')
            result = _execute_tool(name, call.get('args') or {})
            actions.append({'tool': name, 'result': result})
            responses.append({'functionResponse': {'name': name, 'response': result}})
        # Gemini only accepts user/model roles: tool results go back as 'user'.
        payload['contents'].append({'role': 'user', 'parts': responses})

    return 'Done - I ran the requested changes.', actions


def _transcribe(audio_bytes, mime_type, api_key, model):
    """One transcription-only generateContent call for a voice recording."""
    payload = {
        'contents': [{'role': 'user', 'parts': [
            {
                'text': 'Transcribe this voice message. Reply with only the spoken '
                        'words, in the language they were spoken in - nothing else.',
            },
            {
                'inline_data': {
                    'mime_type': mime_type,
                    'data': base64.b64encode(audio_bytes).decode('ascii'),
                },
            },
        ]}],
        'generationConfig': {'temperature': 0, 'maxOutputTokens': 1024},
    }
    data = _generate(payload, api_key, model)
    try:
        parts = data['candidates'][0]['content']['parts']
        text = '\n'.join(p['text'] for p in parts if p.get('text')).strip()
    except (KeyError, IndexError, TypeError):
        text = ''
    if not text:
        raise AgentError('Could not transcribe that recording - please try again.', status=502)
    return text


def voice_chat(audio_bytes, mime_type, history=None):
    """Voice entry point: transcribe with Gemini, then run the normal agent.

    Returns (transcript, reply, actions) so the UI can show what was heard.
    """
    api_key, model = get_config()
    transcript = _transcribe(audio_bytes, mime_type, api_key, model)
    reply, actions = chat(transcript, history=history)
    return transcript, reply, actions

