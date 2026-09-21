# ToDOList

A small todo list. Django (with Django REST Framework) exposes a JSON API and the
React single-page app in `frontend/` is the user interface: add a task with a
priority, edit a task through an inline form, change its priority in one click,
and delete a task after confirming. A Gemini assistant in the corner can do the
same by chat and, when you ask what to do next, recommends tasks with a rough
estimate of how long each may take.

There are two ways to run it:

- **Docker Compose** - one command, no local Python or Node needed:
  `docker compose up --build` then open <http://localhost:8080>
- **Local dev servers** - Django on :8000 and Vite on :5173 (hot reload)

## Tech stack

| Component | Version |
|---|---|
| Python | 3.11 |
| Django | 5.2.17 |
| Django REST Framework | 3.18.1 |
| django-cors-headers | 4.9.0 |
| Database | SQLite (`backend/db.sqlite3` locally, a volume in Docker) |
| Cache | Redis 8 via django-redis 7 (Docker), in-process memory cache otherwise |
| Frontend | React 19 + Vite 8 (in `frontend/`) |
| AI assistant | Google Gemini (`gemini-3.6-flash` default) via `POST /api/chat/` - key in `backend/.env`, never in the browser |
| Node.js (frontend only) | 22 |
| gunicorn (Docker only) | 26.2.0 |
| Docker images | `python:3.11-slim`, `node:22-alpine`, `nginx:1.27-alpine` |

## Architecture

Django serves JSON only (`/api/` plus `/admin/`); every screen comes from the
React app in `frontend/`.

```text
browser
   |  http://localhost:8080                http://localhost:5173 (dev)
   v
[ web: nginx ]  --/api/-->  [ api: gunicorn/Django ]  -->  SQLite (volume)
   |                              |      ^
   +-- static React bundle        |      +-- same-origin: no CORS preflight,
                                  |          first-party csrftoken cookie
                                  +--> [ redis ]  cached task list (60s TTL)
                                  +--> [ Gemini ] chat assistant (/api/chat/)
```

## Running with Docker

```powershell
# from the repository root

docker compose up --build      # build both images and start the stack
# -> open http://localhost:8080

docker compose logs -f api     # follow the API logs
docker compose down            # stop; tasks are kept on the volume
docker compose down -v         # stop and delete the stored tasks
```

| Service | Built from | Role |
|---|---|---|
| `api` | `backend/Dockerfile` | Django + DRF behind gunicorn on :8000, SQLite at `/app/data/db.sqlite3` on the `sqlite-data` volume |
| `web` | `frontend/Dockerfile` | builds the React bundle with Node, serves it with nginx on :8080 and proxies `/api/` to `api:8000` |
| `redis` | `redis:8-alpine` | cache for the task list; internal to the compose network (no published port, no volume) |

The browser only ever talks to port 8080: nginx serves the bundle and forwards
`/api/` to the API container. That is the same single-origin setup as the Vite dev
proxy, so there is no CORS preflight and the `csrftoken` cookie stays first-party.
The API is also published on `:8000`, so you can run a Vite dev server on the host
against the containerized API.

### Configuration

Everything configurable is read from the environment (`docker-compose.yml` sets it):

| Variable | Purpose | Value in compose |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret key - **replace it** | `django-insecure-change-me-before-deploying` |
| `DJANGO_DEBUG` | Django debug mode | `False` |
| `DJANGO_ALLOWED_HOSTS` | comma-separated host names, no ports | `localhost,127.0.0.1,api` |
| `CSRF_TRUSTED_ORIGINS` | extra origins allowed to send write requests | `http://localhost:8080,http://127.0.0.1:8080` |
| `CORS_ALLOWED_ORIGINS` | extra origins allowed to read the API | `http://localhost:8080,http://127.0.0.1:8080` |
| `SQLITE_PATH` | where the database file lives | `/app/data/db.sqlite3` |
| `REDIS_URL` | cache location; leave unset to use the in-process memory cache | `redis://redis:6379/0` |
| `GEMINI_API_KEY` | LLM key for the `/api/chat/` assistant | read from `backend/.env`, which compose mounts with `env_file` |
| `GEMINI_MODEL` | Gemini model name | `gemini-3.6-flash` (also from `backend/.env`) |

The nginx entrypoint proxies `/api/` only, so Django admin is not exposed in
Docker. Run Django directly to use the admin (see below).

## Caching

`GET /api/todos/` is the hot read path, so `TodoViewSet.list` keeps its response in
the cache for 60 seconds and every create/update/delete deletes that key - a write
is always visible on the next read (`backend/tasks/views.py`).

| Setup | Cache backend |
|---|---|
| Docker Compose | Redis (`REDIS_URL=redis://redis:6379/0`), reachable only from the compose network |
| Local `runserver` | in-process memory cache, so no Redis installation is required |

Wanted Redis for local development too? Run one on a free host port:

```powershell
docker run -d --name todolist-redis -p 6380:6379 redis:8-alpine
$env:REDIS_URL = 'redis://localhost:6380/0'
cd backend
python manage.py runserver
```

Redis is used strictly as a cache: the compose service has no volume (nothing is
lost on restart) and publishes no port (so it cannot clash with another Redis on
:6379). If Redis is unreachable the API keeps serving - cache errors are ignored and
the endpoints fall back to SQLite.

## Priorities

Every task carries one of three levels - Low (`1`), Medium (`2`, the default) and
High (`3`). The level is stored as a number so the database can sort on it, which
is what puts high-priority tasks at the top of `GET /api/todos/`; within a level
the oldest task comes first (`Todo.Meta.ordering` in `backend/tasks/models.py`).

| Where | How to set it |
|---|---|
| Add form | dropdown next to the title input, tinted for the chosen level |
| Task row | dropdown on the right of the row - a change is saved immediately |
| Edit form | dropdown next to the title, saved together with the title |
| Admin | editable column in the changelist, plus a priority filter |
| Assistant | just say it: "add buy milk as high priority" (`create_task` and `update_task` accept `low`, `medium`, `high`) |

The tint of the dropdown comes from `.priority-low` / `.priority-medium` /
`.priority-high` in `frontend/src/index.css`; the levels themselves are defined
once, in `frontend/src/features/todos/priorities.js`.

### How long a task may take

`backend/tasks/estimates.py` turns a title into a plausible duration: a short
title is treated as a quick errand, a longer one as more work, and a few verbs
(`call`, `email` mean quick; `write`, `review`, `plan` mean at least an hour)
nudge the result. Nothing is stored - the estimate is computed when the
assistant's `recommend_tasks` tool runs, and the model is instructed to quote it
("about 45 min"). Treat the numbers as planning hints, never as promises.

## Local development

### Requirements

- Python 3.11+ and the pinned packages in [`backend/requirements.txt`](backend/requirements.txt)
- Node.js 18+ for the React frontend (`npm install`)
- Docker Desktop is only needed for the containerized setup

```powershell
# 0. From the repository root: D:\self\todolist\ToDOList

# 1. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies (gunicorn is Linux-only, skip it on Windows)
pip install -r backend/requirements.txt

# 3. Create the database tables
cd backend
python manage.py migrate
```

> If activating the venv is blocked by the execution policy, run
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` first.

### Running the servers

```powershell
# terminal 1 - Django API (http://127.0.0.1:8000)
cd backend
python manage.py runserver

# terminal 2 - React dev server (http://localhost:5173)
cd frontend
npm install        # first time only
npm run dev
```

Open <http://localhost:5173/> - that is the only page of the app. On port 8000
there is nothing but `/api/` and `/admin/`. `frontend/vite.config.js` proxies
`/api/*` to `http://127.0.0.1:8000`.

### API endpoints

| Method | URL | Purpose |
|---|---|---|
| GET | `/api/todos/` | list tasks (high priority first, then oldest first) |
| POST | `/api/todos/` | create a task (`{"title": "...", "priority": 3}`; `priority` is optional and defaults to `2` = Medium) |
| GET | `/api/todos/<id>/` | retrieve one task |
| PUT / PATCH | `/api/todos/<id>/` | update a task (the React app uses PATCH, so `create_at` is untouched) |
| DELETE | `/api/todos/<id>/` | delete a task |
| GET | `/api/csrf/` | sets the `csrftoken` cookie used for write requests |
| POST | `/api/chat/` | chat with the Gemini assistant (`{"message": "...", "history": [...]}` -> `{"reply": "...", "actions": [...]}`); recommendations come back with an estimated duration per task |

Every task has a priority: `1` = Low, `2` = Medium (default), `3` = High - see
`Todo.Priority` in `backend/tasks/models.py`. Responses include both the stored
number (`priority`) and its label (`priority_label`, e.g. `"High"`), and the
inventory is served ordered by priority (high first) and then by age, so the list
reads as a plan rather than a log.

Open any `/api/` URL in a browser to use DRF's browsable API. Write requests need
the `X-CSRFToken` header when you are also logged into the admin in the same
browser (session authentication) - `frontend/src/shared/api/client.js` sends it for you.

### Frontend build

```powershell
cd frontend
npm run build      # outputs frontend/dist (git-ignored)
npm run preview    # serve the built bundle locally
```

## Monorepo tooling

The repo root is an [npm workspaces](https://docs.npmjs.com/cli/v10/using-npm/workspaces)
monorepo with [Turborepo](https://turbo.build/repo) orchestrating tasks across
both `frontend/` (npm/Vite) and `backend/` (Python/Django). `backend/package.json`
has no real npm dependencies - it exists only so Turborepo can drive the Django
commands with the same interface as the frontend.

### One-time setup

```powershell
# from the repository root
npm run setup
```

This runs `npm install` (linking both workspaces and installing frontend deps),
then creates `backend/.venv` and installs `backend/requirements.txt` into it.

### Everyday commands (run from the repository root)

| Command | What it does |
|---|---|
| `npm run dev` | Runs both dev servers together (Vite on :5173, Django on :8000) via Turborepo |
| `npm run dev:frontend` | Just the Vite dev server |
| `npm run dev:backend` | Just `python manage.py runserver` |
| `npm run build` | Builds the frontend bundle and runs Django `collectstatic`, in dependency order, with Turborepo's cache (unchanged packages are skipped on repeat runs) |
| `npm run lint` | Lints both packages (backend needs `flake8` installed; skipped gracefully if it's missing) |
| `npm run test` | Runs `python manage.py test` for the backend and any frontend tests |
| `npm run clean` | Removes build artifacts, `.venv`, and `node_modules` from both packages |

Each workspace still works standalone exactly as before (`cd backend && python
manage.py runserver`, `cd frontend && npm run dev`) - the root scripts are a
convenience layer on top, not a replacement.

### Layout

```text
ToDOList/
├── package.json        # workspace root: "workspaces": ["frontend", "backend"]
├── turbo.json           # task pipeline (dev/build/lint/test/clean)
├── frontend/
│   └── package.json     # real npm dependencies (React, Vite, ...)
└── backend/
    ├── package.json     # scripts only, no npm dependencies
    └── scripts/pip-install.js   # cross-platform "pip install -r requirements.txt"
```

## AI assistant

A chat widget (bottom-right of the React app) talks to Google Gemini. The flow is
deliberately backend-only so the key can never leak:

```
browser -- POST /api/chat/ {message, history} --> Django --> Gemini API
browser <-- {reply, actions} <-- Django <-- tool results + final answer
```

- The key lives in `backend/.env` as `GEMINI_API_KEY` (git-ignored; copy
  `backend/.env.example` to `backend/.env` and paste a free key from
  <https://aistudio.google.com/apikey>). `backend/config/settings.py` loads that
  file for a local `runserver`, and `docker-compose.yml` hands the same file to
  the api container with `env_file: ./backend/.env`. That file is the only
  source: the key is deliberately *not* repeated under the service's
  `environment:` block, because an `environment` entry overrides `env_file` and
  would replace the key with an empty string whenever the host shell has no copy
  of it.
- `backend/chat/agent.py` calls Gemini's `generateContent` REST endpoint with
  plain `urllib` (no SDK dependency) and exposes five tools the model can call:
  `list_tasks`, `create_task`, `update_task`, `delete_task`, `recommend_tasks`.
  The first four take an optional `priority` (`low`/`medium`/`high`);
  `recommend_tasks` returns the task count plus the five tasks to tackle first -
  urgent before old, each with its priority and an estimated duration from
  `tasks/estimates.py` - so the model can answer "what should I do next?" with
  both an order and a time budget. Tool writes go straight to the database and
  clear the cached task list, so the UI reload shows them immediately.
- `POST /api/chat/` (`ChatView` in `backend/chat/views.py`) validates the
  message (required, max 2000 chars; last 6 history turns forwarded) and returns
  `{"reply": "...", "actions": [...]}`. With no key configured it answers 503.
- The React side is `frontend/src/features/chat/components/ChatPanel.jsx` (floating Chat
  button -> panel with bubbles, "Thinking…" state and error display), `sendChatMessage`
  in `frontend/src/features/chat/api.js`, and a `reload` action from
  `frontend/src/features/todos/useTodos.js` so the
  list refreshes whenever the assistant ran a task tool. Voice is built into the
  panel with the browser's free Web Speech API (no key, no dependency): a Speak
  button fills the input via SpeechRecognition, and replies are read aloud via
  speechSynthesis with a "Speak replies" toggle (best in Chrome/Edge over
  HTTP-or-HTTPS `localhost`; the button hides itself where unsupported).

Without a key the endpoint returns 503 and the widget shows the error; the chat
tests in `backend/chat/tests/test_chat.py` stub the Gemini HTTP call, so
`python manage.py test` needs no key and no network.

> Seeing `503 No GEMINI_API_KEY is configured` while the key *is* in
> `backend/.env`? Django reads that file once at start-up, so restart the server
> after editing it (`runserver` does not auto-reload on `.env` changes); with
> Docker re-create the container with
> `docker compose up -d --force-recreate api`. Current AI Studio keys look like
> `AQ.Ab8R…` and older ones like `AIza…` - both are accepted.

## Admin

The admin is styled and usable in both modes: static files are served by
`runserver` locally and by WhiteNoise (+ `collectstatic` in
`docker-entrypoint.sh`) in Docker. `tasks/admin.py` configures a
`TodoAdmin` with columns, newest-first ordering, search, date filters and
branding (`ToDoList admin` / `Task management`).

```powershell
cd backend
python manage.py createsuperuser
python manage.py runserver     # then open http://127.0.0.1:8000/admin/
```

With Docker the admin lives behind the same origin as the app:
<http://localhost:8080/admin/> (nginx proxies `/admin/` and `/static/` to
the API container).

## Tests

```powershell
cd backend
python manage.py test
```

## Project layout

```
ToDOList/                          <- repository root
├── .gitattributes                 <- *.sh keeps LF endings (runs in Linux containers)
├── .gitignore
├── README.md
├── docker-compose.yml             <- api (Django) + web (nginx/React)
├── backend/                       <- Django project (JSON API only)
│   ├── .dockerignore              <- keeps the API build context small
│   ├── .env.example             <- copy to .env, paste GEMINI_API_KEY (git-ignored)
│   ├── Dockerfile                 <- python:3.11-slim + gunicorn
│   ├── docker-entrypoint.sh       <- migrate, then start gunicorn
│   ├── manage.py
│   ├── requirements.txt           <- pinned Python dependencies (incl. gunicorn)
│   ├── db.sqlite3                 <- local database (not committed)
│   ├── config/                    <- project package (settings, root urls, shared csrf view)
│   │   ├── settings.py            <- env-driven (secret key, debug, hosts, SQLITE_PATH)
│   │   ├── urls.py                <- admin + /api/csrf/ + includes each feature's urls
│   │   ├── views.py               <- the shared csrf endpoint (cross-feature infra)
│   │   ├── tests.py               <- tests for the shared config pieces
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── tasks/                     <- feature app: task CRUD
│   │   ├── models.py              <- Todo model (title, priority, create_at)
│   │   ├── estimates.py           <- 'how long may this take' heuristic (assistant only)
│   │   ├── serializers.py         <- TodoSerializer (priority + priority_label)
│   │   ├── cache.py               <- task-list cache key + clear helper (shared with chat)
│   │   ├── views.py               <- TodoViewSet (/api/todos/)
│   │   ├── urls.py                <- the todos router
│   │   ├── admin.py
│   │   ├── migrations/
│   │   └── tests/
│   │       ├── test_models.py
│   │       ├── test_estimates.py
│   │       └── test_api.py
│   └── chat/                      <- feature app: AI assistant
│       ├── agent.py               <- Gemini chat backend + task tools (urllib, no SDK)
│       ├── views.py               <- ChatView (/api/chat/)
│       ├── urls.py
│       └── tests/
│           └── test_chat.py
└── frontend/                      <- React + Vite SPA (the only user interface)
    ├── .dockerignore
    ├── Dockerfile                 <- node build stage -> nginx runtime stage
    ├── nginx.conf                 <- serves the bundle, proxies /api/ -> api:8000
    ├── index.html
    ├── package.json
    ├── package-lock.json
    ├── vite.config.js             <- dev proxy /api -> 127.0.0.1:8000
    └── src/
        ├── main.jsx
        ├── App.jsx                <- page shell (composition only)
        ├── index.css
        ├── shared/
        │   └── api/
        │       └── client.js      <- fetch wrapper + CSRF handling (used by all features)
        └── features/              <- one folder per feature (work one feature at a time)
            ├── todos/             <- task CRUD feature
            │   ├── api.js         <- one function per /api/todos/ endpoint
            │   ├── priorities.js  <- the three levels + their labels (single source)
            │   ├── useTodos.js    <- task state and API actions (incl. reload)
            │   ├── index.js       <- the feature's public exports
            │   └── components/
            │       ├── AddTodoForm.jsx  <- create a task (title + priority)
            │       ├── PrioritySelect.jsx <- tinted priority dropdown, reused everywhere
            │       ├── TodoList.jsx     <- rows, loading and empty state
            │       └── TodoItem.jsx     <- row, priority, inline edit, delete
            └── chat/              <- AI assistant feature
                ├── api.js         <- sendChatMessage (/api/chat/)
                ├── index.js       <- the feature's public exports
                └── components/
                    └── ChatPanel.jsx    <- floating assistant chat (talks to /api/chat/)
```

## Notes

- `venv/`, `db.sqlite3`, `__pycache__/`, `node_modules/` and `frontend/dist/` are
  excluded via `.gitignore`; the virtual environment and `node_modules` are
  recreated from `backend/requirements.txt` and `package-lock.json`.
- Two servers run in local development: Django on :8000 and Vite on :5173. Open
  the React app at <http://localhost:5173/> and use `localhost` rather than
  `127.0.0.1`, because Node 22 binds Vite to IPv6 (`::1`).
- The Docker API container runs one gunicorn worker with threads, because SQLite
  allows a single writer; more processes would just produce `database is locked`.
- Redis is a pure cache: no persistence and no published port, so
  `docker compose down` loses nothing but cached entries.
