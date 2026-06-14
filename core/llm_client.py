# -*- coding: utf-8 -*-
import json
import logging
from typing import Optional

import httpx

from config.settings import settings
from core.runtime import is_llm_enabled, is_llm_mock

logger = logging.getLogger("llm_client")


def complete(prompt: str, *, temperature: float = 0.4, max_tokens: int = 1200) -> Optional[str]:
    """调用配置的 LLM。Mock 或未配置 Key 时返回 None，由调用方使用数据驱动兜底。"""
    if is_llm_mock() or not is_llm_enabled():
        return None

    provider = settings.LLM_PROVIDER.lower()
    if provider == "deepseek":
        return _chat_completion(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com/v1",
            model="deepseek-chat",
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    if provider == "openai":
        return _chat_completion(
            api_key=settings.OPENAI_API_KEY or "",
            base_url=settings.OPENAI_BASE_URL or "https://api.openai.com/v1",
            model="gpt-4o-mini",
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    logger.warning("未知 LLM_PROVIDER=%s，跳过 LLM 调用。", settings.LLM_PROVIDER)
    return None


def _chat_completion(
    *,
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
) -> Optional[str]:
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
        logger.error("LLM 调用失败：%s", exc)
        return None
