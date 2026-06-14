# -*- coding: utf-8 -*-
import argparse
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.endpoints import router as api_router
from config.settings import settings
from core.mock_data import MockDataLoader
from core.rag_engine import InfluencerRagEngine
from database.session import init_db


def create_app() -> FastAPI:
    init_db()

    app = FastAPI(
        title="AI 红人 RAG 匹配平台",
        description="根据商家产品需求检索海外红人内容，并生成匹配理由与开发信草稿。",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1", tags=["红人匹配"])

    frontend_dir = Path(__file__).resolve().parent / "frontend"
    app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")

    @app.get("/", include_in_schema=False)
    async def frontend_home() -> FileResponse:
        return FileResponse(frontend_dir / "index.html")

    return app


app = create_app()


def run_local_test() -> None:
    print(f"当前环境：USE_MOCK={settings.USE_MOCK} | LLM_PROVIDER={settings.LLM_PROVIDER}")

    loader = MockDataLoader()
    raw_influencers = loader.get_all_influencers()
    print(f"已加载 {len(raw_influencers)} 条 Mock 红人数据。")

    product_desc = (
        "一款猫咪去毛梳，带人体工学防滑手柄、温和不伤皮肤的不锈钢梳针，"
        "并支持一键清理浮毛。"
    )

    rag_engine = InfluencerRagEngine()
    rag_engine.build_index(raw_influencers)
    print(rag_engine.generate_pitch_letter(product_desc))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI 红人 RAG 匹配平台运行器")
    parser.add_argument("--test", action="store_true", help="运行本地 Mock RAG 测试。")
    parser.add_argument("--serve", action="store_true", help="启动 FastAPI 开发服务。")
    args = parser.parse_args()

    if args.test:
        run_local_test()
    elif args.serve:
        import uvicorn

        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        parser.print_help()
