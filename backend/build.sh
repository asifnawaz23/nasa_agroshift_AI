#!/usr/bin/env bash
# Render build command (plan section 13). Rebuilds a fresh database in one go; every step is
# safe to repeat on each deploy.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_crops
python manage.py load_prepulled
