import os
import json

from django.utils import timezone
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scheduler.settings')

app = Celery('scheduler')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

def create_perodic_event(task_func, task_name, scheduled_at, task_kwargs, one_off=True):
    from django_celery_beat.models import ClockedSchedule , PeriodicTask

    clocked, _ = ClockedSchedule.objects.get_or_create(
        clocked_time=scheduled_at-timezone.timedelta(hours=5, minutes=30))

    task_func_name = task_func.__module__ + "." + task_func.__name__

    task = PeriodicTask.objects.create(
        clocked=clocked, one_off=one_off, name=task_name,
        task=task_func_name, kwargs=json.dumps(task_kwargs))
    return task
