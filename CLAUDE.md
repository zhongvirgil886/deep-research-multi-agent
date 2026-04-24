# CLAUDE.md

@AGENTS.md

This file provides Claude Code / gstack specific rules. Shared project rules are in AGENTS.md.

## Project Overview

**Project Name**: industry-information-assistant
**Project Type**: Full-Stack (Python backend + React frontend)
**Description**: 基于 AI 的深度研究助手，支持智能搜索、知识图谱、数据可视化

## Repository Structure

```
project/
├── backend/                 # Python FastAPI backend
│   ├── app/                # Application code
│   ├── test/               # Backend tests
│   └── requirements.txt
├── frontend/               # React + Vite + TypeScript
│   ├── src/
│   ├── mock/
│   └── package.json
├── docker/                 # Docker configs
├── docker-compose.yml      # Services: Postgres / Redis / Milvus / ES / MinIO
├── data/                   # Sample / raw data (large files ignored)
├── docs/
│   ├── product-specs/
│   ├── exec-plans/{active,completed}/
│   ├── design-docs/
│   └── generated/
├── .claude/                # Claude Code config
├── checkpoint.md           # Module progress tracking
├── AGENTS.md               # Shared cross-tool contract
└── CLAUDE.md               # This file
```

## Key Technologies

- **Backend**: Python 3.10+, FastAPI (inferred), SQLAlchemy
- **Frontend**: React + Vite + TypeScript, ESLint
- **Storage**: PostgreSQL, Redis, Milvus (vector DB), Elasticsearch, MinIO
- **Package Management**: uv (Python), npm (Frontend)
- **Orchestration**: Docker Compose

## Claude-Specific Workflow

Uses superpowers (design/plan/execute) + gstack (review/QA/release) + custom commands (review/save).

本项目 Profile: **D (全栈)** — 同时有 UI 产品和后端服务

### Lightweight Track

| Scenario | Flow |
|----------|------|
| **Bug fix** | Reproduce → TDD (failing test → fix → pass) → /review → /ship |
| **Small feature** (< half day) | brainstorming → SDD → /review → /ship |
| **Refactor** | Define constraints → modify → /simplify → /review → /ship |
| **Docs only** | Edit → /document-release → /save |
| **UI polish** | /qa-design-review → /ship |

<ROUTER>
收到任何开发请求时，brainstorming 必须在前 3 个问题内完成路由探测，不得跳过：

1. 检查本项目是否有在执行中的 approved Master Plan
   - 无 → 判断规模: 半天内且不改公开接口 → 轻量通道; 否则 → 完整开发
   - 有 → 继续步骤 2

2. 判断请求与 Master Plan 的关系
   - 已在 Plan 某个 Task 中 → 正常执行该 Task
   - 不在 Plan 中 → 执行期变更，继续步骤 3

3. 执行期变更量级判断
   - 小 (≤1 Task，不改公开接口) → Task 内修复，备注列记录
   - 中 (多 Task，改公开接口，架构不变) → 回退⑤ I/O 设计
   - 大 (改架构 / 数据流) → 回退③架构设计

4. 输出路由判断，等待用户确认后再继续

不允许跳过路由探测直接开始编码或生成 spec。
</ROUTER>

<HARD-GATE>
在开始 writing-plans 或 SDD 前，必须确认：

1. requirements spec 包含 8 项（目标用户、核心问题、成功标准、功能列表P0/P1/P2、
   硬约束、术语表、No-Gos、核心场景Given/When/Then）– 任何一项为空则 STOP

2. I/O spec 每个核心接口有：
   函数签名 + 输入样例 + 输出样例 + 断言 + 界面 I/O (看到/做了/反馈) – 缺失则 STOP

3. 存在 approved Master Plan 表格，每个 Task 有：
   类型、核心产出、依赖、验收标准 – 缺失则 STOP

4. 每个 Task 的验收标准经用户显式确认 – 未确认则 STOP

5. PENDING 状态的 Task 不得直接执行：
   必须等前置 Task 完成 → 展示产出物 → 用户确认
   → 补全方案和验收标准 → 用户再次确认 → 才能开始执行

6. 每完成一个 Task 必须回写 Master Plan 表格（状态 + 备注）

不允许在以上条件未满足时开始。不允许在 Master Plan 之外自行开工。
</HARD-GATE>

### Tool Roles

- **superpowers** (auto-triggered) — Design → Plan → Execute. Hard Gate prevents coding without spec.
- **gstack** (manual) — `/review`, `/ship`, `/qa`, `/retro`, `/document-release`
- **Custom commands** (manual) — `/save`, `/load`, `/review-req`, `/review-delivery`

### Session State Management

- Start new session: `/load` (global overview)
- Continue module work: `/load <module-name>` (detailed context)
- Save progress: `/save` (incremental checkpoint + git commit)

## Custom Commands

| Command | Purpose |
|---------|---------|
| `/save` | Save session progress incrementally with Git |
| `/review-req` | Red Team requirement review — 7 groups of challenges |
| `/review-delivery` | Delivery acceptance — 5 check groups against original spec |
| `/load` | Load project state and module context |
| `/init-project` | Initialize new project with Claude Code configuration |
| `/create-issue` | Convert ideas into structured task tickets |

## Context Window Management

- 50-60%：完成当前任务 → `/save` → 建议新会话
- >60%：立即收尾最小可关闭单元 → `/save` → `/load` 重开
- 不在 >50% 时开启大型多步任务

## Project Rules

### Module Organization

- **backend/**: Python 代码按 `backend/app/<feature>/` 组织，测试在 `backend/test/`
- **frontend/**: React 代码在 `frontend/src/`，按功能分目录（components / pages / services）
- **data/**: 小样本放 `data/samples/`（跟踪）；大文件放 `data/raw/`（`.gitignore` 已忽略）
- **docs/**: 严格按四级子目录划分，文档创建前先查对应 `index.md`
- **docker-compose.yml**: 所有基础服务（Postgres / Redis / Milvus / ES / MinIO）统一在此编排

### Code Standards

- **Python**: Python 3.10+，类型注解必备，公开接口有 docstring
- **TypeScript**: `strict: true`，函数式优先；禁止 `any`
- **命名**：后端 snake_case，前端 camelCase，组件 PascalCase
- **目录**：避免根目录堆文件，新文件优先放入已有模块子目录

### Security Requirements

- 任何 API Key / 密钥只存在 `.env`（已被 `.gitignore` 覆盖）
- 前端代码中禁止出现后端密钥
- 数据库连接串通过环境变量读取，不写死
- 任何用户输入进数据库前必须参数化查询（避免 SQL 注入）

### Testing Requirements

- **后端**：每个新业务函数至少 1 个 pytest 测试；失败测试先于实现（TDD）
- **前端**：交互/表单组件至少 1 个 vitest 或 Playwright 场景
- `/save` 前必须跑过本模块测试；未过需在 checkpoint.md 备注

### File Creation Policy（防文档爆炸）

- **优先追加，不轻易新建**：有现有文件可容纳内容时，追加到现有文件，不创建新文件
- **新建文件的条件**：内容是全新独立主题，或现有文件超过 300 行
- **目录文件数量上限**：单个目录超过 10 个文件时，必须先合并或归档再新建
- **禁止碎片化记录**：同一主题的内容不得拆散到多个小文件中

### Documentation Index Rules（强制）

每个 `docs/` 子目录有自己的 `index.md` 作为该目录的注册表。

**创建任何 `docs/` 下的 `.md` 文件前：**
1. 查对应子目录的 `index.md`，有相关文档则更新，不新建

**创建任何 `docs/` 下的 `.md` 文件后：**
1. 立即在对应子目录的 `index.md` 追加一行：`| 文档 | 路径 | 描述 | 更新日期 |`

### Code Quality SOP

**触发条件**：新建独立文件、新建独立函数/类时触发。修改已有代码无需执行。

```
Step 1：搜索项目内是否已有类似实现（Grep/Glob）
Step 2：已存在 → 扩展现有代码，不新建
        不存在 → 允许创建
```

## Important Files

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `checkpoint.md` | Project progress tracking | High (every /save) |
| `AGENTS.md` | Shared cross-tool contract | Low |
| `docker-compose.yml` | Base services orchestration | Low |
| `docs/exec-plans/active/master-plan.md` | Current execution plan | High |
| `docs/design-docs/*` | Architecture & module responsibility | Medium |

## Documentation Guidelines

### Document Organization Principle

- CLAUDE.md is an **index, not a warehouse**
- Keep it concise to save context window
- Reference detailed docs in `docs/` directories

### Creating New Documentation

1. **Check index first**: Read the target subdirectory's `index.md`，有相关文档则更新，不新建
2. **Create document**: Place in the appropriate `docs/` subdirectory
3. **Register immediately**: Add a row to that subdirectory's `index.md` — no exceptions
