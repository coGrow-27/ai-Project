# AI 红人 RAG 匹配平台

AI 红人 RAG 匹配平台是一个基于 FastAPI 的海外红人营销匹配 MVP。项目将品牌 Campaign Brief 转化为可解释的红人推荐结果：输出 Top 10 匹配排名，为 Top 5 生成推荐理由与中英双语邀约信，并保留基于 LlamaIndex 与 BGE Embedding 的 RAG 语义匹配实验链路。

项目采用 Provider 驱动架构：默认使用本地 Mock 数据完成零密钥演示与自动化测试，也可以切换到 RapidAPI YouTube 数据源进行真实红人召回。匹配编排层与数据来源解耦，便于后续接入 Modash、HypeAuditor、CreatorIQ、Upfluence 等第三方商业平台。

## 项目亮点

- **Campaign 匹配 MVP**：根据产品、目标市场、平台、粉丝区间和营销要求，生成 Top 10 红人推荐排名。
- **可解释评分体系**：使用 100 分制评分模型，拆解品类、关键词、市场、粉丝区间和内容活跃度等维度。
- **Top 5 内容生成**：为高匹配候选人生成推荐理由与中英双语邀约信，适合营销人员快速筛选与外联。
- **RAG 实验链路**：保留 LlamaIndex + BGE 向量检索能力，用于基于视频脚本、评论痛点和需求文本的语义匹配实验。
- **多模式运行**：支持 Mock 演示、RapidAPI 真实召回、DeepSeek/OpenAI 文案生成、Celery 异步任务和数据库持久化。
- **可扩展数据源**：通过 Provider 抽象隔离外部 API，新增商业平台时无需改动核心匹配与评分逻辑。

## 技术栈

| 层级 | 技术选型 |
| --- | --- |
| API 服务 | FastAPI, Pydantic v2, Uvicorn |
| 匹配核心 | CampaignMatcher, ScoringEngine, Provider Abstraction |
| 红人数据 | MockInfluencerProvider, RapidApiInfluencerProvider |
| RAG | LlamaIndex, HuggingFace BGE Embeddings |
| LLM 网关 | DeepSeek, OpenAI, Mock Fallback |
| 异步任务 | Celery, Redis, WebSocket Progress |
| 数据持久化 | SQLAlchemy, Alembic, SQLite/PostgreSQL |
| 前端 | 原生 HTML, CSS, JavaScript |
| 测试 | unittest, httpx AsyncClient |

## 系统架构

```text
Campaign 表单
  |
  +-- 同步接口 --> POST /api/v1/campaign/match       --> CampaignMatcher
  |
  +-- 异步接口 --> POST /api/v1/campaign/match/async --> Celery Worker
                                                            |
                                                            +-- WebSocket 进度推送

CampaignMatcher
  |
  +-- Provider.search(campaign)
  |     |
  |     +-- USE_MOCK=True  --> MockInfluencerProvider
  |     |
  |     +-- USE_MOCK=False --> RapidApiInfluencerProvider
  |                            |
  |                            +-- 异常、限流、空结果时降级到 Mock Provider
  |
  +-- ScoringEngine
  |
  +-- Top 10 推荐排名
  |
  +-- Top 5 推荐理由 + 中英双语邀约信

RAG 实验链路
  |
  +-- POST /api/v1/demo/match
  |
  +-- POST /api/v1/match
  |
  +-- InfluencerRagEngine
```

## 运行模式

| 模式 | 数据源 | RAG 策略 | 外部密钥 | 适用场景 |
| --- | --- | --- | --- | --- |
| Mock Mode | 本地 Fixture 数据 | 关键词 Mock Index | 不需要 | 本地演示、CI、单元测试 |
| Real API Mode | RapidAPI YouTube，失败降级 Mock | BGE 向量检索 | RapidAPI Key | 真实红人召回与评估 |
| LLM-enhanced Mode | Mock 或 RapidAPI | Mock 或 Vector RAG | DeepSeek/OpenAI Key | 生成推荐理由与邀约文案 |

查看当前运行状态：

```bash
curl http://127.0.0.1:8000/api/v1/runtime
```

## 快速启动

默认配置使用 Mock Mode，不需要 RapidAPI、OpenAI 或 DeepSeek 密钥。

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

启动 API 服务：

```bash
uvicorn main:app --reload
```

访问前端工作台：

```text
http://127.0.0.1:8000/
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## 配置说明

所有运行配置均从 `.env` 读取。建议从 `.env.example` 复制后按需修改。

### Mock Mode

```env
USE_MOCK=True
LLM_PROVIDER=mock
INFLUENCER_PROVIDER=rapidapi
```

### RapidAPI Mode

```env
USE_MOCK=False
INFLUENCER_PROVIDER=rapidapi
RAPID_API_KEY=your_rapidapi_key_here
RAPID_API_HOST=influencer-data1.p.rapidapi.com
```

当前 RapidAPI Provider 面向 YouTube 红人检索：

| 项目 | 值 |
| --- | --- |
| Endpoint | `GET /api/v0/analytics/creators/find` |
| Parameters | `channelType=youtube`, `keywords=...` |
| Headers | `X-Rapidapi-Key`, `X-Rapidapi-Host` |
| Fallback | 超时、限流、异常响应或空结果时降级到 Mock 数据 |

### LLM Mode

使用 DeepSeek：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

使用 OpenAI-compatible 接口：

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
```

### Async Mode

异步 Campaign 匹配依赖 Redis 与 Celery Worker。

```bash
celery -A tasks.celery_app.celery_app worker --loglevel=info
```

Redis 地址通过 `.env` 配置：

```env
REDIS_URL=redis://localhost:6379/0
```

## 评分体系

系统使用 100 分制评分模型，确保推荐结果具备可解释性和可审计性。

| 评分维度 | 分值 | 说明 |
| --- | ---: | --- |
| Category Match | 30 | 产品品类与红人内容品类的匹配程度 |
| Keyword Relevance | 25 | 产品描述与频道名、简介、内容关键词的相关性 |
| Target Market Match | 20 | 目标国家或地区与红人受众市场的匹配程度 |
| Follower Fit | 15 | 红人粉丝量与 Campaign 目标区间的匹配程度 |
| Content Activity | 10 | 基于作品数量和观看量的内容活跃度信号 |

接口返回 Top 10 推荐排名。仅 Top 5 会生成完整推荐理由与中英双语邀约信。真实数据源字段不完整时，系统只基于可用字段评分，不补造互动率、真实性等不可得指标。

## API 概览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/health` | 健康检查与运行状态摘要 |
| `GET` | `/api/v1/runtime` | 当前 Provider、RAG、LLM、Redis 和结果配置 |
| `POST` | `/api/v1/campaign/match` | 同步 Campaign 匹配 |
| `POST` | `/api/v1/campaign/match/async` | 提交异步 Campaign 匹配任务 |
| `GET` | `/api/v1/jobs/{task_id}` | 查询持久化任务状态 |
| `GET` | `/api/v1/campaigns` | 查询 Campaign 历史记录 |
| `GET` | `/api/v1/campaigns/{campaign_id}` | 查询 Campaign 详情与推荐结果 |
| `WS` | `/api/v1/ws/progress/{task_id}` | 订阅异步任务进度 |
| `POST` | `/api/v1/demo/match` | 自然语言 RAG 匹配兼容接口 |
| `POST` | `/api/v1/match` | 旧版 RAG 异步任务接口 |

## 目录结构

```text
ai-influencer-rag/
├── api/
│   └── endpoints.py                    # FastAPI 路由与 WebSocket 接口
├── alembic/
│   ├── env.py                          # Alembic 迁移环境
│   └── versions/                       # 数据库迁移脚本
├── config/
│   └── settings.py                     # 环境变量驱动的应用配置
├── core/
│   ├── campaign_matcher.py             # Campaign 匹配编排
│   ├── campaign_semantic.py            # Campaign 语义评分辅助逻辑
│   ├── llm_client.py                   # DeepSeek/OpenAI/Mock LLM 网关
│   ├── mock_data.py                    # 本地 Fixture 数据加载
│   ├── outreach_generator.py           # 中英双语邀约信生成
│   ├── progress.py                     # 进度回调基础设施
│   ├── rag_engine.py                   # LlamaIndex/BGE RAG 引擎
│   ├── recommendation_generator.py     # 推荐理由生成
│   ├── runtime.py                      # 运行模式判定
│   ├── schemas.py                      # Pydantic 数据模型
│   ├── scoring_engine.py               # 100 分制评分引擎
│   ├── translator.py                   # Campaign 翻译工具
│   └── providers/
│       ├── base.py                     # Provider 接口
│       ├── context.py                  # Provider 元数据上下文
│       ├── mock_provider.py            # 本地 Mock 红人数据源
│       ├── rapidapi_provider.py        # RapidAPI YouTube 数据源
│       └── reserved.py                 # 第三方商业 Provider 预留
├── data/
│   └── mock_influencers.json           # 演示红人数据
├── database/
│   └── session.py                      # SQLAlchemy Engine/Session
├── frontend/
│   ├── index.html                      # Campaign 工作台
│   ├── app.js                          # 前端交互逻辑
│   └── styles.css                      # UI 样式
├── models/
│   └── persistence.py                  # SQLAlchemy 持久化模型
├── repositories/
│   ├── campaign_repository.py          # Campaign 数据访问
│   ├── job_repository.py               # 异步任务数据访问
│   └── recommendation_repository.py    # 推荐结果数据访问
├── tasks/
│   ├── celery_app.py                   # Celery 应用实例
│   ├── campaign_pipeline.py            # Campaign 异步流水线
│   └── pipeline.py                     # 旧版 RAG 异步流水线
├── tests/                              # 单元测试与集成测试
├── .env.example                        # 环境变量模板
├── alembic.ini                         # Alembic 配置
├── main.py                             # FastAPI 应用入口
└── requirements.txt                    # Python 依赖
```

## 高级扩展：自定义数据源（Provider Extension）

Provider 层用于隔离外部数据源与核心匹配逻辑。新增商业红人平台时，只需实现新的 Provider，并将外部 API 响应映射为统一的 `Influencer` 模型；`CampaignMatcher`、`ScoringEngine` 与 `RecommendationGenerator` 无需感知数据来源变化。

### Provider Contract

自定义 Provider 需要实现统一搜索接口：

```python
search(campaign: CampaignRequest) -> List[Influencer]
```

Provider 负责完成认证、请求、分页、异常处理、字段标准化和必要的降级策略，向核心匹配链路返回结构化红人列表。

### 接入步骤

1. 在 `core/providers/` 下新增 Provider 文件，例如 `modash_provider.py`。
2. 实现 `search(campaign)`，并将第三方平台响应映射为内部 `Influencer` 模型。
3. 在 `ProviderName` 与 `get_influencer_provider` 中注册新 Provider。
4. 在 `config/settings.py` 与 `.env.example` 中补充平台配置项。
5. 使用 Mock API 响应补充确定性的单元测试。

### 示例：接入第三方商业平台（如 Modash）

对于 Modash 一类商业平台，Provider 通常需要完成以下字段映射：

| 第三方字段 | 内部用途 |
| --- | --- |
| `id` | `influencer_id` |
| `username` | 展示名称与推荐结果输出 |
| `followers` | Follower Fit 评分 |
| `country` | Target Market Match 评分 |
| `categories` | Category Match 与 Keyword Relevance 评分 |
| `engagement_rate` | 可选扩展评分信号 |

示例配置：

```env
INFLUENCER_PROVIDER=modash
MODASH_API_KEY=your_modash_api_key_here
```

这种扩展方式可以让 Provider 独立演进认证、分页、限流、字段归一化和降级策略，同时保持核心评分与推荐链路稳定。

## 测试

默认测试应运行在 Mock Mode，不依赖真实外部 API。

```bash
$env:USE_MOCK="True"
$env:LLM_PROVIDER="mock"
$env:RUN_LIVE_RAPIDAPI="0"
python -m unittest discover -s tests -v
```

真实 RapidAPI 联调需要显式开启：

```bash
$env:RUN_LIVE_RAPIDAPI="1"
python -m unittest tests.test_live_rapidapi -v
```

GitHub Actions 默认执行 Mock Mode 测试套件，不需要配置外部服务密钥。

## 安全与最佳实践（Security & Best Practices）

- 服务密钥应存放在本地 `.env` 文件或部署平台提供的 Secret 管理系统中。
- 仓库只提交 `.env.example`，实际 `.env` 文件通过 `.gitignore` 排除。
- 本地 SQLite 数据库、向量库、模型缓存、虚拟环境和 IDE 元数据不进入版本控制。
- CI 与公开演示环境优先使用 Mock Mode，避免自动化流程依赖第三方服务状态。
- 外部 API 的异常、限流和字段缺失应在 Provider 层完成归一化处理，避免泄漏到匹配编排与评分逻辑中。

## License

当前项目尚未选择开源许可证。正式公开为开源项目前，建议补充 `LICENSE` 文件。
