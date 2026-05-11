# Step 1 PRD: ChiefArchitect Planning

## 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 阶段 | Step 1: ChiefArchitect - 规划阶段 |
| 所属产品 | AI 深度研究助手 |
| 文档类型 | 基于当前代码反推的产品 PRD |
| 当前状态 | Draft |
| 覆盖范围 | 从用户原始问题到可执行研究计划 |
| 不覆盖范围 | 搜索执行、数据分析、报告撰写、质量审稿 |
| 主要代码依据 | `backend/app/service/deep_research_v2/agents/architect.py`, `backend/app/service/deep_research_v2/state.py`, `backend/app/service/deep_research_v2/graph.py`, `backend/app/router/research_router.py`, `frontend/src/pages/chat/index.tsx` |

## 2. 产品背景

深度研究任务的用户输入通常是开放式自然语言问题，例如“某行业市场现状和未来趋势是什么”。这类问题如果直接进入搜索或生成环节，容易出现三个问题：

1. 研究范围发散，后续搜索无法判断哪些信息是核心证据。
2. 研究过程不可审计，用户只能看到最终报告，无法理解答案是如何组织出来的。
3. 后续 Agent 缺少统一任务合同，搜索、分析、写作容易各自理解问题。

ChiefArchitect 阶段的产品目标，是把用户问题转化为可执行、可追踪、可恢复的研究计划。它不是最终回答用户问题，而是为后续 DeepScout、DataAnalyst、CodeWizard、LeadWriter、CriticMaster 建立共同的研究蓝图。

## 3. 问题定义

### 3.1 用户问题

用户希望系统对复杂主题进行深度研究，但用户通常不会主动提供完整研究框架、章节顺序、验证假设和搜索关键词。

### 3.2 产品需要解决的问题

系统需要在正式搜索前完成一次规划：

- 理解用户原始问题的研究意图。
- 拆解出可执行的研究章节。
- 为每个章节生成搜索关键词。
- 形成待验证的研究假设。
- 将规划过程通过 SSE 事件展示给前端，避免用户等待黑盒执行。

### 3.3 成功定义

该阶段成功的标志不是“生成了文本”，而是生成了后续阶段可直接消费的结构化状态：

- `outline` 非空，且章节数量满足最低要求。
- 每个章节具备 `id/title/description/section_type/search_queries/status` 等字段。
- `research_questions` 可用于解释研究关注点。
- `hypotheses` 可用于 Step 2 做证据验证。
- 前端可收到并展示 `planning` 阶段的运行和完成状态。

## 4. 目标用户与使用场景

### 4.1 目标用户

- 行业研究人员：需要快速建立研究框架。
- 投研、咨询、市场分析用户：需要从开放问题进入有结构的研究过程。
- 企业内部知识工作者：需要结合外部信息与本地知识库进行主题研究。

### 4.2 核心场景

**场景 A：行业趋势研究**

用户输入：“2026 年中国金融科技监管走向和重点机会”。系统应先规划市场背景、政策环境、监管重点、机会方向、风险因素等章节，而不是直接生成答案。

**场景 B：公司或行业机会判断**

用户输入：“某上市公司在某行业里的竞争力如何”。系统应识别公司、行业、竞争格局、财务或市场指标等研究维度，并为后续搜索提供关键词。

**场景 C：带本地知识库的研究**

用户选择本地知识库搜索时，规划阶段仍只负责拆解研究任务；是否搜索本地知识库由请求参数进入全局状态，供 Step 2 使用。

## 5. 产品目标

### 5.1 当前阶段目标

ChiefArchitect 阶段应完成以下目标：

1. 将自然语言查询转化为结构化研究计划。
2. 生成 5-8 个优先级清晰的研究章节；当前代码最低接受 3 个章节。
3. 为每个章节生成至少 1 个搜索关键词。
4. 生成可验证的研究假设，用于 Step 2 追踪支持或反驳证据。
5. 通过 SSE 输出阶段进度，使前端可展示规划过程。
6. 将规划结果写入全局 `ResearchState`，作为后续阶段输入。

### 5.2 非目标

ChiefArchitect 阶段不负责：

- 调用搜索 API。
- 抽取事实或计算来源可信度。
- 生成图表、数据分析或代码执行。
- 撰写最终报告。
- 判断最终报告质量。

## 6. 功能范围

### 6.1 Must Have

1. 接收用户原始 `query`。
2. 调用 LLM 生成研究大纲和研究假设。
3. 支持扁平 JSON 格式到标准 `outline` 格式的转换。
4. 对 LLM 输出进行基本有效性检查：必须存在 `outline` 且章节数量不少于 3。
5. 对每个章节补齐必要字段：
   - `id`
   - `title`
   - `description`
   - `section_type`
   - `requires_data`
   - `requires_chart`
   - `priority`
   - `search_queries`
   - `status`
6. 若章节缺少 `search_queries`，使用章节标题作为兜底搜索词。
7. 输出 `research_step` 事件，标记 `planning` 开始和完成。
8. 输出 `outline` 事件，供前端或日志消费。

### 6.2 Should Have

1. 生成面向验证的 `hypotheses`，每个假设包含：
   - `id`
   - `content`
   - `status`
   - `evidence_for`
   - `evidence_against`
2. 提取 `research_questions`，帮助解释本次研究关注点。
3. 初始化空知识图谱结构 `knowledge_graph = {"nodes": [], "edges": []}`。
4. 对 LLM 规划失败进行重试，降低偶发 JSON 失败概率。

### 6.3 Could Have

1. 根据行业类型选择不同规划模板。
2. 在进入 Step 2 前让用户确认或编辑大纲。
3. 给每个章节标记搜索预算、证据要求和优先级。
4. 展示假设与章节之间的映射关系。

## 7. 输入输出契约

### 7.1 上游输入

该阶段由 `/research/stream` 请求触发。V2 模式下，后端会创建或恢复 `ResearchState`。

请求侧关键字段：

| 字段 | 类型 | 说明 | 默认 |
| --- | --- | --- | --- |
| `query` | string | 用户原始研究问题 | 必填 |
| `session_id` | string/null | 会话 ID，用于检查点保存与恢复 | 可为空 |
| `max_iterations` | number | 最大迭代次数 | 3 |
| `kb_name` | string/null | 本地知识库名称，当前主要作为兼容字段 | null |
| `search_web` | boolean/null | 是否启用网络搜索，兼容旧版 | null |
| `search_local` | boolean/null | 是否启用本地知识库，兼容旧版 | null |
| `search_modes` | string[]/null | 新版搜索模式，如 `["web", "local"]` | null |
| `version` | `"v1"`/`"v2"` | 研究服务版本，V2 为多智能体架构 | `"v2"` |

### 7.2 状态输入

ChiefArchitect 从 `ResearchState` 读取：

| 字段 | 说明 |
| --- | --- |
| `query` | 用户原始问题 |
| `session_id` | 当前会话 ID |
| `phase` | 当前阶段；初始规划时应为 `init` |
| `search_web` | 是否启用网络搜索；规划阶段保留，不消费 |
| `search_local` | 是否启用本地搜索；规划阶段保留，不消费 |

### 7.3 状态输出

ChiefArchitect 写入：

| 字段 | 说明 |
| --- | --- |
| `outline` | 后续研究章节列表 |
| `research_questions` | 核心研究子问题 |
| `hypotheses` | 待验证研究假设 |
| `key_entities` | 关键实体，当前实现依赖 LLM 输出 |
| `mind_map` | 思维导图/知识结构，当前实现保留字段 |
| `knowledge_graph` | 初始化为空图谱 |
| `phase` | 更新为 `planning` |
| `errors` | 规划失败时追加错误 |

### 7.4 `outline` 字段规范

每个章节对象应满足：

```json
{
  "id": "sec_1",
  "title": "市场概况",
  "description": "描述市场规模、增速",
  "section_type": "mixed",
  "requires_data": true,
  "requires_chart": true,
  "priority": 1,
  "search_queries": ["金融科技监管 2026 市场趋势"],
  "status": "pending"
}
```

字段约束：

| 字段 | 约束 |
| --- | --- |
| `id` | 章节唯一标识，建议 `sec_N` |
| `title` | 面向用户可读的章节标题 |
| `description` | 说明该章节需要回答的问题 |
| `section_type` | `qualitative` / `quantitative` / `mixed`，当前默认 `mixed` |
| `requires_data` | 是否要求数据支撑 |
| `requires_chart` | 是否建议后续生成图表 |
| `priority` | 章节优先级 |
| `search_queries` | 非空数组；缺失时用标题兜底 |
| `status` | 初始为 `pending`，供 Step 2 筛选待研究章节 |

### 7.5 事件输出

ChiefArchitect 阶段通过 SSE 输出：

| 事件类型 | 触发时机 | 关键字段 |
| --- | --- | --- |
| `phase` | 进入规划阶段 | `phase="planning"`, `content="开始规划研究..."` |
| `research_step` | 规划开始 | `step_type="planning"`, `status="running"` |
| `thought` | 正在分析问题 | `agent="ChiefArchitect"`, `content` |
| `outline` | 大纲生成完成 | `outline`, `research_questions`, `key_entities` |
| `research_step` | 规划完成 | `step_type="planning"`, `status="completed"`, `stats.sections_count`, `stats.questions_count` |
| `checkpoint_saved` | 阶段结束后保存检查点 | `phase`, `session_id` |

## 8. 核心流程

1. 用户提交深度研究请求。
2. 路由解析请求参数，选择 V2 多智能体服务。
3. Graph 创建初始 `ResearchState`，写入 `query/session_id/search_web/search_local/max_iterations`。
4. Graph 发送 `research_start` 事件。
5. Graph 发送 `phase=planning` 事件。
6. ChiefArchitect 发送 `research_step running` 事件。
7. ChiefArchitect 调用 LLM 生成研究大纲和假设。
8. 若 LLM 返回扁平格式，转换为标准 `outline`。
9. 若无有效大纲或章节少于 3 个，最多重试 2 次。
10. ChiefArchitect 规范化章节字段，补齐搜索关键词和状态。
11. ChiefArchitect 写入 `ResearchState`。
12. ChiefArchitect 发送 `outline` 和 `research_step completed` 事件。
13. Graph 清空临时消息队列并保存检查点。
14. Graph 进入 Step 2: DeepScout。

## 9. 前端展示需求

前端应将该阶段展示为研究过程中的第一个步骤。

### 9.1 步骤条

`research_step` 事件映射为：

| 后端字段 | 前端含义 |
| --- | --- |
| `step_type="planning"` | 步骤类型：研究计划 |
| `title="研究计划"` | 步骤标题 |
| `subtitle="分析问题，制定大纲"` | 步骤说明 |
| `status="running/completed"` | 步骤状态 |
| `stats.sections_count` | 展示章节数量 |
| `stats.questions_count` | 展示研究问题数量 |

当前前端会将 snake_case 统计字段转换为 camelCase，例如 `sections_count -> sectionsCount`。

### 9.2 详情面板

当前前端会为 `planning` 创建研究详情记录，但主要详情面板能力集中在搜索结果、知识图谱、图表和报告。规划大纲的专用展示仍属于后续优化方向。

## 10. 检查点与恢复

规划阶段完成后，Graph 会保存检查点。检查点应包含：

- 后端研究状态：`state_json`
- UI 状态：`ui_state_json`
- 当前阶段：`phase`
- 会话 ID：`session_id`

前端恢复时，如果检查点包含 `research_steps`，应恢复规划步骤状态；如果没有步骤数据，当前前端会基于已有数据创建默认步骤。

## 11. 非功能需求

### 11.1 可解释性

规划结果必须结构化，不能只是一段自然语言。后续阶段应能从 `outline` 和 `hypotheses` 中解释为什么执行某个搜索。

### 11.2 稳定性

LLM 输出可能不是标准 JSON。系统需要：

- 启用 JSON 模式调用。
- 支持扁平格式转换。
- 对解析失败或大纲过短进行重试。
- 失败时写入 `errors`，不应静默进入后续阶段。

### 11.3 可扩展性

规划输出应允许未来扩展字段，例如：

- 章节级搜索预算。
- 章节级证据要求。
- 用户确认状态。
- 行业模板 ID。

### 11.4 性能

规划阶段主要耗时来自 LLM 调用。PRD 不设固定 SLA，但应避免多轮无意义重试。当前实现最多重试 2 次。

## 12. 验收标准

### 12.1 功能验收

| 编号 | 验收项 | 验收标准 |
| --- | --- | --- |
| A1 | 阶段启动 | SSE 中出现 `type=phase, phase=planning` |
| A2 | 步骤运行态 | SSE 中出现 `type=research_step, step_type=planning, status=running` |
| A3 | 大纲生成 | `state.outline.length >= 3` |
| A4 | 章节字段 | 每个章节均有 `id/title/search_queries/status` |
| A5 | 搜索关键词兜底 | 任一章节缺失搜索词时，最终 `search_queries` 不为空 |
| A6 | 研究问题 | 输出 `research_questions`，允许为空但应作为统计字段返回 |
| A7 | 假设生成 | 支持输出 `hypotheses`，每条假设有验证状态 |
| A8 | 步骤完成态 | SSE 中出现 `type=research_step, step_type=planning, status=completed` |
| A9 | 统计字段 | 完成事件包含 `stats.sections_count` 和 `stats.questions_count` |
| A10 | 检查点 | 规划结束后发送或保存 `checkpoint_saved` |

### 12.2 异常验收

| 场景 | 预期 |
| --- | --- |
| LLM 返回非 JSON | 触发重试 |
| LLM 返回扁平 JSON | 转换为标准 `outline` |
| 大纲少于 3 个章节 | 触发重试 |
| 多次失败 | 写入 `state.errors`，不声称规划成功 |
| 用户取消任务 | Graph 返回 `research_cancelled`，不继续进入 Step 2 |

### 12.3 典型案例

以下案例用于说明阶段契约，不代表一次真实线上运行结果。

#### 12.3.1 输入

用户问题：

```text
研究 2024-2026 中国 AI 芯片市场格局、主要玩家、技术趋势和投资风险。
```

初始状态摘要：

```json
{
  "query": "研究 2024-2026 中国 AI 芯片市场格局、主要玩家、技术趋势和投资风险。",
  "session_id": "sess_ai_chip_001",
  "phase": "init",
  "iteration": 0,
  "max_iterations": 3,
  "search_web": true,
  "search_local": false,
  "outline": [],
  "facts": [],
  "data_points": [],
  "messages": []
}
```

#### 12.3.2 调用链与方案

1. Graph 将初始状态交给 `ChiefArchitect.process(state)`。
2. ChiefArchitect 识别 `phase="init"`，进入 `_initial_planning()`。
3. Agent 通过 `BaseAgent.call_llm()` 调用规划模型，使用 `PLANNING_PROMPT`。
4. LLM 输出研究理解、大纲、关键实体、研究问题和假设。
5. 如果 LLM 输出扁平字段，如 `sec_1_title/sec_1_query`，系统调用 `_convert_flat_to_outline()` 转换。
6. 如果输出没有 `outline` 或章节少于 3 个，最多重试 2 次，并使用简化 prompt。
7. 系统规范化每个章节，补齐 `id/title/description/section_type/requires_data/requires_chart/search_queries/status`。

#### 12.3.3 输出

状态写入示例：

```json
{
  "phase": "planning",
  "outline": [
    {
      "id": "sec_1",
      "title": "市场规模与增长趋势",
      "description": "分析 2024-2026 年中国 AI 芯片市场规模、增速和需求来源。",
      "section_type": "quantitative",
      "requires_data": true,
      "requires_chart": true,
      "priority": 1,
      "search_queries": [
        "2024 中国 AI 芯片 市场规模 报告",
        "2025 中国 AI 加速芯片 增长率"
      ],
      "status": "pending"
    },
    {
      "id": "sec_2",
      "title": "主要玩家与竞争格局",
      "description": "梳理寒武纪、华为昇腾、壁仞科技等玩家的定位和竞争关系。",
      "section_type": "mixed",
      "requires_data": true,
      "requires_chart": false,
      "priority": 2,
      "search_queries": [
        "中国 AI 芯片 主要厂商 寒武纪 昇腾 壁仞"
      ],
      "status": "pending"
    }
  ],
  "research_questions": [
    "中国 AI 芯片市场的增长主要由哪些需求拉动？",
    "国产 AI 芯片厂商与海外 GPU 供应商的差距在哪里？"
  ],
  "hypotheses": [
    {
      "id": "h_1",
      "content": "推理算力需求增长会推动国产 AI 芯片市场扩张。",
      "status": "untested",
      "evidence": []
    }
  ],
  "knowledge_graph": {
    "nodes": [],
    "edges": []
  }
}
```

前端事件示例：

```json
{
  "type": "research_step",
  "content": {
    "step_type": "planning",
    "title": "研究计划",
    "subtitle": "分析问题，制定大纲",
    "status": "completed",
    "stats": {
      "sections_count": 5,
      "questions_count": 4
    }
  }
}
```

#### 12.3.4 验收点

- `outline` 至少包含 3 个章节。
- 每个章节至少有 1 个非空 `search_queries`。
- `requires_data/requires_chart` 能指导 Analyze 阶段是否生成数据和图表。
- `status` 初始化为 `pending`。
- 规划完成后才允许进入 DeepScout。

## 13. 当前代码依据

| 能力 | 代码位置 |
| --- | --- |
| 阶段状态枚举 | `backend/app/service/deep_research_v2/state.py` |
| 初始状态创建 | `backend/app/service/deep_research_v2/state.py:create_initial_state` |
| 请求模型与搜索模式解析 | `backend/app/router/research_router.py:ResearchRequest` |
| V2 SSE 入口 | `backend/app/router/research_router.py:stream_research` |
| Graph 阶段编排 | `backend/app/service/deep_research_v2/graph.py` |
| ChiefArchitect 规划提示词 | `backend/app/service/deep_research_v2/agents/architect.py` |
| 扁平格式转换 | `backend/app/service/deep_research_v2/agents/architect.py:_convert_flat_to_outline` |
| 初始规划逻辑 | `backend/app/service/deep_research_v2/agents/architect.py:_initial_planning` |
| 前端研究步骤消费 | `frontend/src/pages/chat/index.tsx` |
| 前端研究详情类型 | `frontend/src/pages/chat/component/research-detail/index.tsx` |

## 14. 边界与不做范围

本阶段不负责：

1. 判断搜索结果是否可信。
2. 访问 Bocha、Milvus 或其他检索服务。
3. 从网页中提取正文。
4. 生成数据图表。
5. 生成最终报告。
6. 执行 Critic 审核。

## 15. 后续需求变更候选

这些需求不属于当前反推范围，但建议作为后续版本演进候选。

### 15.1 用户确认研究计划

在 Step 1 和 Step 2 之间增加用户确认门：

- 用户可查看大纲、研究问题和假设。
- 用户可删除、重排、编辑章节。
- 用户可增加搜索关键词或禁用某些研究方向。
- 确认后再进入 DeepScout。

### 15.2 规划模板化

根据问题类型选择模板：

- 行业研究模板。
- 公司分析模板。
- 政策解读模板。
- 投资机会模板。
- 技术趋势模板。

### 15.3 章节级约束

为每个章节增加：

- `evidence_requirements`
- `preferred_source_types`
- `min_sources`
- `search_budget`
- `freshness_requirement`

### 15.4 假设可视化

将 `hypotheses` 显示为可验证对象：

- 未验证。
- 已支持。
- 已反驳。
- 部分支持。

Step 2 提取证据后动态更新假设状态。

### 15.5 规划质量评分

增加规划阶段质量指标：

- 章节覆盖度。
- 搜索词明确度。
- 假设可验证性。
- 章节之间是否重复。
- 是否遗漏关键研究维度。

## 16. 待确认问题

1. 是否需要在 Step 1 后强制用户确认大纲，还是默认自动进入 Step 2？
2. 规划阶段是否需要按行业模板生成不同结构？
3. `hypotheses` 是否要成为前端一级展示对象？
4. 是否需要为每个章节设置最少来源数和来源类型要求？
5. 规划失败时，产品上应终止任务还是允许用户手动编辑后继续？
