# API image: Django + Django REST Framework served by gunicorn.
#
# Build context is this directory (see docker-compose.yml), so build it with:
#   docker build -t todolist-api ./backend
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Requirements first, so this layer is reused when only the code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# manage.py, the config package and the feature apps (tasks, chat).
COPY . ./

# The SQLite file lives on a volume (SQLITE_PATH) so the tasks outlive the container.
RUN mkdir -p /app/data
VOLUME ["/app/data"]

# Git on Windows does not store POSIX permission bits, so set them explicitly.
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
# A single worker with threads: SQLite allows only one writer, so extra processes
# would only add "database is locked" errors on concurrent writes.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", \
     "--workers", "1", "--threads", "8", "--access-logfile", "-"]
