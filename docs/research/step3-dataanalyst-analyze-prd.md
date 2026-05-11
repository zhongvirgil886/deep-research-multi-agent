# Step 3 PRD: DataAnalyst Analyze

## 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 阶段 | Step 3: DataAnalyst - 数据分析阶段 |
| 所属产品 | AI 深度研究助手 |
| 文档类型 | 基于当前代码反推的产品 PRD |
| 当前状态 | Draft |
| 覆盖范围 | 从 DeepScout 产出的事实库到结构化数据、知识图谱、ECharts 图表配置和数据洞察 |
| 不覆盖范围 | Python 代码执行、Matplotlib 图片生成、报告写作、质量审稿、审核后补充搜索 |
| 主要代码依据 | `backend/app/service/deep_research_v2/agents/data_analyst.py`, `backend/app/service/deep_research_v2/state.py`, `backend/app/service/deep_research_v2/graph.py`, `frontend/src/pages/chat/index.tsx`, `frontend/src/pages/chat/component/research-detail/index.tsx`, `frontend/src/pages/chat/component/research-detail/visualization.tsx`, `frontend/src/pages/chat/component/research-detail/knowledge-graph.tsx` |

## 2. 产品背景

DeepScout 阶段已经把搜索结果转化为事实、数据点、来源和实体线索，但这些资产仍然偏原始。如果直接交给写作阶段，系统只能把事实逐条拼接成文本，无法稳定回答趋势、分布、对比、实体关系等分析型问题。

DataAnalyst 阶段的产品目标，是把事实证据进一步加工成可分析、可视化、可在报告中引用的中间资产。它不负责执行任意 Python 代码，而是通过 LLM 生成结构化结果和 ECharts 配置，让后续 CodeWizard、LeadWriter 和前端详情面板可以消费同一套分析资产。

当前实现中，DataAnalyst 是 Analyze 阶段的第一位 Agent。Graph 在进入 `phase="analyzing"` 后先运行 DataAnalyst，再运行 CodeWizard。因此 DataAnalyst 的输出质量会直接影响后续代码图表生成与报告图文混排。

## 3. 问题定义

### 3.1 用户问题

用户希望深度研究结果不仅有来源和事实，还能给出关键数据、趋势判断、实体关系和可视化解释。

### 3.2 产品需要解决的问题

系统需要在分析阶段完成：

- 从事实库中提取可量化数据点。
- 识别时间序列、分布数据和指标类别。
- 从事实文本中提取关键实体和关系。
- 生成前端可直接渲染的 ECharts 图表配置。
- 将数据洞察写回全局状态，供写作阶段使用。
- 把知识图谱和图表通过事件流推送到前端。

### 3.3 成功定义

DataAnalyst 阶段成功的标志不是“调用了分析模型”，而是形成了可复用的分析资产：

- `data_points` 被补充为更完整的结构化数据。
- `insights` 包含可写入报告的趋势或对比结论。
- `knowledge_graph.nodes/edges` 可被前端图谱视图渲染。
- `charts` 至少在存在足够数据时包含 ECharts 配置。
- 前端能收到 `knowledge_graph` 和 `charts` 事件。
- 完成后能发送 `research_step` 完成事件，统计事实、图表和实体数量。

## 4. 目标用户与使用场景

### 4.1 目标用户

- 行业研究人员：需要把资料转化为趋势、分布和市场结构。
- 咨询和投研用户：需要在报告中看到数据图表和实体关系。
- 企业知识工作者：需要把内部资料与外部事实统一抽象成可分析对象。

### 4.2 核心场景

**场景 A：事实到数据点**

用户提出市场规模、竞争格局、增长趋势类问题。DeepScout 产出事实后，DataAnalyst 从事实中提取市场规模、增长率、市场份额、排名等数据点，写入 `state["data_points"]`。

**场景 B：事实到知识图谱**

用户研究产业链、技术路线、企业竞争关系。DataAnalyst 从事实文本中抽取实体节点和关系边，生成 `knowledge_graph`，前端在详情面板的图谱页展示节点和边。

**场景 C：数据到 ECharts 图表**

用户研究主题中包含时间序列或结构占比数据。DataAnalyst 生成 ECharts `option`，前端在图表页渲染折线图、柱状图、饼图、横向条形图等。

**场景 D：分析洞察进入写作**

LeadWriter 撰写章节时读取 `insights`、`data_points` 和 `charts`，把趋势判断和图表引用整合到报告正文中。

## 5. 产品目标

### 5.1 当前阶段目标

DataAnalyst 阶段应完成以下目标：

1. 只在 `state["phase"] == "analyzing"` 时执行。
2. 发送 `research_step` running 事件，标记数据分析开始。
3. 从 `state["facts"]` 的前 20 条事实中提取结构化数据。
4. 识别 `data_points/time_series/distributions/insights`。
5. 将 `data_points` 追加到全局状态。
6. 将 `insights` 追加到全局状态。
7. 从 `state["facts"]` 的前 15 条事实中构建知识图谱。
8. 为知识图谱节点补充 `size`，便于前端表达重要性。
9. 在有足够数据时生成 ECharts 图表配置。
10. 将图表追加到 `state["charts"]`。
11. 发送 `knowledge_graph` 与 `charts` 事件。
12. 发送 `research_step` completed 事件，并带上事实、图表和实体统计。

### 5.2 非目标

DataAnalyst 阶段不负责：

- 执行 LLM 生成的 Python 代码。
- 生成 base64 图片图表。
- 对图表代码做安全沙箱校验。
- 编写最终研究报告。
- 审核事实是否存在幻觉。
- 决定是否需要补充搜索或修订报告。

## 6. 功能范围

### 6.1 Must Have

1. 读取 `facts` 作为分析输入。
2. 支持无事实时安全返回空分析结果。
3. 通过 LLM 提取结构化数据，输出 JSON。
4. 追加 `data_points`，不覆盖已有数据点。
5. 追加 `insights`，不覆盖已有洞察。
6. 通过 LLM 构建知识图谱，输出 `nodes` 和 `edges`。
7. 为节点按 `importance` 计算 `size`。
8. 在存在数据时生成 ECharts 图表配置。
9. 图表缺失 `id` 时自动补充 `chart_<uuid>`。
10. 发送前端可消费的 `knowledge_graph` 事件。
11. 发送前端可消费的 `charts` 事件。
12. 发送数据分析步骤开始和完成事件。

### 6.2 Should Have

1. 数据提取应覆盖市场规模、增长率、市场份额、排名、时间序列。
2. 知识图谱实体类型应覆盖核心概念、技术、企业、政策、产品、人物。
3. ECharts 图表类型应按数据形态选择：时间序列用折线，分类比较用柱状，占比用饼图。
4. 图表样式应保持专业、简洁，使用稳定配色。
5. 数据不足时应跳过图表生成，而不是构造假数据。

### 6.3 Could Have

1. 支持为每个章节生成独立知识子图。
2. 支持对数据点做冲突检测。
3. 支持给图表绑定 `section_id`。
4. 支持把洞察按章节归类。
5. 支持图表配置 schema 校验。

## 7. 输入输出契约

### 7.1 上游输入

DataAnalyst 依赖 Step 1 和 Step 2 形成的全局状态：

| 字段 | 类型 | 来源 | 用途 |
| --- | --- | --- | --- |
| `query` | string | 用户原始问题 | 作为分析主题 |
| `phase` | string | Graph | 必须为 `analyzing` |
| `facts` | array | DeepScout | 数据提取和知识图谱构建 |
| `data_points` | array | DeepScout 或 DataAnalyst | 图表生成的现有数据 |
| `outline` | array | ChiefArchitect | 后续报告章节上下文 |
| `knowledge_graph` | object | ChiefArchitect 或 DeepScout | 当前知识图谱状态 |
| `messages` | array | Agent 共享消息区 | 追加前端事件 |

### 7.2 数据提取输入

DataAnalyst 当前最多读取前 20 条事实，格式化为：

```text
- {content} (来源: {source_name})
```

每条事实至少应包含：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `content` | string | 是 | 事实正文 |
| `source_name` | string | 否 | 来源名称 |
| `source_url` | string | 否 | 来源链接，后续引用使用 |
| `credibility_score` | number | 否 | 来源可信度 |
| `related_sections` | array | 否 | 关联章节 |

### 7.3 数据提取输出

LLM 应返回 JSON：

```json
{
  "data_points": [
    {
      "id": "dp_001",
      "name": "中国AI市场规模",
      "value": 5000,
      "unit": "亿元",
      "year": 2024,
      "source": "艾瑞咨询",
      "category": "market_size",
      "confidence": 0.9
    }
  ],
  "time_series": [
    {
      "id": "ts_001",
      "metric": "AI市场规模",
      "unit": "亿元",
      "data": [
        {"year": 2020, "value": 3200},
        {"year": 2024, "value": 8500}
      ],
      "source": "艾瑞咨询"
    }
  ],
  "distributions": [
    {
      "id": "dist_001",
      "name": "细分领域市场份额",
      "year": 2024,
      "data": [
        {"category": "计算机视觉", "value": 32, "unit": "%"}
      ],
      "source": "IDC"
    }
  ],
  "insights": ["市场规模保持增长"]
}
```

### 7.4 知识图谱输出

知识图谱必须满足：

```json
{
  "nodes": [
    {
      "id": "ai",
      "name": "人工智能",
      "type": "core",
      "importance": 10,
      "size": 50
    }
  ],
  "edges": [
    {
      "source": "baidu",
      "target": "ai",
      "relation": "布局"
    }
  ]
}
```

节点要求：

- `id` 在当前图中唯一。
- `name` 面向用户可读。
- `type` 建议使用 `core/tech/company/policy/product/person`。
- `importance` 范围为 1-10。
- `size` 由系统按 `20 + importance * 3` 补充。

### 7.5 ECharts 图表输出

图表对象必须满足：

```json
{
  "id": "chart_001",
  "title": "中国AI市场规模",
  "subtitle": "2020-2024年市场规模（亿元）",
  "type": "line",
  "echarts_option": {
    "xAxis": {"type": "category", "data": ["2020", "2024"]},
    "yAxis": {"type": "value"},
    "series": [{"type": "line", "data": [3200, 8500]}]
  }
}
```

前端要求：

- `echarts_option` 必须为可被 `echarts-for-react` 渲染的对象。
- `title` 必须简洁，不能只写“图表1”。
- `type` 建议与 ECharts series 类型一致或使用产品约定类型。
- 如果缺少 `id`，后端会自动生成，但推荐 LLM 返回稳定语义 ID。

### 7.6 状态输出

DataAnalyst 应修改以下状态：

| 字段 | 写入方式 | 说明 |
| --- | --- | --- |
| `data_points` | append | 新提取的数据点 |
| `insights` | append | 数据洞察 |
| `knowledge_graph` | replace | 当前分析生成的图谱 |
| `charts` | append | ECharts 图表配置 |
| `messages` | append | 事件流消息 |

## 8. 分析流程

### 8.1 阶段进入流程

1. Graph 发送 `phase` 事件：`phase="analyzing"`。
2. Graph 设置 `state["phase"] = "analyzing"`。
3. Graph 先运行 `DataAnalyst.process(state)`。
4. DataAnalyst 检查阶段是否为 `analyzing`。
5. 如果不是 `analyzing`，直接返回原状态。

### 8.2 数据提取流程

1. 收集前 20 条 `facts`。
2. 格式化事实内容和来源名称。
3. 无事实时返回空数组。
4. 调用 LLM，要求输出 JSON。
5. 解析 JSON 响应。
6. 将 `data_points` 追加到全局状态。
7. 将 `insights` 追加到全局状态。

### 8.3 知识图谱构建流程

1. 收集前 15 条事实正文。
2. 无内容时返回空图谱。
3. 调用 LLM 提取实体与关系。
4. 解析 `nodes/edges`。
5. 为每个节点按 `importance` 补充 `size`。
6. 写入 `state["knowledge_graph"]`。
7. 发送 `knowledge_graph` 事件。

### 8.4 图表配置生成流程

1. 汇总本轮提取的 `data_points/time_series/distributions`。
2. 补充读取已有 `state["data_points"]` 前 10 条。
3. 如果三类数据总量为 0，则跳过图表生成。
4. 调用 LLM 生成 ECharts 配置。
5. 解析 `charts` 数组。
6. 对缺失 `id` 的图表补充 UUID。
7. 追加到 `state["charts"]`。
8. 发送 `charts` 事件。

## 9. 事件与前端展示需求

### 9.1 阶段事件

进入分析阶段时，Graph 发送：

```json
{
  "type": "phase",
  "phase": "analyzing",
  "content": "开始数据分析..."
}
```

DataAnalyst 开始时发送：

```json
{
  "type": "research_step",
  "content": {
    "step_type": "analyzing",
    "title": "数据分析",
    "subtitle": "生成可视化",
    "status": "running",
    "stats": {
      "results_count": 0,
      "charts_count": 0,
      "entities_count": 0
    }
  }
}
```

完成时发送：

```json
{
  "type": "research_step",
  "content": {
    "step_type": "analyzing",
    "title": "数据分析",
    "subtitle": "生成可视化",
    "status": "completed",
    "stats": {
      "results_count": 12,
      "charts_count": 2,
      "entities_count": 10
    }
  }
}
```

### 9.2 知识图谱事件

```json
{
  "type": "knowledge_graph",
  "content": {
    "graph": {
      "nodes": [],
      "edges": []
    },
    "stats": {
      "entities_count": 10,
      "relations_count": 14
    }
  }
}
```

前端详情面板应：

- 把 `graph` 存入当前研究详情。
- 在图谱 tab 渲染节点和关系。
- 展示实体数和关系数。

### 9.3 图表事件

```json
{
  "type": "charts",
  "content": {
    "charts": [
      {
        "id": "chart_001",
        "title": "市场规模趋势",
        "type": "line",
        "echarts_option": {}
      }
    ]
  }
}
```

前端应：

- 将图表存入 `detail.charts`。
- 同步更新当前消息的 `charts`。
- 在研究过程步骤条中展示图表数量。
- 在图表 tab 用 `ReactECharts` 渲染。
- 在报告 tab 中允许按标题匹配并内联插入图表。

### 9.4 检查点恢复

Graph 在 DataAnalyst 和 CodeWizard 都完成后保存 Analyze 检查点：

```json
{
  "type": "analyzing",
  "status": "completed",
  "stats": {
    "charts": 2
  }
}
```

恢复时，前端应从 checkpoint 的 `ui_state.charts` 和 `ui_state.knowledge_graph` 恢复图表与图谱。

## 10. 数据质量规则

### 10.1 数据点规则

- 只提取有明确来源的数据。
- `confidence` 范围必须为 0-1。
- `year` 不确定时可为 null，但不能伪造年份。
- `value` 应尽量使用数值，不把完整句子塞入数值字段。
- `unit` 应保留原始单位，如“亿元”“%”“亿美元”。

### 10.2 时间序列规则

- 同一 `time_series` 中的 `metric` 必须一致。
- `data` 中每项必须包含 `year` 和 `value`。
- 年份顺序建议从早到晚。
- 缺失年份不能自动补齐为 0。

### 10.3 分布数据规则

- `distribution.data` 中的 `category` 必须为用户可读分类。
- 百分比总和不一定强制为 100，但应避免明显矛盾。
- 如果来源只给出排名，不应伪造成市场份额。

### 10.4 图表规则

- 无数据时不生成图表。
- 图表标题必须对应研究主题或章节。
- 图表配置不能依赖浏览器外部脚本。
- ECharts 配置不能包含不可序列化对象。

## 11. 非功能需求

### 11.1 可追踪性

每个数据点应尽量保留来源名称，后续写作和审核可以追踪数据出处。

### 11.2 可解释性

图表和知识图谱应能解释研究主题，而不是只展示装饰性可视化。

### 11.3 稳定性

LLM 返回空结果或解析失败时，系统应返回空结构，不应中断整个研究流程。

### 11.4 扩展性

数据提取、知识图谱、图表生成应保持相互独立，便于后续替换为确定性抽取器或专用图表服务。

### 11.5 性能

当前阶段限制读取事实数量，避免把全部搜索结果塞入单次 LLM 调用。

## 12. 验收标准

### 12.1 功能验收

1. 当 `phase="analyzing"` 且 `facts` 非空时，DataAnalyst 能执行完整分析流程。
2. 当 `facts` 为空时，DataAnalyst 不抛异常。
3. 成功提取数据时，`state["data_points"]` 数量增加。
4. 成功提取洞察时，`state["insights"]` 数量增加。
5. 成功构建图谱时，`state["knowledge_graph"]` 包含 `nodes` 和 `edges`。
6. 成功生成图表时，`state["charts"]` 包含 `echarts_option`。
7. 前端能收到 `knowledge_graph` 事件并渲染图谱 tab。
8. 前端能收到 `charts` 事件并渲染图表 tab。
9. 完成事件中的 `charts_count/entities_count` 与状态统计一致。

### 12.2 异常验收

1. LLM 返回空 JSON 时，不影响后续 CodeWizard 执行。
2. 图表数据不足时，系统跳过图表生成，不生成假图。
3. 知识图谱节点缺失 `importance` 时，系统使用默认值补充 `size`。
4. 图表缺失 `id` 时，系统自动生成。
5. Graph 保存检查点时包含已生成图表统计。

### 12.3 典型案例

以下案例用于说明阶段契约，不代表一次真实线上运行结果。

#### 12.3.1 输入

来自 Step 2 的状态摘要：

```json
{
  "query": "研究 2024-2026 中国 AI 芯片市场格局、主要玩家、技术趋势和投资风险。",
  "phase": "analyzing",
  "facts": [
    {
      "id": "fact_market_001",
      "content": "示例行业报告称，中国 AI 芯片市场在 2024 年继续增长，主要受大模型推理需求驱动。",
      "source_name": "示例行业报告",
      "source_url": "https://example.com/ai-chip-report",
      "credibility_score": 0.78,
      "related_sections": ["sec_1"]
    },
    {
      "id": "fact_vendor_001",
      "content": "寒武纪、华为昇腾和壁仞科技是国产 AI 芯片生态中的代表性参与者。",
      "source_name": "示例产业研究",
      "source_url": "https://example.com/vendor-report",
      "credibility_score": 0.74,
      "related_sections": ["sec_2"]
    }
  ],
  "data_points": [
    {
      "id": "dp_market_2024",
      "name": "中国 AI 芯片市场规模",
      "value": 500,
      "unit": "亿元",
      "year": 2024,
      "source": "示例行业报告",
      "confidence": 0.78
    }
  ],
  "knowledge_graph": {
    "nodes": [],
    "edges": []
  },
  "charts": []
}
```

#### 12.3.2 调用链与方案

##### 12.3.2.1 进入分析阶段：把研究材料转成结构化分析产物

**当前行为**：Graph 发送 `phase="analyzing"`，先调用 `DataAnalyst.process(state)`。

**目标**：把 Step2 收集到的事实、来源和初步数据转入分析阶段，开始提取结构化数据、洞察、知识图谱和图表配置。

**作用**：这是 Analyze 阶段的第一步。DataAnalyst 主要负责结构化理解，不负责执行任意代码；CodeWizard 会在其后继续做代码/图表增强。

##### 12.3.2.2 提取候选数据：从事实库中选择可分析材料

**当前行为**：DataAnalyst 调用 `_extract_data()`，读取前 20 条事实。

**目标**：从事实库中挑选一批材料，尝试抽取数值、时间序列、分布、趋势和分析洞察。

**作用**：这一步把文本事实转成后续可计算、可画图、可写入报告的数据素材。

**当前限制**：当前是读取 `state["facts"][:20]`，即事实列表中的前 20 条，不是按相关性、可信度或章节重要性排序后的前 20 条。后续应改为基于 section、source quality、recency 和 data relevance 的筛选。

##### 12.3.2.3 调用数据抽取模型：生成数据点、序列、分布和洞察

**当前行为**：Agent 通过 `DATA_EXTRACTION_PROMPT` 调用 LLM，提取 `data_points/time_series/distributions/insights`。

**目标**：让 LLM 从自然语言事实中识别可结构化的信息，并输出统一 schema。

**作用**：

1. `data_points` 为 Step4 分析、Step5 写作和 Step6 审核提供数字依据。
2. `time_series` 支持趋势图。
3. `distributions` 支持占比和结构分析。
4. `insights` 为报告提供分析观点。

**当前限制**：LLM 抽取可能误读数值、遗漏单位、混淆年份或把不确定描述转成确定数据。后续应保留 `source_fact_id/source_url/source_quote/confidence`，并用确定性校验约束数值字段。

##### 12.3.2.4 构建知识图谱：从事实中提取实体和关系

**当前行为**：DataAnalyst 调用 `_build_knowledge_graph()`，读取前 15 条事实，提取实体和关系。

**目标**：把文本事实中出现的公司、技术、产品、机构、市场关系等转为 `nodes/edges`。

**作用**：知识图谱帮助用户理解研究对象之间的关系，也为前端可视化和后续报告中的关系分析提供材料。

**当前限制**：这是项目代码中的自定义 LLM 抽取流程，不是 LangGraph 内置知识图谱能力。当前节点、边和关系类型主要来自 LLM 输出，缺少 schema 约束、去重、关系置信度和来源绑定。

##### 12.3.2.5 计算图谱节点大小：把重要性转为可视化权重

**当前行为**：系统按 `importance` 为图谱节点计算 `size`。

**目标**：让前端图谱可视化时能用节点大小表达实体重要程度。

**作用**：`importance` 是语义权重，`size` 是可视化属性。这个转换让核心实体在图谱上更醒目。

**当前限制**：`importance` 当前仍主要由 LLM 判断，不是基于引用次数、来源质量、关系中心性或数据证据计算。后续应引入确定性权重计算，例如 degree、PageRank、引用频次和来源置信度。

##### 12.3.2.6 生成图表输入：把提取数据交给图表生成流程

**当前行为**：DataAnalyst 调用 `_generate_charts()`，把本轮提取数据和已有 `data_points` 传给 `CHART_GENERATION_PROMPT`。

**目标**：根据已抽取的数据点、时间序列和分布信息，生成适合前端渲染的图表配置。

**作用**：这一步把结构化数据转成用户可视化理解的载体，例如趋势折线图、分类柱状图或占比图。

**当前限制**：图表选择和 ECharts option 当前仍由 LLM 生成，缺少图表类型规则、数据一致性校验和 `source_data_point_ids` 绑定。

##### 12.3.2.7 输出或跳过图表：避免在数据不足时生成假图

**当前行为**：如果存在可用数据，LLM 输出 ECharts `option`；如果没有数据，则跳过图表生成。

**目标**：在有足够数据时输出可视化配置，在数据不足时避免为了展示而伪造图表。

**作用**：跳过图表比生成错误图表更安全。它能防止无数据场景下出现误导用户的可视化结果。

**当前限制**：是否“存在可用数据”仍偏宽松。后续应明确图表生成门槛，例如至少 2 个时间点才能画趋势图，占比图必须检查合计范围，x/y 序列长度必须一致。

#### 12.3.3 输出

状态写入示例：

```json
{
  "data_points": [
    {
      "id": "dp_growth_2025",
      "name": "中国 AI 芯片市场增速",
      "value": 28,
      "unit": "%",
      "year": 2025,
      "source": "示例行业报告",
      "confidence": 0.72
    }
  ],
  "insights": [
    "AI 芯片市场增长与大模型推理部署密切相关。"
  ],
  "knowledge_graph": {
    "nodes": [
      {"id": "ai_chip", "name": "AI 芯片", "type": "core", "importance": 10, "size": 50},
      {"id": "ascend", "name": "华为昇腾", "type": "product", "importance": 8, "size": 44}
    ],
    "edges": [
      {"source": "ascend", "target": "ai_chip", "relation": "属于"}
    ]
  },
  "charts": [
    {
      "id": "chart_market_trend",
      "title": "中国 AI 芯片市场增长趋势",
      "type": "line",
      "echarts_option": {
        "xAxis": {"type": "category", "data": ["2024", "2025"]},
        "yAxis": {"type": "value"},
        "series": [{"type": "line", "data": [500, 640]}]
      }
    }
  ]
}
```

前端事件示例：

```json
{
  "type": "charts",
  "content": {
    "charts": [
      {
        "id": "chart_market_trend",
        "title": "中国 AI 芯片市场增长趋势",
        "type": "line",
        "echarts_option": {}
      }
    ]
  }
}
```

#### 12.3.4 验收点

- `data_points` 新增项必须能追溯到来源。
- `knowledge_graph.nodes` 必须有可渲染的 `id/name/type/size`。
- `charts` 中的 ECharts 配置必须是可序列化对象。
- 数据不足时应跳过图表，不生成假图。
- 图表事件应能在前端图表 tab 渲染。

## 13. 当前代码依据

- `DataAnalyst.process()`：仅在 `ResearchPhase.ANALYZING` 时执行。
- `DataAnalyst._analyze_data()`：串联数据提取、知识图谱和 ECharts 图表生成。
- `DataAnalyst._extract_data()`：读取前 20 条事实，追加 `data_points` 和 `insights`。
- `DataAnalyst._build_knowledge_graph()`：读取前 15 条事实，生成 `nodes/edges` 并补充 `size`。
- `DataAnalyst._generate_charts()`：基于数据点、时间序列、分布数据生成 ECharts 配置。
- `ResearchState`：定义 `facts/data_points/knowledge_graph/charts/insights/messages`。
- `DeepResearchGraph._run_simplified()`：Analyze 阶段先运行 DataAnalyst，再运行 CodeWizard。
- `frontend/src/pages/chat/index.tsx`：处理 `charts`、`chart`、`knowledge_graph` 和 `research_step` 事件。
- `research-detail/visualization.tsx`：渲染 ECharts 与图片图表。
- `research-detail/knowledge-graph.tsx`：渲染知识图谱。

## 14. 边界与不做范围

- DataAnalyst 不验证外部来源真实性，只基于已有事实提取结构化数据。
- DataAnalyst 不执行 Python 代码，不产生 Matplotlib base64 图片。
- DataAnalyst 不保证每次都有图表，数据不足时应返回空图表。
- DataAnalyst 不负责把图表插入最终报告，只提供图表资产。
- DataAnalyst 不负责审核报告质量。

## 15. 后续需求变更候选

### 15.1 图表 schema 校验

**变更说明**：生成图表后先校验 ECharts 配置是否包含必要字段。

**价值**：减少前端渲染失败。

**影响范围**：DataAnalyst 图表生成、前端图表降级展示。

### 15.2 数据点去重与冲突检测

**变更说明**：按指标名、年份、单位、来源对数据点去重，并标记冲突值。

**价值**：避免写作阶段引用重复或冲突数据。

**影响范围**：`data_points` schema、CriticMaster 审核规则。

### 15.3 章节级图表绑定

**变更说明**：图表生成时绑定 `section_id`，LeadWriter 可更准确插入图表。

**价值**：提升图文混排准确度。

**影响范围**：DataAnalyst、LeadWriter、前端报告渲染。

### 15.4 图谱增量合并

**变更说明**：不直接覆盖 `knowledge_graph`，而是与 DeepScout 和历史图谱合并。

**价值**：保留跨阶段实体关系发现。

**影响范围**：图谱节点 ID 规则、边去重规则、前端恢复逻辑。

### 15.5 洞察可信度评分

**变更说明**：为 `insights` 增加来源映射和置信度。

**价值**：让写作和审核阶段知道哪些洞察更可靠。

**影响范围**：`insights` schema、LeadWriter prompt、CriticMaster prompt。

## 16. 待确认问题

1. DataAnalyst 生成的 ECharts 图表是否必须绑定章节，还是允许作为全局分析图？
2. 知识图谱是以 DataAnalyst 输出覆盖前序图谱，还是应改为增量合并？
3. 图表数量是否需要产品层上限，还是由 LLM 与前端自然承载？
4. 数据点冲突是否应在 Analyze 阶段解决，还是交给 Review 阶段指出？
