# -*- coding: utf-8 -*-
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.persistence import JobRecord


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, task_id: str, campaign_id: str, status: str = "PENDING") -> JobRecord:
        existing = self.get(task_id)
        if existing is not None:
            existing.campaign_id = campaign_id
            existing.status = status
            existing.progress = 0
            existing.stage = "queued"
            existing.start_time = datetime.now(timezone.utc)
            existing.finish_time = None
            self.db.flush()
            return existing

        record = JobRecord(
            task_id=task_id,
            campaign_id=campaign_id,
            status=status,
            progress=0,
            stage="queued",
            start_time=datetime.now(timezone.utc),
        )
        self.db.add(record)
        self.db.flush()
        return record

    def get(self, task_id: str) -> JobRecord | None:
        return self.db.get(JobRecord, task_id)

    def update_progress(self, task_id: str, progress: int, stage: str, status: str = "PROGRESS") -> None:
        record = self.get(task_id)
        if record is None:
            return
        record.status = status
        record.progress = progress
        record.stage = stage
        if record.start_time is None:
            record.start_time = datetime.now(timezone.utc)
        self.db.flush()

    def finish(self, task_id: str, status: str, progress: int = 100, stage: str = "completed") -> None:
        record = self.get(task_id)
        if record is None:
            return
        record.status = status
        record.progress = progress
        record.stage = stage
        record.finish_time = datetime.now(timezone.utc)
        self.db.flush()


def serialize_job(record: JobRecord) -> dict:
    return {
        "task_id": record.task_id,
        "campaign_id": record.campaign_id,
        "status": record.status,
        "progress": record.progress,
        "stage": record.stage,
        "start_time": record.start_time.isoformat() if record.start_time else None,
        "finish_time": record.finish_time.isoformat() if record.finish_time else None,
    }
