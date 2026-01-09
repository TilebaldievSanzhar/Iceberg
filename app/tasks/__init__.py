from celery import Celery

from app.config import settings

celery_app = Celery(
    "pfm",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
)

# ВАЖНО: Явный импорт задачи ПОСЛЕ создания celery_app
from app.tasks.process_upload import process_upload_task  # noqa: F401