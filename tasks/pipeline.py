# -*- coding: utf-8 -*-
import logging
from typing import Any, Dict

from celery import Task

from core.mock_data import MockDataLoader
from core.rag_engine import InfluencerRagEngine
from tasks.celery_app import celery_app

logger = logging.getLogger("celery.task")


class RAGTask(Task):
    _rag_engine = None

    @property
    def rag_engine(self) -> InfluencerRagEngine:
        if self._rag_engine is None:
            logger.info("正在为当前 Celery Worker 加载 RAG 引擎。")
            self._rag_engine = InfluencerRagEngine()
        return self._rag_engine


@celery_app.task(base=RAGTask, bind=True, name="tasks.pipeline.run_rag_matching")
def run_rag_matching(self: RAGTask, merchant_requirement: str) -> Dict[str, Any]:
    task_id = self.request.id
    if not merchant_requirement or not merchant_requirement.strip():
        raise ValueError("需求不能为空。")

    logger.info("任务 %s 已收到商家需求。", task_id)

    self.update_state(state="LOADING_DATA", meta={"message": "正在加载红人数据。"})
    loader = MockDataLoader()
    raw_influencers = loader.get_all_influencers()

    self.update_state(state="BUILDING_INDEX", meta={"message": "正在构建红人检索索引。"})
    engine = self.rag_engine
    engine.build_index(raw_influencers)

    self.update_state(state="GENERATING", meta={"message": "正在生成红人匹配结果和开发信草稿。"})
    result_text = engine.query(merchant_requirement)

    logger.info("任务 %s 已成功完成。", task_id)
    return {
        "task_id": task_id,
        "status": "SUCCESS",
        "data": result_text,
    }
