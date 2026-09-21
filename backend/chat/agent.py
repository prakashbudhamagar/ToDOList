import json
import urllib.error
import urllib.request

from tasks.cache import clear_task_list_cache
from tasks.estimates import estimate_minutes, format_minutes
from tasks.models import Todo

# Gemini REST endpoint (v1beta generateContent). No SDK needed - plain HTTPS,
# so no extra dependency in requirements.txt.
API_BASE = 'https://generativelanguage.googleapis.com/v1beta'
DEFAULT_MODEL = 'gemini-3.6-flash'
MAX_TOOL_ROUNDS = 5
# How many tasks a recommendation looks at - a day's worth, not the whole list.
RECOMMEND_LIMIT = 5

SYSTEM_PROMPT = (
    'You are a friendly assistant for a todo-list app. '
    'Answer briefly in plain text (no markdown tables). '
    'Use the provided tools whenever the user wants to see, add, rename, '
    'reprioritise or delete tasks - do not invent task IDs, call list_tasks '
    'first if you need them. Every task has one of three priorities: low, '
    'medium or high. After a tool result, confirm what happened in one short '
    'sentence. When the user asks what to do next or wants recommendations, '
    'call recommend_tasks first and base your suggestions on it; always tell '
    'the user how long each recommended task may take (the estimate field) so '
    'they can plan their day. You may also propose new tasks, but only create '
    'them if the user agrees.'
)


class AgentError(Exception):
    """Raised when the chat backend cannot produce a reply."""

    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


class ToolInputError(Exception):
    """Raised when the model called a tool with arguments that cannot be used."""


def get_config():
    """Read the Gemini key/model from Django settings (env-driven)."""
    from django.conf import settings

    api_key = (getattr(settings, 'GEMINI_API_KEY', '') or '').strip()
    if not api_key:
        raise AgentError(
            'No GEMINI_API_KEY is configured. Put your key in backend/.env '
            '(see backend/.env.example) and restart the server - Django reads '
            'that file once at start-up.',
            status=503,
        )
    model = (getattr(settings, 'GEMINI_MODEL', '') or '').strip() or DEFAULT_MODEL
    return api_key, model


def _tools():
    # Shared by create_task and update_task so the model always sees one spelling.
    priority = {
        'type': 'STRING',
        'enum': ['low', 'medium', 'high'],
        'description': 'How urgent the task is; medium when unsure.',
    }
    return [
        {
            'functionDeclarations': [
                {
                    'name': 'list_tasks',
                    'description': 'List all tasks with id, title, priority and creation time.',
                },
                {
                    'name': 'create_task',
                    'description': 'Create a new task.',
                    'parameters': {
                        'type': 'OBJECT',
                        'properties': {
                            'title': {'type': 'STRING', 'description': 'Task title.'},
                            'priority': priority,
                        },
                        'required': ['title'],
                    },
                },
                {
                    'name': 'update_task',
                    'description': 'Change the title and/or priority of an existing task by its id.',
                    'parameters': {
                        'type': 'OBJECT',
                        'properties': {
                            'id': {'type': 'INTEGER', 'description': 'Task id.'},
                            'title': {'type': 'STRING', 'description': 'New title.'},
                            'priority': priority,
                        },
                        'required': ['id'],
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
                        'Get task stats and what to tackle first (urgent and oldest '
                        'tasks, each with an estimated duration in minutes), to base '
                        'recommendations on when the user asks what to do next.'
                    ),
                },
            ]
        }
    ]


def _task_row(todo, with_estimate=False):
    """One task as the model should see it: id, title, priority, age, duration."""
    row = {
        'id': todo.id,
        'title': todo.title,
        'priority': todo.get_priority_display(),
        'create_at': todo.create_at.isoformat(),
    }
    if with_estimate:
        minutes = estimate_minutes(todo.title)
        row['estimate_minutes'] = minutes
        row['estimate'] = format_minutes(minutes)
    return row


def _find_task(args):
    """The task the model pointed at; raises when the id cannot be resolved."""
    try:
        return Todo.objects.get(pk=int(args.get('id')))
    except (Todo.DoesNotExist, TypeError, ValueError):
        raise ToolInputError(f"No task with id {args.get('id')}.") from None


def _clean_title(value):
    """The model's title argument as a usable title; raises when it is not."""
    title = str(value or '').strip()
    if not title:
        raise ToolInputError('Title must not be empty.')
    if len(title) > 100:
        raise ToolInputError('Title must be at most 100 characters.')
    return title


def _clean_priority(value):
    """The model's priority argument as a stored level; raises when unknown."""
    priority = Todo.parse_priority(value)
    if priority is None:
        raise ToolInputError(f"Unknown priority '{value}' - use low, medium or high.")
    return priority


def _run_tool(name, args):
    """The tool implementations, one branch per declared function."""
    if name == 'list_tasks':
        return {'tasks': [_task_row(todo) for todo in Todo.objects.all()]}

    if name == 'create_task':
        todo = Todo.objects.create(
            title=_clean_title(args.get('title')),
            priority=_clean_priority(args.get('priority')) if args.get('priority')
            else Todo.Priority.MEDIUM,
        )
        clear_task_list_cache()
        return {'created': True, **_task_row(todo)}

    if name == 'update_task':
        todo = _find_task(args)
        changes = {}
        if args.get('title') is not None:
            changes['title'] = _clean_title(args.get('title'))
        if args.get('priority') is not None:
            changes['priority'] = _clean_priority(args.get('priority'))
        if not changes:
            raise ToolInputError('Nothing to change - pass a new title and/or priority.')
        for field, value in changes.items():
            setattr(todo, field, value)
        todo.save(update_fields=list(changes))
        clear_task_list_cache()
        return {'updated': True, **_task_row(todo)}

    if name == 'delete_task':
        _find_task(args).delete()
        clear_task_list_cache()
        return {'deleted': True}

    if name == 'recommend_tasks':
        # Urgent first, then oldest first: the model gets a ready-made plan, and
        # the estimate tells the user how much of their day each item costs.
        focus = Todo.objects.order_by('-priority', 'create_at')[:RECOMMEND_LIMIT]
        return {
            'total': Todo.objects.count(),
            'focus_next': [_task_row(todo, with_estimate=True) for todo in focus],
        }

    raise ToolInputError(f'Unknown tool: {name}.')


def _execute_tool(name, args):
    """Run one model-requested tool against the tasks feature.

    Anything the model got wrong (unknown id, empty title, bad priority) comes
    back as {'error': ...} so the model can correct itself on the next round.
    """
    try:
        return _run_tool(name, args or {})
    except ToolInputError as exc:
        return {'error': str(exc)}


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