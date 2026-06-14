# -*- coding: utf-8 -*-
import logging
from typing import Any, Dict

from celery import Task

from core.campaign_matcher import CampaignMatcher
from core.progress import progress_payload
from core.providers.context import get_search_meta
from core.schemas import CampaignRequest
from database.session import session_scope
from repositories.campaign_repository import CampaignRepository
from repositories.job_repository import JobRepository
from repositories.recommendation_repository import RecommendationResultRepository
from tasks.celery_app import celery_app

logger = logging.getLogger("celery.task")


class CampaignTask(Task):
    _matcher = None

    @property
    def matcher(self) -> CampaignMatcher:
        if self._matcher is None:
            self._matcher = CampaignMatcher()
        return self._matcher


@celery_app.task(base=CampaignTask, bind=True, name="tasks.campaign_pipeline.run_campaign_matching")
def run_campaign_matching(
    self: CampaignTask,
    campaign_payload: Dict[str, Any],
    campaign_id: str | None = None,
) -> Dict[str, Any]:
    task_id = self.request.id
    campaign = CampaignRequest.model_validate(campaign_payload)
    if campaign_id is None:
        with session_scope() as db:
            campaign_id = CampaignRepository(db).create(campaign).campaign_id

    def progress_callback(progress: int, stage: str, message: str) -> None:
        payload = progress_payload(progress, stage, message)
        self.update_state(state="PROGRESS", meta=payload)
        if campaign_id:
            with session_scope() as db:
                JobRepository(db).update_progress(task_id, progress, stage)

    progress_callback(0, "queued", "Task queued, waiting for worker...")
    try:
        result = self.matcher.match(campaign, progress_callback=progress_callback)
        meta = get_search_meta()
        enriched = result.model_copy(
            update={
                "data_source": meta.get("data_source", "mock"),
                "fallback_message": meta.get("fallback_message"),
            }
        )
        with session_scope() as db:
            RecommendationResultRepository(db).save_match_response(campaign_id, enriched)
            JobRepository(db).finish(task_id, "SUCCESS")
    except Exception:
        with session_scope() as db:
            JobRepository(db).finish(task_id, "FAILURE", progress=0, stage="failed")
        raise

    logger.info("Campaign task %s completed with %s candidates.", task_id, enriched.total_candidates)

    return {
        "task_id": task_id,
        "campaign_id": campaign_id,
        "status": "SUCCESS",
        "data": enriched.model_dump(mode="json"),
    }
