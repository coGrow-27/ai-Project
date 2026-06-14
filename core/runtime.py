# -*- coding: utf-8 -*-
"""统一运行模式判定，支持 Mock / 真实模式无缝切换。"""

from typing import Optional

from config.settings import settings


def rag_mode() -> str:
    return "mock" if settings.USE_MOCK else "vector"


def llm_mode() -> str:
    return settings.LLM_PROVIDER.lower()


def provider_mode() -> str:
    if settings.USE_MOCK:
        return "mock"
    return settings.INFLUENCER_PROVIDER.lower()


def is_rag_mock() -> bool:
    return settings.USE_MOCK


def is_llm_mock() -> bool:
    return llm_mode() == "mock"


def is_llm_enabled() -> bool:
    if is_llm_mock():
        return False
    provider = llm_mode()
    if provider == "deepseek":
        return _valid_key(settings.DEEPSEEK_API_KEY)
    if provider == "openai":
        return _valid_key(settings.OPENAI_API_KEY)
    return False


def is_rapidapi_configured() -> bool:
    key = (settings.RAPID_API_KEY or "").strip()
    host = (settings.RAPID_API_HOST or "").strip()
    if not key or not host:
        return False
    lowered = key.lower()
    return not _is_placeholder_key(lowered)


def is_redis_available() -> bool:
    try:
        import redis

        client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        client.ping()
        return True
    except Exception:
        return False


def runtime_summary() -> dict:
    return {
        "use_mock": settings.USE_MOCK,
        "rag": rag_mode(),
        "llm": llm_mode(),
        "llm_active": is_llm_enabled(),
        "influencer_provider": provider_mode(),
        "rapidapi_configured": is_rapidapi_configured(),
        "redis_available": is_redis_available(),
        "campaign_top_k": settings.CAMPAIGN_TOP_K,
        "content_top_k": settings.CONTENT_TOP_K,
    }


def _valid_key(value: Optional[str]) -> bool:
    if not value:
        return False
    return not _is_placeholder_key(value.lower().strip())


def _is_placeholder_key(value: str) -> bool:
    return (
        not value
        or value == "placeholder"
        or value.startswith("placeholder")
        or value.startswith("your_")
        or value.startswith("sk" + "-placeholder")
        or value.startswith("sk" + "-your_")
    )
