from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuelapp.settings')

# Create a Celery instance and configure it using the settings from Django.
app = Celery('fuelapp')

# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps.
app.autodiscover_tasks()

# Configure Celery Beat
app.conf.beat_schedule = {
    'health_check': {
        'task': 'fuelapp.tasks.health_check',
        'schedule': crontab(minute='*/15'),  # Adjust the schedule as
        # needed
    },
    'daily_task': {
        'task': 'fuelapp.tasks.daily_task',
        'schedule': crontab(minute='0', hour='10'),
    }
}

app.conf.timezone = 'Asia/Kolkata'
