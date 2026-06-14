# -*- coding: utf-8 -*-
from typing import List, Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 运行模式：本地演示和测试建议保持 Mock 模式。
    USE_MOCK: bool = True

    # 大模型提供方：mock、deepseek 或 openai。
    LLM_PROVIDER: str = "mock"

    # 红人数据源：rapidapi、mock、modash、hypeauditor、creatoriq、upfluence。
    # USE_MOCK=False 时默认使用 RapidAPI（失败自动降级 Mock）。
    INFLUENCER_PROVIDER: str = "rapidapi"

    # RapidAPI 红人检索（influencer-data1.p.rapidapi.com）
    RAPID_API_KEY: str = ""
    RAPID_API_HOST: str = "influencer-data1.p.rapidapi.com"

    # Campaign 匹配结果数量与文案生成数量。
    CAMPAIGN_TOP_K: int = 10
    CONTENT_TOP_K: int = 5

    # DeepSeek 凭据和网关地址。
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: Optional[str] = Field(
        default="https://api.deepseek.com/v1",
        validation_alias=AliasChoices("DEEPSEEK_BASE_URL", "DEEPSEEK_API_BASE"),
    )

    # OpenAI 凭据和网关地址。
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = "https://api.openai.com/v1"

    # 异步任务基础设施。
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_EXPIRES: int = 3600

    # PostgreSQL persistence. Local/test runs can keep the SQLite fallback; production should set
    # postgresql+psycopg://user:password@localhost:5432/ai_influencer_rag
    DATABASE_URL: str = "sqlite:///./data/ai_influencer.db"
    DB_AUTO_CREATE: bool = True

    # API 安全配置。
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    MAX_REQUIREMENT_LENGTH: int = 2000

    # RapidAPI 第一层召回池大小（粗筛候选人数）。
    CANDIDATE_POOL_MAX: int = 100

    # 详细营销要求最大长度。
    MAX_MARKETING_REQUIREMENTS_LENGTH: int = 2000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
