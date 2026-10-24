#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

if [ -d "smart_room_system" ]; then
    cd smart_room_system
fi

python manage.py collectstatic --noinput
python manage.py migrate
python manage.py loaddata data_dump.json || true
