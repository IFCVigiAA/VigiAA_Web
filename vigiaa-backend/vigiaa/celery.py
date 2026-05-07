import os
from celery import Celery

# Define o modulo de configurações padrão do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vigiaa.settings')

app = Celery('vigiaa')

# Lê as configurações do Django com o prefixo CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descobre automaticamente tarefas em todas as apps (tasks.py)
app.autodiscover_tasks()