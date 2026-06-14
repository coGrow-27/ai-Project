# -*- coding: utf-8 -*-
import asyncio
import json
from typing import Any, Dict, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from kombu.exceptions import OperationalError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config.settings import settings
from core.campaign_matcher import CampaignMatcher
from core.providers.context import get_search_meta
from core.runtime import runtime_summary
from core.mock_data import MockDataLoader
from core.rag_engine import InfluencerRagEngine
from core.schemas import CampaignMatchResponse, CampaignRequest, Platform
from database.session import get_db
from repositories.campaign_repository import CampaignRepository, serialize_campaign
from repositories.job_repository import JobRepository, serialize_job
from repositories.recommendation_repository import RecommendationResultRepository
from tasks.celery_app import celery_app

router = APIRouter()


class MatchRequest(BaseModel):
    requirement: str = Field(
        ...,
        min_length=5,
        max_length=settings.MAX_REQUIREMENT_LENGTH,
        examples=[
            "为一款一键清理、温和不伤皮肤的猫咪去毛梳匹配美国宠物红人。"
        ],
    )


class MatchTaskResponse(BaseModel):
    message: str
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "正常", "runtime": runtime_summary()}


@router.get("/runtime")
async def runtime_info() -> Dict[str, Any]:
    return runtime_summary()


@router.post("/campaign/match", response_model=CampaignMatchResponse)
async def campaign_match(request: CampaignRequest, db: Session = Depends(get_db)) -> CampaignMatchResponse:
    matcher = CampaignMatcher()
    result = matcher.match(request)
    meta = get_search_meta()
    enriched = result.model_copy(
        update={
            "data_source": meta.get("data_source", "mock"),
            "fallback_message": meta.get("fallback_message"),
        }
    )
    if not enriched.results:
        raise HTTPException(
            status_code=404,
            detail="未找到符合筛选条件的红人，请放宽平台、粉丝或互动率要求后重试。",
        )
    campaign_record = CampaignRepository(db).create(request)
    RecommendationResultRepository(db).save_match_response(campaign_record.campaign_id, enriched)
    db.commit()
    return enriched


@router.post("/campaign/match/async", response_model=MatchTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def campaign_match_async(request: CampaignRequest, db: Session = Depends(get_db)) -> MatchTaskResponse:
    campaign_record = CampaignRepository(db).create(request)
    try:
        task = celery_app.send_task(
            "tasks.campaign_pipeline.run_campaign_matching",
            args=[request.model_dump(mode="json"), campaign_record.campaign_id],
        )
        JobRepository(db).create(task.id, campaign_record.campaign_id, status="PENDING")
        db.commit()
    except OperationalError:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Redis 未启动，无法提交异步任务。请取消「异步任务」勾选，使用同步匹配；或启动 Redis 与 Celery Worker。",
        )

    return MatchTaskResponse(
        message="Campaign 匹配任务已提交。",
        task_id=task.id,
        status="PENDING",
    )


@router.get("/campaigns")
async def list_campaigns(db: Session = Depends(get_db)) -> Dict[str, Any]:
    records = CampaignRepository(db).list()
    return {"items": [serialize_campaign(record) for record in records]}


@router.get("/campaigns/{campaign_id}")
async def get_campaign_detail(campaign_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    detail = CampaignRepository(db).get_detail(campaign_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return detail


@router.get("/jobs/{task_id}")
async def get_persisted_job(task_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    record = JobRepository(db).get(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return serialize_job(record)


@router.post("/demo/match")
async def demo_match(request: MatchRequest) -> Dict[str, Any]:
    """兼容旧接口：将自然语言需求写入 Campaign 主链路（含 RAG 语义匹配）。"""
    requirement = request.requirement.strip()
    if not requirement:
        raise HTTPException(status_code=400, detail="需求不能为空。")

    campaign = CampaignRequest(
        product_name="兼容模式产品",
        product_category="General",
        product_description=requirement,
        target_country="US",
        target_language="English",
        platforms=[Platform.youtube],
        min_followers=1000,
        max_followers=500000,
        min_engagement_rate=0.0,
        influencer_category="General",
        campaign_budget=1000,
        detailed_marketing_requirements=requirement,
    )
    matcher = CampaignMatcher()
    result = matcher.match(campaign)
    meta = get_search_meta()
    enriched = result.model_copy(
        update={
            "data_source": meta.get("data_source", "mock"),
            "fallback_message": meta.get("fallback_message"),
        }
    )
    return {
        "message": "已通过 Campaign 主链路完成匹配（含 RAG 语义评分）。",
        "status": "SUCCESS",
        "result": enriched.model_dump(mode="json"),
    }


@router.post("/match", response_model=MatchTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_match_task(request: MatchRequest) -> MatchTaskResponse:
    requirement = request.requirement.strip()
    if not requirement:
        raise HTTPException(status_code=400, detail="需求不能为空。")

    task = celery_app.send_task("tasks.pipeline.run_rag_matching", args=[requirement])

    return MatchTaskResponse(
        message="匹配任务已提交。",
        task_id=task.id,
        status="PENDING",
    )


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    result = AsyncResult(task_id, app=celery_app)

    if result.state == "SUCCESS":
        return TaskStatusResponse(task_id=task_id, status=result.state, result=result.result)
    if result.state == "FAILURE":
        return TaskStatusResponse(task_id=task_id, status=result.state, error="任务执行失败。")
    if isinstance(result.info, dict):
        return TaskStatusResponse(task_id=task_id, status=result.state, progress=result.info)

    return TaskStatusResponse(task_id=task_id, status=result.state)


@router.websocket("/ws/progress/{task_id}")
async def websocket_progress_endpoint(websocket: WebSocket, task_id: str) -> None:
    await websocket.accept()
    result = AsyncResult(task_id, app=celery_app)

    try:
        last_payload = None
        while True:
            payload: Dict[str, Any] = {"task_id": task_id, "status": result.state}

            if result.state == "SUCCESS":
                payload["result"] = result.result
                await websocket.send_text(json.dumps(payload, ensure_ascii=False))
                break
            if result.state == "FAILURE":
                payload["error"] = "任务执行失败。"
                await websocket.send_text(json.dumps(payload, ensure_ascii=False))
                break
            if isinstance(result.info, dict):
                payload["progress"] = result.info
                if "progress" in result.info:
                    payload["progress_pct"] = result.info.get("progress")
                if "stage" in result.info:
                    payload["stage"] = result.info.get("stage")
                if "message" in result.info:
                    payload["message"] = result.info.get("message")

            serialized = json.dumps(payload, ensure_ascii=False)
            if serialized != last_payload:
                await websocket.send_text(serialized)
                last_payload = serialized

            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
