# Checkpoint

## Codex Save - 2026-05-11 PRD Refinement

- Saved DeepResearch Step1-Step6 PRD refinement session.
- Expanded Step1-Step4 `调用链与方案` sections into step-by-step explanations with subheadings, current behavior, goal, role, and current limitations.
- Expanded Step5 `12.3.2 调用链与方案` using the same format, clarifying writing entry, section traversal, evidence collection, data/chart collection, LLM section writing, draft persistence, report synthesis, and fallback report behavior.
- Expanded Step6 `12.3.2 调用链与方案` using the same format, clarifying review entry, phase gate, review content selection, evidence summary, LLM review, issue normalization, quality state calculation, and routing decision.
- Added Step5 professionalization guidance: evidence-bound writing, Evidence Pack, Claim-Citation ledger, numeric/chart locking, writing/composition split, and revision audit trail.
- Added Step6 professionalization guidance: LLM evaluation instability, routing error risks, deterministic checks, claim/evidence review, multi-signal routing, issue lifecycle, and quality gate roadmap.
- Verified `docs/research/index.md` still registers Step1-Step6 and `canonical-examples.md`.
- Verification status: documentation-level checks only; no backend/frontend tests were run.
- Remaining risk: unrelated existing modifications in `docs/design-docs/deepresearch-eval-platform-design.md` and `docs/design-docs/index.md` remain in the worktree and are not part of this research PRD refinement.

## Codex Save - 2026-05-11

- Saved DeepResearch six-step research PRD documentation session before cloud push.
- Added research-stage PRDs under `docs/research/` for Step 1 through Step 6: ChiefArchitect planning, DeepScout research, DataAnalyst analyze, CodeWizard analyze, LeadWriter write, and CriticMaster review.
- Added concrete representative cases for Step 1 through Step 6, including inputs, tool/agent call chains, state outputs, and event flow expectations; added `docs/research/canonical-examples.md` for cross-step examples.
- Updated Step 3 and Step 4 documentation to state current prototype limitations objectively: fact/data ordering limits, LLM-generated knowledge graph/chart/code risks, context-scaling concerns, and the recommended deterministic production architecture.
- Updated Step 4 with a dedicated "current implementation limits and professionalization recommendations" section covering cumulative `ResearchState` inputs, prompt context growth, LLM-generated code, chart selection rules, and data consistency checks.
- Updated `docs/research/index.md` to register the new research PRDs and canonical examples.
- Verification: checked `docs/research/` file list, confirmed index entries for Step 1-6 and `canonical-examples.md`, confirmed Step 4 sections 15.1-15.5 exist. No backend/frontend tests were run because this save only changes documentation.
- Remaining risk: existing unrelated modifications in `docs/design-docs/deepresearch-eval-platform-design.md` and `docs/design-docs/index.md` are still present in the worktree and were intentionally left out of this save.

## Codex Save - 2026-05-08

- Saved DeepResearch V2 runtime repair session before cloud push.
- Completed fixes: demo runner loads `backend/.env`, returns real exit codes, uses ASCII-safe trace status labels, rejects empty/zero-score E2E results, and supports `DR_V2_DEMO_TIMEOUT_SECONDS`.
- Completed fixes: DashScope-compatible max token clamp, bounded DeepScout search budget, LLM output normalization, portable CodeWizard debug dirs, syntax-failure short-circuit before sandbox execution, and JSONB-safe checkpoint serialization without runtime queues.
- Added regression coverage in `tests/test_deep_research_v2_runtime.py` for env loading, exit codes, token clamp, DeepScout budget/normalization, CodeWizard cleanup/invalid-code handling, checkpoint serialization, E2E success criteria, and timeout guard.
- Docker Desktop/compose was recovered and verified: postgres, redis, milvus, etcd, minio, elasticsearch healthy; Postgres `select 1`, Milvus connect, and checkpoint DB smoke passed.
- Verification: `backend\.venv\Scripts\python.exe -m unittest tests.test_deep_research_v2_runtime -v` -> 17 tests OK; `backend\.venv\Scripts\python.exe -m py_compile ...` -> OK; 30s timeout guard trace exited 1 as expected.
- Ignored local generated artifacts: root chart PNGs and `tests/traces/`. Remaining risk: full live E2E still depends on slow/unstable external LLM calls; next work should add graph-level Agent failure propagation and a smaller agents-only/e2e-only demo mode.

> 最后更新：2026-05-07

## 项目信息

- **项目名称**：industry-information-assistant
- **项目类型**：Full-Stack (Python backend + React frontend)
- **当前版本**：0.1.0
- **主分支**：main

---

## 全局状态

### 进度总览

| 模块 | 状态 | 进度 | 负责人 | 分支 | 最后更新 |
|------|------|------|--------|------|----------|
| backend | 未开始 | 0% | Unassigned | main | 2026-04-25 |
| frontend | 未开始 | 0% | Unassigned | main | 2026-04-25 |
| search | 未开始 | 0% | Unassigned | main | 2026-04-25 |
| knowledge-graph | 未开始 | 0% | Unassigned | main | 2026-04-25 |
| visualization | 未开始 | 0% | Unassigned | main | 2026-04-25 |
| 缺陷修复（伞行） | 🔄 in-progress | - | - | - | 2026-04-25 |
| 技术债务（伞行） | 🔄 in-progress | - | - | - | 2026-04-25 |
| 文档维护（伞行） | 🔄 in-progress | - | - | - | 2026-04-25 |

### 全局待办

- ✅ ~~环境就绪：Docker compose 6 服务全部 healthy（postgres/redis/milvus/etcd/minio/elasticsearch）~~
- ✅ ~~后端启动：uv venv + requirements.txt 装完，FastAPI on :8000，/hello 200~~
- ✅ ~~前端启动：npm install（项目级 .npmrc 绕开本地代理）+ Vite dev on :5183~~
- ✅ ~~盘点现有 11 router + 22 service 的实际能力 → 决定保留引擎本体，做业务定位重塑 + UI 升级~~
- ✅ ~~产出 v2 spec（rubric-based 单产出，3 轮 review approved）：`docs/product-specs/v2-advertiser-signals-spec.md`~~
- 进入 writing-plans：基于 v2 spec 出 Master Plan + Hard Gate 审批
- 实施改造：按 Master Plan 顺序落地（scoring_rubric.yaml / scoring_service.py / 4 类目重命名 / chat-trace U2 重建）
- 实施完后同步更新 `interview-prep.md` 的 talk track + 跑一份真实评分 demo

### 依赖关系

- search 依赖 backend 的数据层和向量检索接入（Milvus）
- knowledge-graph 依赖 backend（图谱存取）与 search（实体抽取）
- visualization 依赖 frontend 与 knowledge-graph 输出
- 所有模块依赖 docker-compose.yml 的基础服务正常运行

---

## backend模块

**负责**：Unassigned
**状态**：未开始 (0%)
**测试状态**：⚠️ 不涉及（本次仅环境配置）
**分支**：main
**最后更新**：2026-04-25

### 最近完成
- [2026-04-25] 创建 `backend/.env`，填入 `DASHSCOPE_API_KEY` 与 `BOCHA_API_KEY`
- [2026-04-25] 路径决策：放弃 CODEX 中转站，全链路使用 DashScope（兼容 embedding/rerank，零代码改动）
- 项目初始化（Claude Code 配置、AGENTS.md/CLAUDE.md）
- 已存在 backend/app/ 代码骨架（待盘点）

### 进行中
- 等待 Docker Desktop 安装完成后启动后端
- 盘点现有代码结构与功能

### 下一步
1. 读取 backend/requirements.txt 明确依赖版本
2. 梳理 backend/app 现有模块结构
3. 撰写 backend 模块 PRD 与 I/O spec

### 依赖
- docker-compose.yml 基础服务运行正常（Postgres / Redis / Milvus / ES / MinIO）

### 相关文档
- PRD: docs/product-specs/backend-requirements.md (待创建)
- 架构: docs/design-docs/backend-architecture.md (待创建)

---

## frontend模块

**负责**：Unassigned
**状态**：未开始 (0%)
**测试状态**：⚠️ 未验证（最后运行：-）
**分支**：main
**最后更新**：2026-04-25

### 最近完成
- 项目初始化
- 已存在 frontend/src/ React + Vite + TS 骨架（待盘点）

### 进行中
- 盘点现有页面与组件

### 下一步
1. 梳理 frontend/src 目录结构
2. 确认 mock/ 目录与后端联调方案
3. 撰写 frontend 模块 PRD 与 UI I/O spec

### 依赖
- backend 提供 API 契约

### 相关文档
- PRD: docs/product-specs/frontend-requirements.md (待创建)
- 架构: docs/design-docs/frontend-architecture.md (待创建)

---

## search模块

**负责**：Unassigned
**状态**：未开始 (0%)
**测试状态**：⚠️ 未验证（最后运行：-）
**分支**：main
**最后更新**：2026-04-25

### 最近完成
- 项目初始化

### 进行中
- 待开始

### 下一步
1. 定义搜索需求（关键词、语义、混合检索）
2. 设计 Milvus 向量库与 Elasticsearch 倒排索引的协作策略
3. 产出 search 模块 I/O spec

### 依赖
- backend 数据层
- Milvus / Elasticsearch 就绪

### 相关文档
- PRD: docs/product-specs/search-requirements.md (待创建)
- 架构: docs/design-docs/search-architecture.md (待创建)

---

## knowledge-graph模块

**负责**：Unassigned
**状态**：未开始 (0%)
**测试状态**：⚠️ 未验证（最后运行：-）
**分支**：main
**最后更新**：2026-04-25

### 最近完成
- 项目初始化

### 进行中
- 待开始

### 下一步
1. 定义图谱 Schema（实体、关系、属性）
2. 选型存储（PostgreSQL 图扩展 vs 专用图库）
3. 产出 knowledge-graph 模块 I/O spec

### 依赖
- search 的实体抽取输出
- backend 数据层

### 相关文档
- PRD: docs/product-specs/knowledge-graph-requirements.md (待创建)
- 架构: docs/design-docs/knowledge-graph-architecture.md (待创建)

---

## visualization模块

**负责**：Unassigned
**状态**：未开始 (0%)
**测试状态**：⚠️ 未验证（最后运行：-）
**分支**：main
**最后更新**：2026-04-25

### 最近完成
- 项目初始化

### 进行中
- 待开始

### 下一步
1. 选型可视化库（ECharts / D3 / 专用图谱库）
2. 定义可视化视图（图谱、时间线、主题图）
3. 产出 visualization 模块 UI I/O spec

### 依赖
- frontend 框架就绪
- knowledge-graph 图谱数据输出

### 相关文档
- PRD: docs/product-specs/visualization-requirements.md (待创建)
- 架构: docs/design-docs/visualization-architecture.md (待创建)

---

## 伞行（长期归集）

### 缺陷修复
**状态**：🔄 in-progress（持续）
**详情**：
- _暂无记录_

### 技术债务
**状态**：🔄 in-progress（持续）
**详情**：
- _暂无记录_

### 文档维护
**状态**：🔄 in-progress（持续）
**详情**：
- [2026-04-25] /load 演练 + 深度盘点项目结构（11 个 FastAPI 路由 / 6 Agent LangGraph 编排 / 5 Docker 服务依赖）
- [2026-04-25] 初始化 Claude Code 项目配置：AGENTS.md / CLAUDE.md / checkpoint.md / docs 骨架
- [2026-04-25] 产出 `docs/design-docs/architecture.md`：系统架构文档 v1.0（四层模型、LangGraph 编排、存储拓扑、数据流、已知风险）
- [2026-04-25] 全栈环境拉通：Docker 6 服务 healthy / backend uv venv + Python 3.12.7 / frontend npm + Vite 5183，新增 `frontend/.npmrc`（绕本地代理）+ `.gitignore` 增加 `.npmrc` 规则
- [2026-04-26] 面试 P0 准备完成：D1 补丁（点行业卡片自动开深度搜索）+ `tests/research_demo.py` 真跑「金融科技」query（24min/136 事件/200 源/6 章大纲）+ `docs/exec-plans/active/interview-prep.md`（速查卡：60s pitch + 3 张 Mermaid 架构图 + 6 类追问对答 + 实测指标）
- [2026-04-27] 完成 brainstorming + 产出 v2 spec（rubric-based 单产出版）：`docs/product-specs/v2-advertiser-signals-spec.md` 三轮 spec-document-reviewer subagent 审 approved。核心定位：金融广告主多智能体 deep research，报告末尾追加 5 维度 rubric 评分（业务扩张度 25% / 监管态度 25% / 品牌活跃度 20% / 竞争地位 15% / 创新与数字化 15%）。同时产出 `docs/exec-plans/active/ui-mockups.html`（U1/U2/U3 三种风格对比，已选 U2）+ 项目 memory（feedback_proxy_isolation / feedback_no_time_estimates）

---

## 已知问题

- 根目录存在 `READMED.md` 拼写错误（预期为 `README.md`），待处理
- backend 招标采集 API（bid.81api.com）返回 401，因为 `BID_APP_KEY/BID_APP_CODE` 仍是 .env 中的占位值，需用户补真实 Key
- backend 控制台日志中文显示乱码（Windows GBK 编码问题），不影响功能，后续可加 `PYTHONIOENCODING=utf-8` 修复
- frontend `.npmrc` 中空 `proxy=` 触发 npm warn，但不影响安装结果（已验证）

## 技术决策记录

- 使用 uv 作为 Python 环境/包管理工具
- Python src 布局沿用既有 backend/app 结构，不另建 src/

---

## 更新指南

### 增量更新规则

1. **只修改自己负责的模块章节**
2. **不得删除或修改其他模块的内容**
3. **保持章节结构完整**
4. **使用 /save 命令自动更新**

### 「最近完成」长度限制

- **最多 10 条**，超过时将最旧记录移动到 `docs/archive/checkpoint-history.md`
- 单次 `/save` 如果新增条目使总数超过 10，必须先归档后再追加

---

## Codex 保存记录

### 2026-05-07

- 本次 `/save` 检查结果：工作区无未提交代码改动，`main` 与 `origin/main` 原本已对齐。
- 已确认当前项目定位：应用层多智能体 Deep Research 系统，不是 Agentic Continual Pre-training 训练项目。
- 已整理简历项目表述建议：强调 FastAPI + React + LangGraph 风格状态机、多 Agent 研究流水线、SSE 流式输出、checkpoint 续跑、多源检索、CodeWizard 分析执行、rubric-based 金融广告主基本面评分设计。
- 当前 active 文档：`docs/product-specs/v2-advertiser-signals-spec.md`、`docs/exec-plans/active/interview-prep.md`、`docs/exec-plans/active/ui-mockups.html`。
- 推送策略：本次仅新增 checkpoint 保存记录；代码与产品文档主体无额外变更。
