# Checkpoint

> 最后更新：2026-04-25

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

- 撰写 PRD：明确目标用户、核心问题、成功标准
- 架构评审：确认 backend/frontend 与 search/knowledge-graph/visualization 的职责边界
- 完成 I/O spec：各核心接口定义函数签名、输入输出样例
- 输出 Master Plan 并走 Hard Gate 审批

### 依赖关系

- search 依赖 backend 的数据层和向量检索接入（Milvus）
- knowledge-graph 依赖 backend（图谱存取）与 search（实体抽取）
- visualization 依赖 frontend 与 knowledge-graph 输出
- 所有模块依赖 docker-compose.yml 的基础服务正常运行

---

## backend模块

**负责**：Unassigned
**状态**：未开始 (0%)
**测试状态**：⚠️ 未验证（最后运行：-）
**分支**：main
**最后更新**：2026-04-25

### 最近完成
- 项目初始化（Claude Code 配置、AGENTS.md/CLAUDE.md）
- 已存在 backend/app/ 代码骨架（待盘点）

### 进行中
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
- [2026-04-25] 初始化 Claude Code 项目配置：AGENTS.md / CLAUDE.md / checkpoint.md / docs 骨架
- [2026-04-25] 产出 `docs/design-docs/architecture.md`：系统架构文档 v1.0（四层模型、LangGraph 编排、存储拓扑、数据流、已知风险）

---

## 已知问题

- 根目录存在 `READMED.md` 拼写错误（预期为 `README.md`），待处理

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
