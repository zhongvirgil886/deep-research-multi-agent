# AGENTS.md

This file is the shared cross-tool project specification. Both Claude Code and Codex read this file as their project contract.

## Repository Role

基于 AI 的深度研究助手，支持智能搜索、知识图谱、数据可视化。Full-Stack 应用：Python FastAPI 后端 + React + Vite + TypeScript 前端 + Docker 编排基础服务（PostgreSQL / Redis / Milvus / Elasticsearch / MinIO）。Follow the coding conventions and testing requirements defined in CLAUDE.md.

## Start Here

Read `checkpoint.md` before making changes.

Use these entry points as needed:
- `docs/product-specs/index.md` — 需求与设计文档注册表
- `docs/exec-plans/index.md` — 执行计划注册表
- `docs/design-docs/index.md` — 长期参考文档（架构、职责矩阵）
- `CLAUDE.md` for Claude Code specific workflow rules

## Dual-Tool Workflow

本仓库同时使用 Claude Code 和 Codex，两者平级，由用户调度分配任务。

- 同一文件同一时刻只由一个工具修改，用户负责任务分配和冲突避免
- 共享项目规则在本文件维护，工具专用规则在各自配置文件维护
- 修改共享规则时优先改本文件，不在工具专用文件中重复

## Development Workflow

### Four Phases (Full Development)

| Phase | Core Activity | Output |
|-------|--------------|--------|
| **Phase 1** 需求分析 | PRD → 架构 → I/O → Master Plan | specs + architecture + io-spec + **Master Plan (approved)** |
| **Phase 2** TDD 开发 | 逐 Task 闭环：确认→TDD→验证→回写 | 代码 + 测试 + Master Plan 实时更新 |
| **Phase 3** 验证测试 | 代码审查 → QA → 交付验收 | 审查报告 + 验收结果 |
| **Phase 4** 报告归档 | 发布 → 文档同步 → 归档 | 发布产物 + 归档记录 |

### Pipeline Rules

- **Master Plan is the sole execution contract.** Only execute what's in the approved Master Plan.
- **I/O design is a Hard Gate.** After architecture review, before task breakdown, I/O design must be completed per module with user confirmation.
- **Mid-execution changes must enter the pipeline.** Assess impact → small / medium / large.
- **No skipping gates.** Failure → fix and retry, never "skip now fix later".
- **Acceptance criteria ownership belongs to user.** AI proposes, user confirms. Silence ≠ consent.
- **Task completion requires write-back.** Every completed Task updates Master Plan status + notes.

## Working Conventions

### Output Quality
- Requirements, plans, and specs must include concrete details: function signatures, file paths, algorithm names, data formats, threshold values.
- When asked to review or give feedback on a plan, align with the user's stated direction.

### Research Before Create
- 新建文件/函数前，先搜索项目内是否已有类似实现
- 新增依赖前，先查有无现成方案
- 存在 80%+ 匹配的现成方案时，优先复用而非重写

## Shared Working Rules

### File Creation Policy

- 优先追加现有文件，不轻易新建；新建条件为全新独立主题或现有文件超 300 行
- 单个目录超过 10 个文件时，必须先合并或归档再新建
- 同一主题的内容不得拆散到多个小文件中

### Documentation Index Rules

每个 `docs/` 子目录有自己的 `index.md` 作为该目录的注册表。

- 创建任何 `docs/` 下的 `.md` 文件前：查对应子目录的 `index.md`，有相关文档则更新，不新建
- 创建任何 `docs/` 下的 `.md` 文件后：立即在对应子目录的 `index.md` 追加一行登记

### General Rules

- Keep root files intentional; prefer docs under `docs/`, scripts under `scripts/`.
- Treat this file as the shared cross-tool contract. Keep it short and durable.
- Put long explanations in `docs/` instead of expanding this file.
- If a rule is specific to Claude Code workflow, keep it in `CLAUDE.md` rather than duplicating it here.

## Verification

- For documentation edits, verify referenced paths, commands, and filenames still exist.
- For workflow/rules edits, update all affected guidance files so they do not drift.
- Do not claim a command is standard for this repo unless it exists and is actually used.

## Project Structure Rules

### Root Files

- `AGENTS.md` — shared cross-tool contract (this file)
- `CLAUDE.md` — Claude-specific rules; imports AGENTS.md
- `README.md` — human-facing project overview and getting-started
- `checkpoint.md` — module progress tracking
- `.gitignore` — protects secrets and large files
- `docker-compose.yml` — base services orchestration
- `start-services.sh` — helper script for docker services
- `pyproject.toml` — Python package config (to be added if needed)

### File Placement Rules

- Backend code -> `backend/app/<feature>/`
- Backend tests -> `backend/test/`
- Frontend code -> `frontend/src/`
- Small sample data -> `data/samples/` or `examples/` or `tests/fixtures/`
- Large data (ignored) -> `data/raw/`, `data/processed/`
- Documentation -> `docs/<category>/`
- Scripts -> `scripts/`

### Artifact Paths

```
docs/
├── design-docs/          # Architecture and module responsibility
├── product-specs/        # Requirements, io-spec, reviews
├── exec-plans/
│   ├── active/           # Master plan, change log
│   └── completed/        # Final snapshots of completed plans
└── generated/            # Auto-generated docs (indexes, etc.)
```

## Progress Tracking

Project progress is recorded in `checkpoint.md`. Read it at the start of each session.
