# -*- coding: utf-8 -*-
"""Provider 检索上下文，供 API 层读取数据来源而不侵入 CampaignMatcher。"""
from contextvars import ContextVar
from typing import Any, Dict, Optional

_search_meta: ContextVar[Optional[Dict[str, Any]]] = ContextVar("provider_search_meta", default=None)


def set_search_meta(meta: Dict[str, Any]) -> None:
    _search_meta.set(meta)


def get_search_meta() -> Dict[str, Any]:
    return _search_meta.get() or {
        "data_source": "mock",
        "fallback_message": None,
    }


def clear_search_meta() -> None:
    _search_meta.set(None)
