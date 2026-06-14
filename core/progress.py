# -*- coding: utf-8 -*-
"""Campaign 匹配进度回调与阶段定义。"""
from typing import Callable, Optional

ProgressCallback = Callable[[int, str, str], None]

STAGE_FETCHING = "fetching influencers"
STAGE_INDEXING = "building semantic index"
STAGE_SCORING = "calculating scores"
STAGE_OUTREACH = "generating outreach"
STAGE_COMPLETED = "completed"

# 兼容旧 stage 名称（测试/日志）
STAGE_SEARCHING = STAGE_FETCHING
STAGE_REASONING = STAGE_OUTREACH
STAGE_DONE = STAGE_COMPLETED


def emit_progress(
    callback: Optional[ProgressCallback],
    progress: int,
    stage: str,
    message: str,
) -> None:
    if callback is not None:
        callback(progress, stage, message)


def progress_payload(progress: int, stage: str, message: str) -> dict:
    return {"progress": progress, "stage": stage, "message": message}
