web: gunicorn config.wsgi
worker: python manage.py process_tasks
release: python manage.py migrate && python manage.py collectstatic --noinput
