#!/bin/sh
# Runs before the CMD: the SQLite database sits on a volume, so on a brand new
# volume the tables do not exist yet.
set -e

python manage.py migrate --noinput
# Gather the admin CSS/JS into STATIC_ROOT so WhiteNoise can serve it
# (STATIC_URL). Without this the admin renders as unstyled HTML.
python manage.py collectstatic --noinput --clear

exec "$@"