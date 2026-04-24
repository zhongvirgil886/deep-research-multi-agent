# 系统架构文档

> 最后更新：2026-04-25
> 版本：1.0（首次整理）
> 适用：industry-information-assistant（行业信息助手 · Deep Research S4）

本文档是项目的技术北极星，解读系统架构、核心机制、数据流、部署拓扑，以及当前已知风险和演进方向。前端章节仅覆盖接入层，未对组件细节展开。

---

## 1. 架构总览

### 1.1 产品定位

一款面向行业研究员的 **AI 深度研究助手**：输入一个行业/公司查询，系统通过多智能体协作输出一份结构化研究报告（含大纲、关键事实、统计图表、知识图谱、对抗式审核后的修订版）。相比普通 RAG 问答，核心差异在于 —— **链路更长**（规划 → 侦察 → 分析 → 写作 → 审核），**产物更重**（完整报告 + 图表 + 可视化）。

### 1.2 四层分层模型

```
┌───────────────────────────────────────────────────────────────┐
│  Presentation 层 · React + Vite + Valtio (端口 5183)          │
│  路由 / 鉴权守卫 / SSE 消费 / 图表渲染                         │
└──────────────────────────────┬────────────────────────────────┘
                   HTTP + text/event-stream
┌──────────────────────────────▼────────────────────────────────┐
│  API 层 · FastAPI (端口 8000)                                 │
│  11 个路由模块 / OAuth2+JWT / CORS / Lifespan 调度器          │
└──────────────────────────────┬────────────────────────────────┘
                              │
┌──────────────────────────────▼────────────────────────────────┐
│  Orchestration 层 · LangGraph 多智能体编排                     │
│  ChiefArchitect → DeepScout → DataAnalyst/CodeWizard →        │
│  LeadWriter ⇄ CriticMaster（对抗式修订循环，最多 3 次）        │
└──────────────────────────────┬────────────────────────────────┘
                              │
┌──────────────────────────────▼────────────────────────────────┐
│  Storage 层 · Docker Compose 编排的多种存储                    │
│  PostgreSQL · Redis · Milvus(+etcd+MinIO) · Elasticsearch     │
└───────────────────────────────────────────────────────────────┘
```

### 1.3 代码组织拓扑

```
project/
├── backend/                        Python 3.10+ 后端
│   ├── app/
│   │   ├── app_main.py             FastAPI 入口（lifespan + 11 router）
│   │   ├── router/                 HTTP 路由层（11 个模块）
│   │   ├── service/
│   │   │   ├── deep_research_v2/   多智能体引擎（核心）
│   │   │   │   ├── graph.py        LangGraph 状态机
│   │   │   │   ├── state.py        ResearchState 定义
│   │   │   │   └── agents/         6 个 agent 实现
│   │   │   ├── text2sql_service.py 自然语言 → SQL（带安全白名单）
│   │   │   ├── milvus_service.py   向量检索
│   │   │   ├── checkpoint_service.py 断点续传
│   │   │   └── ...（共 20+ 服务）
│   │   ├── core/                   基础设施（db/redis/security）
│   │   ├── config/                 LLM / 行业 / 股票映射配置
│   │   ├── models/                 SQLAlchemy ORM
│   │   └── schemas/                Pydantic DTO
│   └── requirements.txt
├── frontend/                       React 19 + Vite + Valtio
│   ├── src/
│   │   ├── api/request/            Axios 拦截器链
│   │   ├── pages/chat/             深度研究主界面 + SSE 消费
│   │   ├── pages/{knowledge,memory,database,news,bidding}/
│   │   ├── store/                  Valtio + 自定义持久化
│   │   └── router/                 路由 + AuthGuard
│   └── vite.config.ts
├── docker-compose.yml              基础服务编排
├── docker/init-db/                 Postgres 初始化脚本
└── start-services.sh               start/stop/status/logs/clean
```

---

## 2. API 层（FastAPI）

### 2.1 应用初始化

入口文件 `backend/app/app_main.py:63-89`：
- FastAPI 标题"行业信息助手 API"，版本 2.0.0
- CORS 全开（`allow_origins=["*"]`，生产环境需收缩 —— 见 §9）
- `Base.metadata.create_all()` 启动时建表（开发便利，生产应改用 Alembic）
- `lifespan` 启动时调用 `init_scheduler_and_check_data()` —— 定时任务调度器（APScheduler，负责新闻/招投标采集等周期作业）

### 2.2 路由模块清单

| 路由前缀 | 文件 | 职责 | 是否 SSE |
|---------|------|------|---------|
| `/auth` | `auth_router.py` | OAuth2 + JWT 登录、注册、token 刷新 | 否 |
| `/sessions` | `session_router.py` | 会话 CRUD、消息列表 | 否 |
| `/chat` | `chat_router.py` | 对话补全（v1/v3），知识库 + Web 检索增强 | **是** |
| `/research` | `research_router.py` | 深度研究（v2），取消、检查点 | **是** |
| `/knowledge` | `knowledge_router.py` | 知识库 + 文档管理 | 否 |
| `/attachments` | `attachment_router.py` | 附件上传、查询 | 否 |
| `/memory` | `memory_router.py` | 长短期记忆 | 否 |
| `/database` | `database_router.py` | Text2SQL、Schema 探索 | 否 |
| `/document` | `document_router.py` | DocMind 文档解析 | 否 |
| `/search` | `search_router.py` | Web / Policy 搜索聚合 | 否 |
| `/news` | `news_router.py` | 行业新闻聚合 | 否 |

### 2.3 鉴权方案

- **协议**：OAuth2 Password Flow + JWT
- **Token 端点**：`POST /auth/token`（用户名/邮箱 + 密码）
- **保护端点**：依赖 `get_current_user()`，自动解析 `Authorization: Bearer <JWT>`
- **密码**：bcrypt 哈希（`core/security.py`）
- **配置**：`JWT_SECRET_KEY` / `JWT_ALGORITHM` / `JWT_EXPIRE_MINUTES` 经环境变量读取

---

## 3. 多智能体编排引擎（核心）

这是本项目技术上最独特的部分。编排不是 Agent Framework 生搬硬套，而是用 **LangGraph 状态机** 显式建模研究流程。

### 3.1 状态机定义

`service/deep_research_v2/graph.py:200-235`

```
      ┌──────┐
      │ PLAN │ ChiefArchitect：生成大纲、研究问题、假设、知识图谱骨架
      └──┬───┘
         ▼
    ┌────────┐
    │RESEARCH│ DeepScout：并行深度搜索，产出结构化事实（带可信度评级）
    └──┬─────┘
       ▼
    ┌────────┐
    │ANALYZE │ DataAnalyst + CodeWizard：统计、预测、沙箱执行绘图代码
    └──┬─────┘
       ▼
    ┌────────┐
    │ WRITE  │ LeadWriter：基于 facts 和 charts 撰写 draft_sections
    └──┬─────┘
       ▼
    ┌────────┐              ┌─────────┐
    │ REVIEW │──────────────▶│ COMPLETE│ CriticMaster 打分 ≥ 6.0 → 完成
    └──┬─────┘   _should_   └─────────┘
       │         revise()
       ▼（质量不达标 OR 有 critical/major issue）
    ┌────────┐
    │ REVISE │ LeadWriter 根据 critic_feedback 修订，回到 REVIEW
    └──┬─────┘
       │  最多循环 max_iterations 次（默认 3）
       └──────────▶ REVIEW
```

### 3.2 状态结构：`ResearchState`

`service/deep_research_v2/state.py:108-205` 定义的 TypedDict 涵盖三类数据：

| 维度 | 字段 | 说明 |
|------|------|------|
| **规划** | `outline`, `research_questions`, `hypotheses`, `mind_map`, `knowledge_graph` | 架构师产出 |
| **知识** | `facts[]`, `data_points[]`, `raw_sources[]`, `references[]` | 侦察员/分析师累积 |
| **产出** | `draft_sections`, `final_report`, `charts[]`, `critic_feedback[]`, `quality_score` | 写手/评论家产出 |
| **控制** | `phase`, `iterations`, `_message_queue`, `session_id` | 运行时 |

关键子结构：
- `Fact`：`{content, source_url, credibility_score, source_type}`，`source_type ∈ {official, academic, news, report, self_media}`，用于信源权重与引用追溯
- `CriticFeedback`：`{issue_type, severity, section_id, suggestion}`，`issue_type ∈ {missing_source, logic_error, bias, hallucination, outdated, incomplete}`
- `Chart`：`{python_code, output_base64, echarts_config}`，**双通道**保证降级

### 3.3 六大 Agent 模型分配

`config/llm_config.py:106-120` 对 Agent 做差异化模型分配：

| Agent | 模型 | 温度 | 职责 |
|-------|------|------|------|
| ChiefArchitect | `deepseek-v3.2` | 0.7 | 规划需要长程推理，用强模型 |
| DeepScout | `qwen-plus` | 0.3 | 多轮并发搜索，成本敏感，用快模型 |
| DataAnalyst | `deepseek-v3.2` | 0.5 | 数据归纳 |
| CodeWizard | `deepseek-v3.2` | 0.2 | 代码生成需低温度 |
| LeadWriter | `deepseek-v3.2` | 0.7 | 写作 |
| CriticMaster | `deepseek-v3.2` | 0.3 | 审核要客观稳定 |

统一走阿里云百炼 OpenAI 兼容接口（`base_url: https://dashscope.aliyuncs.com/compatible-mode/v1`），备选 OpenRouter 做容错。

### 3.4 Agent 基类与 SSE 推送

`service/deep_research_v2/agents/base.py:24-110` 提供通用能力：
- **LLM 调用**：OpenAI 兼容 SDK，支持 JSON 强制模式
- **JSON 解析容错**：三重降级（直接解析 → 正则修复转义 → `ast.literal_eval`）
- **执行日志**：记录 agent_name、action、duration、tokens，写入 state["logs"]
- **实时推送**：`add_message()` 直接 put 到 `state["_message_queue"]` —— 这是 SSE 能流式吐事件的关键（见 §5.1）

### 3.5 对抗式质检循环

CriticMaster 不是简单的相似度评分，而是结构化输出 issue 列表：

```python
# state.py
IssueType = Literal["missing_source", "logic_error", "bias",
                    "hallucination", "outdated", "incomplete"]
Severity  = Literal["critical", "major", "minor"]
```

`_should_revise()` 的决策规则：存在 `critical` 或多个 `major` → revise；否则 complete。修订次数封顶 `max_iterations=3`（`config/llm_config.py:90`），避免无限循环。

---

## 4. 存储层

### 4.1 PostgreSQL — 单一持久层

- **镜像**：`postgres:15-alpine`，容器名 `industry_postgres`，暴露 `5432`
- **连接池**：SQLAlchemy 引擎，`pool_pre_ping=True`（`core/database.py:17-20`）
- **核心表（模型注册在 `models/`）**：
  - 账户：`users`
  - 会话：`chat_sessions`, `chat_messages`, `chat_attachments`
  - 研究：`research_checkpoints`（含 `state_json` + `ui_state_json` + `final_report`）
  - 知识：`knowledge_bases`, `documents`
  - 业务数据：`industry_stats`, `company_data`, `policy_data`, `industry_news`, `bidding_info`
  - 记忆：`long_term_memory`
  - 调度：`news_collection_tasks`
- **初始化**：`docker/init-db/` 下的 SQL 脚本在容器首次启动时执行

### 4.2 Redis — 缓存与协调

- **镜像**：`redis:7-alpine`，暴露 `6379`，`--appendonly yes`（AOF 持久化）
- **用途分类**（`core/redis_client.py:29-108`）：
  - 会话缓存：TTL 24h
  - 通用缓存：TTL 1h（搜索结果、LLM 响应）
  - 短期记忆列表：最多 100 条
  - **取消标志**：`research:cancel:{session_id}` —— 前端调 `/research/cancel/{sid}` 写入，graph 每个节点执行前检查（`is_research_cancelled`，见 `graph.py:20-29`）

### 4.3 Milvus + etcd + MinIO — 向量库栈

Milvus Standalone 模式：
- **Milvus**：`milvusdb/milvus:v2.3.3`，`19530`（gRPC）/`9091`（HTTP 健康检查）
- **etcd**：存储 Milvus 集合元数据 + 配置
- **MinIO**：存储向量索引数据块（S3 兼容）

集合定义（`service/milvus_service.py:56-82`）：
```
字段：id, doc_id, kb_id, filename, content, chunk_index, vector(FLOAT_VECTOR, dim=1024)
索引：IVF_FLAT，metric_type=COSINE
```

嵌入模型：阿里云 `text-embedding-v4`（`embedding_service.py`）

### 4.4 Elasticsearch — 全文检索（可选）

- **镜像**：`elasticsearch:8.11.3`，**暴露映射 1200:9200**（主机 1200 → 容器 9200）
- **模式**：`discovery.type=single-node`，`xpack.security.enabled=false`（开发便利，生产需开启）
- **用途**：全文倒排索引，与 Milvus 向量检索互补（待确认具体接入点）

---

## 5. 关键数据流

### 5.1 深度研究 SSE 流

```
[前端 chat page]                     [FastAPI]                   [LangGraph]
  ── POST /research/stream ─────────────▶
                                       ├ 创建 _message_queue
                                       ├ 启动 graph.ainvoke() (async task)
                                       │                             │
                                       │◀─ agent.add_message(ev) ────┤
  ◀── data: {event: agent_start,...} ──┤  （SSE yield）              │
                                       │                             │
                                       │◀─ agent.add_message(ev) ────┤
  ◀── data: {event: fact_found,...} ───┤                             │
                                       │                             │
                                       │                          REVIEW 通过
  ◀── data: {event: complete,...} ─────┤                             │

用户若点"停止"：
  ── POST /research/cancel/{sid} ──────▶ Redis SET research:cancel:sid=1
                                                                     │
                                       每个 agent 执行前 check  ◀────┤
                                       → 抛 Cancelled，graph 退出
```

关键点：
- **解耦**：Agent 只负责把事件丢进队列，不关心传输；路由层只负责从队列拉事件转 SSE
- **前端消费**：`frontend/src/api/session.ts` 用 `responseType: 'stream' + adapter: 'fetch'`，`ReadableStreamDefaultReader.read()` 循环读取；点停止调 `reader.cancel()` + 后端 cancel API

### 5.2 知识库向量检索流

```
用户问题 → EmbeddingService.generate_embedding(text-embedding-v4)
        → MilvusService.search(kb_id, top_k=5, metric=COSINE)
        → 取回 top_k 文本块 + 元数据
        → 注入 LLM prompt 上下文
        → 返回生成结果（附引用）
```

### 5.3 Text2SQL 流（带安全网）

`service/text2sql_service.py`：
1. **Schema 注入**：`DatabaseExplorer` 自动发现 `industry_stats`、`company_data`、`policy_data` 等表结构
2. **LLM 生成**：生成 SQL + 可视化提示（如"折线图适合"）
3. **安全过滤**：
   - 白名单 token：`SELECT / FROM / WHERE / JOIN / GROUP BY / ORDER BY / LIMIT`
   - 黑名单 token：`DROP / DELETE / UPDATE / INSERT / TRUNCATE / ALTER / EXEC`
   - 正则检测 SQL 注入模式
4. **执行**：SQLAlchemy 只读连接执行
5. **返回**：`{sql, explanation, rows, visualization_hint}`

### 5.4 检查点续传流

- **写入时机**：每个 agent 节点结束后，`CheckpointService.save_checkpoint(session_id, state)`
- **存储字段**（`research_checkpoints` 表）：
  - `state_json`：完整 ResearchState（恢复执行）
  - `ui_state_json`：前端所需裁剪（research_steps / charts / knowledge_graph）
  - `final_report`：最终报告文本
- **恢复**：`GET /research/checkpoint/{sid}` 前端拿 UI 态重渲；`graph.resume(session_id)` 后端从 state_json 续跑

---

## 6. 前端接入层（轻量）

### 6.1 技术栈

| 层 | 选型 |
|----|------|
| 框架 | React 19 + React Router v6 |
| 构建 | Vite v6.1（dev server 5183） |
| UI | Ant Design v5.24 |
| 图表 | ECharts v5.6 |
| 状态 | **Valtio v2.1.3** + 自定义 `valtio-persist.ts`（SingleFile/MultiFile 策略、版本迁移） |
| 请求 | Axios v1.7.9，拦截器链：`auth → service → loading → repeat → error-toast` |
| Mock | `vite-plugin-mock`（开发期，生产关闭） |

### 6.2 路由与守卫

`frontend/src/router/routes.tsx` 七个主路由：`/`, `/chat`, `/knowledge`, `/memory`, `/database`, `/news`, `/bidding`。所有非登录路由受 `AuthGuard` 保护，统一套 `BaseLayout`。

### 6.3 SSE 消费模式

`pages/chat/index.tsx` 主流程：
1. 调用 `session.ts` 的 `deepsearch()` / `chatWithAttachments()`，返回 `ReadableStream`
2. `for await (const chunk of reader)` 解析 `data: {...}\n\n` 事件
3. 根据事件类型分发到 `ResearchStep[]` / `SearchResult[]` / `Chart[]` / `KnowledgeGraph` 状态
4. 点击"停止"：`reader.cancel()` + `POST /research/cancel/{sessionId}`
5. 2000ms 轮询附件处理状态（非 SSE）

---

## 7. 关键机制深入

### 7.1 代码沙箱（CodeWizard）

`service/deep_research_v2/agents/wizard.py:38-80`：
- **生成侧约束**：禁止反斜杠续行，代码 ≤ 40 行
- **执行侧隔离**：`contextlib.redirect_stdout/stderr` 捕获输出，matplotlib `Agg` 后端渲染
- **产物**：PNG → base64 嵌入响应 + 执行日志

**当前限制**（需要注意）：`exec()` 执行在同一 Python 进程，**没有容器或 seccomp 级别的隔离**。低信任环境下有逃逸风险 —— 见 §9。

### 7.2 断点续传

研究流程可能持续几分钟到十几分钟，任何原因（超时、用户刷新、LLM 报错）中断后：
- UI 态：`ui_state_json` → 前端重建对话界面（步骤、搜索结果、图表已展示部分）
- 执行态：`state_json` → 后端 `graph.resume()` 从上次中断的节点继续

### 7.3 Text2SQL 安全白名单

详见 §5.3。**当前方案是 token 级过滤，不是 AST 解析**，面对 `SELECT ... UNION SELECT password FROM users` 这类变体仍有风险 —— 建议升级为 `sqlglot` AST 解析 + 只读账号双保险。

### 7.4 配置管理

- **按 Agent 差异化模型**：见 §3.3
- **行业预设**（`config/industry_config.py`）：智慧交通 / 金融科技 / 医疗健康 / 能源电力四个行业，各自关键词、新闻源、招投标标签
- **股票映射**（`stock_mapping.py`）：热门 A 股公司名 → 股票代码（带 sh/sz 前缀）

---

## 8. 部署与运维

### 8.1 端口与凭证速查表

| 服务 | 主机端口 | 容器端口 | 凭证 | 备注 |
|------|---------|---------|------|------|
| FastAPI | 8000 | — | JWT | `python app_main.py` 直接起，或 uvicorn |
| Vite Dev | 5183 | — | — | `VITE_API_PROXY=http://localhost:8000` |
| PostgreSQL | 5432 | 5432 | `postgres / postgres123` | 库 `industry_assistant` |
| Redis | 6379 | 6379 | 无密码 | AOF 持久化 |
| Milvus | 19530 / 9091 | 19530 / 9091 | — | Standalone 模式 |
| etcd | — | 2379 | — | 仅容器内 |
| MinIO | 9000 / 9001 | 9000 / 9001 | `minioadmin / minioadmin` | Console 在 9001 |
| Elasticsearch | **1200** | 9200 | 无密码（xpack off） | 注意主机端口非 9200 |

### 8.2 生命周期

`start-services.sh` 提供子命令：`start / stop / restart / status / logs / clean`。启动顺序隐式由 `depends_on` 保证（Milvus 等 etcd + minio）；健康检查最长 30s × 5 retries。

### 8.3 环境变量分类

`backend/.env.example` 共 22+ 变量，分 7 组：
- **LLM**（必填）：`DASHSCOPE_API_KEY`, `OPENAI_MODEL=qwen3-max`
- **搜索**（必填/可选）：`BOCHA_API_KEY`（必），`SERPER_API_KEY`（可），`JUHE_STOCK_API_KEY`（可）
- **招投标**（可选）：`BID_APP_KEY/SECRET/CODE`
- **数据库**：`POSTGRES_HOST/PORT/USER/PASSWORD/DB`
- **向量/缓存**：`MILVUS_HOST/PORT`, `REDIS_HOST/PORT`
- **存储**：`MINIO_ENDPOINT/ACCESS/SECRET`
- **认证**：`JWT_SECRET_KEY/ALGORITHM/EXPIRE_MINUTES`

---

## 9. 当前缺失与演进方向

这一节刻意写得直白，作为后续迭代的输入。

### 9.1 可观测性（优先级高）

| 维度 | 当前 | 建议 |
|------|------|------|
| 日志 | FastAPI 默认 logging（INFO 到 stderr） | 加 `RotatingFileHandler` 落盘；引入结构化日志（JSON） |
| Tracing | 无 | 接入 **Langfuse**（README 已提及，但未见配置） —— 跟踪每次研究的 6 个 agent span + token 消耗 |
| Metrics | 无 | Prometheus + Grafana；关注 agent 耗时、token、成功率、检查点 hit 率 |
| 错误追踪 | 无 | Sentry / 同类 |

### 9.2 安全性（优先级高）

- **CORS `*`**：生产必须收窄到实际前端域
- **ES `xpack.security.enabled=false`**：生产必须开启
- **代码沙箱逃逸**：CodeWizard 用 `exec()` 同进程执行 → 应改为子进程 + `resource` 限制 / Docker exec / gVisor / e2b
- **Text2SQL token 过滤**：应升级为 AST 解析 + 只读角色
- **密钥泄露风险**：`.env` 已被 .gitignore 过滤，但 `backend/.env.example` 应定期审查是否误塞真实 key
- **密码**：Postgres 默认 `postgres123` 写死在 `docker-compose.yml`，生产必须改

### 9.3 性能与弹性

- **单体部署**：FastAPI、调度器、Agent 编排都在一个进程 → 建议 Agent 编排拆 worker（Celery / Arq）
- **LLM 并发**：DeepScout 声称"并行"，需确认是否真的用 `asyncio.gather` —— 如果是串行就会成为瓶颈
- **Milvus Standalone**：不支持横向扩展，向量库过百万条时应迁 Milvus Cluster
- **Postgres `Base.metadata.create_all()`**：开发便利，生产应改 Alembic 迁移

### 9.4 架构债

- **路由分离不一致**：部分 router 用 `router.router`（`from router.auth_router import router as auth_router`），部分直接 `from router import chat_router`，接入方式应统一
- **import 容错**：`graph.py` 里 `try: from router.xxx except: from app.router.xxx except: 兼容直接运行` 的三重 try 说明模块路径规划有历史包袱，值得清理
- **chat_service v1/v2/v3 并存**：需要明确哪个是 SSoT，废弃旧版

### 9.5 功能演进候选

- **知识图谱交互**：当前前端只是渲染，可加"点击节点展开相关事实"
- **多语言研究**：Scout 只搜中文源，扩展英文 arxiv/news 能显著提升信源质量
- **Agent 记忆**：当前 `memory_service` 存在但未接入 Agent → 让 ChiefArchitect 能用用户历史研究作为风格参考

---

## 附录 A：关键文件索引

| 组件 | 文件 | 说明 |
|------|------|------|
| FastAPI 入口 | `backend/app/app_main.py` | 105 行，lifespan + 11 router |
| 研究路由 | `backend/app/router/research_router.py` | SSE 端点、取消、检查点 |
| 鉴权路由 | `backend/app/router/auth_router.py` | OAuth2 + JWT |
| LangGraph 编排 | `backend/app/service/deep_research_v2/graph.py` | 状态机定义 |
| 状态结构 | `backend/app/service/deep_research_v2/state.py` | TypedDict + 子结构 |
| Agent 基类 | `backend/app/service/deep_research_v2/agents/base.py` | LLM 调用 + 消息推送 |
| CodeWizard | `backend/app/service/deep_research_v2/agents/wizard.py` | 代码生成 + 沙箱 |
| 检查点服务 | `backend/app/service/checkpoint_service.py` | 断点续传 |
| Text2SQL | `backend/app/service/text2sql_service.py` | 自然语言 → SQL |
| Milvus | `backend/app/service/milvus_service.py` | 向量检索 |
| 数据库 | `backend/app/core/database.py` | SQLAlchemy 引擎 |
| Redis | `backend/app/core/redis_client.py` | 缓存 + 取消标志 |
| LLM 配置 | `backend/app/config/llm_config.py` | Agent 模型分配 |
| 行业配置 | `backend/app/config/industry_config.py` | 4 个行业预设 |
| 前端路由 | `frontend/src/router/routes.tsx` | 7 个主路由 |
| 前端 API | `frontend/src/api/session.ts` | SSE 消费 |
| Docker 编排 | `docker-compose.yml` | 6 个基础服务 |
| 启停脚本 | `start-services.sh` | start/stop/status/logs |

## 附录 B：术语表

| 术语 | 含义 |
|------|------|
| SSE | Server-Sent Events，单向 HTTP 流式推送 |
| LangGraph | LangChain 的状态机编排库，支持节点 + 条件边 |
| 对抗式质检 | CriticMaster 独立审 LeadWriter 产出，不达标打回修订 |
| 断点续传 | Agent 执行中断后，从上次检查点恢复 |
| 信源评级 | Fact.credibility_score，根据 source_type 权重计算 |
| 研究态 vs UI 态 | state_json 给后端续跑；ui_state_json 给前端重渲 |
