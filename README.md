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

Open any `/api/` URL in a browser to use DRF's browsable API. Write requests need
the `X-CSRFToken` header when you are also logged into the admin in the same
browser (session authentication) - `frontend/src/shared/api/client.js` sends it for you.

### Frontend build

```powershell
cd frontend
npm run build      # outputs frontend/dist (git-ignored)
npm run preview    # serve the built bundle locally
```

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
│   └── todo_list/                 <- the application
│       ├── models.py              <- Todo model (title, create_at)
│       ├── serializers.py         <- TodoSerializer
│       ├── views.py               <- TodoViewSet + csrf endpoint
│       ├── urls.py                <- the /api/ router
│       ├── admin.py
│       ├── migrations/
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
        ├── api/
        │   ├── client.js          <- fetch wrapper + CSRF handling
        │   └── todos.js           <- one function per endpoint
        ├── components/
        │   ├── AddTodoForm.jsx    <- create a task
        │   ├── TodoList.jsx       <- rows, loading and empty state
        │   └── TodoItem.jsx       <- row, inline edit, delete confirmation
        └── hooks/
            └── useTodos.js        <- task state and API actions
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
