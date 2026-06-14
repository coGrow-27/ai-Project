# -*- coding: utf-8 -*-
from celery import Celery

from config.settings import settings


celery_app = Celery(
    "ai_influencer_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    imports=["tasks.pipeline", "tasks.campaign_pipeline"],
    result_expires=settings.CELERY_RESULT_EXPIRES,
    task_track_started=True,
    task_time_limit=180,
    task_soft_time_limit=150,
    worker_prefetch_multiplier=1,
)
