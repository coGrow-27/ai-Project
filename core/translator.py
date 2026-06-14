# -*- coding: utf-8 -*-
"""Campaign 中文输入 → 英文检索/匹配翻译（RapidAPI 与评分引擎使用）。"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Dict
from urllib.parse import quote

import httpx

from core.llm_client import complete
from core.runtime import is_llm_enabled
from core.schemas import CampaignRequest

logger = logging.getLogger("translator")

CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")

CATEGORY_ZH_TO_EN: Dict[str, str] = {
    "宠物护理": "pet care",
    "宠物": "pet care",
    "美妆": "beauty makeup",
    "美容": "beauty",
    "护肤": "skincare beauty",
    "健身": "fitness",
    "家居": "home kitchen",
    "厨房": "home kitchen",
    "科技": "tech",
    "数码": "tech",
    "时尚": "fashion",
    "美食": "food",
    "母婴": "parenting",
    "旅行": "travel",
    "户外": "outdoor",
}


def contains_chinese(text: str) -> bool:
    return bool(CHINESE_RE.search(text or ""))


@lru_cache(maxsize=256)
def translate_to_english(text: str) -> str:
    """将中文文本翻译为英文；已是英文则原样返回。"""
    cleaned = (text or "").strip()
    if not cleaned:
        return cleaned
    if not contains_chinese(cleaned):
        return cleaned

    mapped = CATEGORY_ZH_TO_EN.get(cleaned)
    if mapped:
        return mapped

    if is_llm_enabled():
        llm_result = _translate_via_llm(cleaned)
        if llm_result:
            return llm_result

    remote = _translate_via_mymemory(cleaned)
    if remote:
        return remote

    logger.warning("翻译失败，保留原文：%s", cleaned[:40])
    return cleaned


def translate_campaign_for_api(campaign: CampaignRequest) -> Dict[str, str]:
    """供 RapidAPI 关键词与英文邀约信使用的 Campaign 英文字段。"""
    return {
        "product_name": translate_to_english(campaign.product_name),
        "product_category": translate_to_english(campaign.product_category),
        "product_description": translate_to_english(campaign.product_description),
        "influencer_category": translate_to_english(campaign.influencer_category),
    }


def _translate_via_llm(text: str) -> str | None:
    prompt = (
        "Translate the following Chinese marketing text into natural English for influencer search keywords. "
        "Output English only, no explanation.\n\n"
        f"{text}"
    )
    result = complete(prompt, temperature=0.1, max_tokens=300)
    if not result:
        return None
    translated = result.strip().strip('"').strip("'")
    if contains_chinese(translated):
        return None
    return translated


def _translate_via_mymemory(text: str) -> str | None:
    chunk = text[:480]
    url = (
        "https://api.mymemory.translated.net/get?"
        f"q={quote(chunk)}&langpair=zh-CN|en"
    )
    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()
            translated = payload.get("responseData", {}).get("translatedText", "")
            if not translated or contains_chinese(translated):
                return None
            if translated.upper().startswith("QUERY LENGTH"):
                return None
            return translated.strip()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("MyMemory 翻译失败：%s", exc)
        return None
