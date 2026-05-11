# Step 2 PRD: DeepScout Research

## 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 阶段 | Step 2: DeepScout - 深度搜索阶段 |
| 所属产品 | AI 深度研究助手 |
| 文档类型 | 基于当前代码反推的产品 PRD |
| 当前状态 | Draft |
| 覆盖范围 | 从研究计划到结构化事实、数据点、来源与知识图谱增量 |
| 不覆盖范围 | 数据分析、代码生成、报告写作、质量审稿 |
| 主要代码依据 | `backend/app/service/deep_research_v2/agents/scout.py`, `backend/app/service/deep_research_v2/state.py`, `backend/app/service/deep_research_v2/graph.py`, `backend/app/router/research_router.py`, `frontend/src/pages/chat/index.tsx`, `frontend/src/pages/chat/component/research-detail/index.tsx` |

## 2. 产品背景

用户在深度研究中真正需要的不是一组搜索链接，而是一组可验证、可引用、可追踪的事实证据。普通搜索结果通常存在以下问题：

1. 只返回网页摘要，无法直接支撑报告。
2. 来源质量混杂，缺少可信度分级。
3. 多个页面可能重复表达同一事实。
4. 数据点、实体、关系没有结构化，无法交给后续数据分析和写作阶段。
5. 搜索过程不透明，用户看不到系统正在检索哪些章节和关键词。

DeepScout 阶段的产品目标，是把 Step 1 的研究计划转化为可被后续阶段消费的事实库、数据点、引用来源和知识图谱增量。

## 3. 问题定义

### 3.1 用户问题

用户希望系统给出有证据支撑的深度研究结果，而不是泛化生成的答案。

### 3.2 产品需要解决的问题

系统需要在搜索阶段完成：

- 按研究大纲拆分搜索任务。
- 支持网络搜索与本地知识库搜索。
- 将搜索结果转化为结构化事实。
- 为事实标注来源、来源类型和可信度评分。
- 从事实中抽取数据点。
- 识别实体与关系，更新知识图谱。
- 将搜索进展和搜索结果实时推送到前端。

### 3.3 成功定义

DeepScout 阶段成功的标志不是“调用了搜索 API”，而是生成了可用于后续分析与写作的证据资产：

- `facts` 中存在可验证事实。
- `data_points` 中存在可结构化利用的数据。
- `references` 或搜索结果可映射到前端来源展示。
- `knowledge_graph` 可随着实体发现逐步扩展。
- `hypotheses` 可根据证据更新状态。
- 前端能实时看到搜索进度和结果数量。

## 4. 目标用户与使用场景

### 4.1 目标用户

- 行业研究人员：需要高可信度来源和结构化事实。
- 咨询、投研、市场分析用户：需要在短时间内收集数据与证据。
- 企业内部知识工作者：需要同时利用互联网信息和本地知识库。

### 4.2 核心场景

**场景 A：网络深度搜索**

用户选择默认网络搜索。系统根据 Step 1 的章节搜索词调用 Bocha Web Search API，并把结果转成事实、数据点和来源。

**场景 B：本地知识库搜索**

用户开启本地知识库。系统使用 Milvus 向量检索获取内部文档片段，并以与网络搜索一致的格式进入事实抽取链路。

**场景 C：混合搜索**

用户同时开启网络和本地搜索。系统应把两类结果合并，保留来源类型，后续报告可以同时引用外部网页和内部资料。

**场景 D：补充搜索**

后续 Critic 发现信息缺失后，可把 `pending_search_queries` 交回 DeepScout，进入补充搜索。本文档聚焦首次 Step 2，但保留补充搜索作为能力边界。

## 5. 产品目标

### 5.1 当前阶段目标

DeepScout 阶段应完成以下目标：

1. 读取 Step 1 生成的 `outline`，筛选 `status="pending"` 的章节。
2. 每次最多并行处理 3 个待研究章节。
3. 根据 `search_web/search_local` 决定执行网络搜索、本地搜索或混合搜索。
4. 对每个章节的 `search_queries` 逐个检索，并实时发送搜索进度。
5. 使用 LLM 分析搜索结果，抽取事实、数据点、假设证据、实体、洞察和后续搜索线索。
6. 对事实进行去重，避免重复证据污染后续报告。
7. 更新 `facts/data_points/insights/knowledge_graph/hypotheses`。
8. 发送 `search_results` 事件供前端详情面板展示。
9. 完成后输出 `research_step completed` 和检查点。

### 5.2 非目标

DeepScout 阶段不负责：

- 对数据点进行统计分析或图表生成。
- 编写最终研究报告。
- 对报告做质量评分。
- 决定最终是否需要修订。

## 6. 功能范围

### 6.1 Must Have

1. 读取 `outline` 中待研究章节。
2. 识别搜索模式：
   - `search_web=true` 时执行网络搜索。
   - `search_local=true` 时执行本地知识库搜索。
   - 两者都未选时回退到网络搜索。
3. 发送 `research_step` 事件，标记 `searching` 开始和完成。
4. 发送 `search_progress` 事件，展示当前查询进展。
5. 发送 `search_results` 事件，展示原始或结构化搜索结果。
6. 调用搜索 API 获取网页结果。
7. 调用本地向量检索获取知识库结果。
8. 使用 LLM 从搜索结果中抽取 `extracted_facts`。
9. 为事实记录 `source_name/source_url/source_type/credibility_score`。
10. 对事实去重。
11. 将事实写入 `state.facts`。
12. 将数据点写入 `state.data_points`。
13. 更新假设证据状态。

### 6.2 Should Have

1. 识别搜索结果中的实体并更新知识图谱。
2. 识别需要追溯原始数据源的查询。
3. 识别后续搜索线索并递归搜索。
4. 支持搜索缓存，避免重复查询。
5. 支持网页正文深度读取。
6. 支持上市公司问题下的实时股票数据补充。

### 6.3 Could Have

1. 来源冲突检测。
2. 事实级引用链展示。
3. 用户手动收藏、排除或标记来源。
4. 搜索预算可视化。
5. 根据来源可信度自动过滤低质量结果。

## 7. 输入输出契约

### 7.1 上游输入

DeepScout 从 Step 1 接收规划结果：

| 字段 | 说明 |
| --- | --- |
| `query` | 用户原始研究问题 |
| `outline` | 研究章节列表 |
| `hypotheses` | 待验证假设 |
| `research_questions` | 研究子问题 |
| `search_web` | 是否使用网络搜索 |
| `search_local` | 是否使用本地知识库 |
| `iteration` | 当前迭代轮次 |
| `max_iterations` | 最大迭代次数 |

### 7.2 章节输入

DeepScout 只处理 `outline` 中 `status="pending"` 的章节。

章节对象至少应包含：

```json
{
  "id": "sec_1",
  "title": "市场概况",
  "description": "描述市场规模、增速",
  "search_queries": ["金融科技监管 市场规模 2026"],
  "status": "pending"
}
```

### 7.3 搜索模式

| 模式 | 条件 | 行为 |
| --- | --- | --- |
| 网络搜索 | `search_web=true` | 调用 Bocha Web Search API |
| 本地搜索 | `search_local=true` | 调用 Milvus 向量检索 |
| 混合搜索 | 两者都为 true | 合并网络与本地结果 |
| 默认回退 | 两者都为 false | 自动设置 `search_web=true` |

### 7.4 状态输出

DeepScout 写入：

| 字段 | 说明 |
| --- | --- |
| `phase` | 更新为 `researching` |
| `facts` | 结构化事实库 |
| `data_points` | 从事实中抽取的数据点 |
| `raw_sources` | 原始来源，当前字段保留 |
| `references` | 参考来源，供最终展示和报告引用 |
| `insights` | 搜索阶段得到的关键洞察 |
| `knowledge_graph` | 实体和关系增量 |
| `hypotheses` | 根据证据更新后的假设状态 |
| `pending_search_queries` | 补充搜索阶段使用 |
| `errors` | 搜索或分析失败记录 |

### 7.5 事实对象规范

`facts` 中的事实对象建议满足：

```json
{
  "id": "fact_ab12cd34",
  "content": "具体、可验证的事实陈述",
  "source_url": "https://example.com/report",
  "source_name": "来源名称",
  "source_type": "official",
  "credibility_score": 0.9,
  "extracted_at": "2026-05-10T12:00:00",
  "related_sections": ["sec_1"],
  "verified": false,
  "related_hypothesis": "h_1",
  "hypothesis_support": "supports"
}
```

字段约束：

| 字段 | 约束 |
| --- | --- |
| `content` | 必须具体、可验证，不能是宽泛观点 |
| `source_url` | 应指向原始网页、本地文档片段或 API 来源 |
| `source_name` | 来源名称，用于前端展示 |
| `source_type` | `official/academic/news/report/self_media/local` 等 |
| `credibility_score` | 0-1 分值 |
| `related_sections` | 关联章节 ID |
| `verified` | 当前默认为 false，后续可由交叉验证更新 |
| `related_hypothesis` | 可为空 |
| `hypothesis_support` | `supports/refutes/neutral` |

### 7.6 数据点对象规范

`data_points` 建议满足：

```json
{
  "id": "dp_ab12cd34",
  "name": "市场规模",
  "value": "1.2",
  "unit": "万亿元",
  "year": 2025,
  "source": "来源名称",
  "confidence": 0.85
}
```

## 8. 搜索与抽取流程

### 8.1 首次搜索流程

1. Graph 发送 `phase=researching`。
2. DeepScout 读取 `search_web/search_local`。
3. 如果两种搜索都未开启，自动回退到网络搜索。
4. DeepScout 从 `outline` 中筛选待研究章节。
5. 发送 `research_step searching running`。
6. 最多取前 3 个待研究章节并行执行。
7. 对每个章节的 `search_queries` 逐个执行搜索。
8. 每个查询完成后发送 `search_progress` 和 `search_results`。
9. 合并该章节所有结果。
10. 调用 LLM 分析搜索结果。
11. 抽取事实、数据点、实体、假设证据、洞察、后续搜索线索。
12. 事实去重后写入 `state.facts`。
13. 数据点写入 `state.data_points`。
14. 实体写入 `state.knowledge_graph`。
15. 假设证据写入 `state.hypotheses`。
16. 若发现源头追溯或后续线索，在搜索预算内继续递归搜索。
17. 发送阶段完成 `research_step searching completed`。
18. 发送聚合后的 `search_results`。
19. Graph 保存检查点并进入 Step 3。

### 8.2 网络搜索流程

网络搜索通过 Bocha Web Search API 执行：

| 参数 | 当前行为 |
| --- | --- |
| URL | `https://api.bocha.cn/v1/web-search` |
| `query` | 章节搜索词 |
| `summary` | true |
| `count` | 默认 10，补充搜索可为 8 或 6 |
| `freshness` | `noLimit` |
| 超时 | 30 秒 |

返回结果被规范化为：

```json
{
  "url": "https://example.com",
  "title": "页面标题",
  "summary": "摘要",
  "snippet": "片段",
  "site_name": "站点名称",
  "date": "发布日期或抓取日期"
}
```

### 8.3 本地知识库搜索流程

本地搜索通过 Milvus 向量检索执行：

1. 对查询生成 embedding。
2. 在 `knowledge_base` collection 中检索。
3. 返回 `top_k` 条文档片段。
4. 将本地结果格式化为与网络搜索相近的结构。

本地结果示例：

```json
{
  "url": "local://kb/{kb_id}/{doc_id}",
  "title": "文件名",
  "summary": "文档片段",
  "snippet": "短摘要",
  "site_name": "本地知识库",
  "score": 0.82,
  "is_local": true,
  "kb_id": "kb_1",
  "doc_id": "doc_1",
  "chunk_index": 3
}
```

### 8.4 LLM 抽取结果

DeepScout 的搜索分析应输出：

| 字段 | 说明 |
| --- | --- |
| `extracted_facts` | 结构化事实 |
| `hypothesis_evidence` | 对假设的支持、反驳或不确定证据 |
| `entities_discovered` | 新发现实体与关系 |
| `key_insights` | 搜索阶段洞察 |
| `follow_up_queries` | 后续线索搜索 |
| `source_tracing_queries` | 原始数据源追溯搜索 |
| `missing_info` | 仍缺失的信息 |
| `source_quality_assessment` | 来源质量评估 |

## 9. 事件与前端展示需求

### 9.1 阶段事件

| 事件类型 | 触发时机 | 关键字段 |
| --- | --- | --- |
| `phase` | 进入搜索阶段 | `phase="researching"`, `content="开始深度搜索..."` |
| `research_step` | 搜索开始 | `step_type="searching"`, `status="running"` |
| `thought` | 搜索策略说明 | `agent="DeepScout"`, `content` |
| `action` | 执行并行搜索 | `tool="parallel_search"`, `section`, `queries` |
| `search_progress` | 单个查询完成 | `query`, `results_count`, `total_so_far`, `section`, `progress`, `search_type` |
| `search_results` | 搜索结果返回 | `results`, `section`, `isIncremental` |
| `observation` | 章节分析完成 | `section`, `facts_added`, `insights`, `source_quality` |
| `research_step` | 搜索完成 | `step_type="searching"`, `status="completed"`, `stats.results_count`, `stats.sources_count` |
| `checkpoint_saved` | 阶段结束后保存检查点 | `phase`, `session_id` |

### 9.2 前端步骤条

`research_step` 被前端映射为研究过程步骤：

| 后端字段 | 前端展示 |
| --- | --- |
| `step_type="searching"` | 步骤类型：信息检索 |
| `status="running"` | 正在运行 |
| `status="completed"` | 已完成 |
| `stats.results_count` | 结果数量 |
| `stats.sources_count` | 来源数量 |

前端会将 `results_count` 转为 `resultsCount`，将 `sources_count` 转为 `sourcesCount`。

### 9.3 右侧详情面板

前端应将 `search_results` 放入搜索详情：

| 字段 | 展示含义 |
| --- | --- |
| `title` | 结果标题 |
| `source` | 来源类型或站点 |
| `url` | 来源链接 |
| `snippet` | 摘要片段 |
| `date` | 发布时间或抓取时间 |

当前前端会将搜索详情聚合到 `ResearchDetail` 的 `searchResults`，并在深度研究模式下展示到右侧详情面板。

### 9.4 检查点恢复

检查点 UI 状态应包含：

| 字段 | 用途 |
| --- | --- |
| `research_steps` | 恢复步骤条 |
| `search_results` | 恢复搜索结果详情 |
| `knowledge_graph` | 恢复知识图谱 |
| `charts` | 后续阶段使用 |
| `streaming_report` | 后续阶段使用 |
| `references` | 恢复引用来源 |

## 10. 来源可信度规则

当前提示词定义的来源评分区间：

| 来源类型 | 建议评分 |
| --- | --- |
| 官方来源：政府、央企等 | 0.9-1.0 |
| 学术来源：论文、研究机构 | 0.8-0.95 |
| 权威媒体：央媒、财经媒体 | 0.7-0.85 |
| 行业报告：券商、咨询机构 | 0.7-0.9 |
| 一般新闻 | 0.5-0.7 |
| 自媒体 | 0.2-0.5 |

产品约束：

1. 事实必须记录可信度分数。
2. 后续报告引用时应优先使用高可信度来源。
3. 低可信度来源不能单独支撑关键结论。
4. 若来源类型无法识别，应使用保守分值。

## 11. 去重与质量控制

### 11.1 事实去重

当前实现通过事实内容中的数字和关键词生成指纹，用于判断重复事实。产品上要求：

- 相同事实不应重复进入 `facts`。
- 不同来源支持同一事实时，应保留来源差异或用于交叉验证，而不是简单丢失证据链。
- 同一来源中更详细的事实可以保留。

### 11.2 搜索预算

当前实现包含搜索预算配置：

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `DR_V2_MAX_DEEP_SEARCH_CALLS` | 8 | 最大深度搜索调用次数 |
| `DR_V2_MAX_DEEP_SEARCH_DEPTH` | 1 | 最大递归深度 |

产品要求：

- 递归搜索必须受预算限制。
- 优先执行 `source_tracing_queries`，再执行 `follow_up_queries`。
- 预算耗尽时应停止递归，不影响已收集事实。

## 12. 非功能需求

### 12.1 可追踪性

每条事实应能追溯到来源 URL 或本地文档片段。

### 12.2 可解释性

搜索阶段应通过 `thought/action/search_progress/observation` 展示执行过程，避免用户看到黑盒等待。

### 12.3 稳定性

搜索 API 失败、本地知识库不可用、网页读取失败时，系统应记录错误并继续处理其他可用查询。

### 12.4 扩展性

搜索结果格式应兼容网络、本地知识库、实时数据 API 和后续更多来源。

### 12.5 性能

DeepScout 是当前链路中最需要实时输出的阶段。产品上要求搜索过程中持续输出进度，避免用户认为任务卡死。

## 13. 验收标准

### 13.1 功能验收

| 编号 | 验收项 | 验收标准 |
| --- | --- | --- |
| B1 | 阶段启动 | SSE 中出现 `type=phase, phase=researching` |
| B2 | 步骤运行态 | SSE 中出现 `type=research_step, step_type=searching, status=running` |
| B3 | 章节读取 | 只处理 `outline.status=pending` 的章节 |
| B4 | 搜索模式 | `search_web/search_local` 控制实际搜索路径 |
| B5 | 默认回退 | 两种搜索都关闭时自动启用网络搜索 |
| B6 | 搜索进度 | 每个查询完成后输出 `search_progress` |
| B7 | 搜索结果 | 输出 `search_results`，前端详情面板可展示 |
| B8 | 事实抽取 | 成功搜索后 `state.facts.length > 0` |
| B9 | 来源可信度 | 每条事实包含 `credibility_score` |
| B10 | 数据点抽取 | 搜索结果中存在数据时写入 `data_points` |
| B11 | 假设更新 | 存在 `hypothesis_evidence` 时更新假设状态 |
| B12 | 步骤完成态 | SSE 中出现 `research_step searching completed` |
| B13 | 统计字段 | 完成事件包含 `results_count` 和 `sources_count` |
| B14 | 检查点 | 搜索结束后保存检查点 |

### 13.2 异常验收

| 场景 | 预期 |
| --- | --- |
| 没有待研究章节 | 记录日志并返回，不误报搜索成功 |
| 网络搜索 API 超时 | 当前查询返回空结果，继续其他查询 |
| Bocha API 非 200 | 记录错误，返回空结果 |
| 本地知识库不可用 | 记录 warning，返回空结果 |
| embedding 生成失败 | 本地搜索返回空结果 |
| LLM 分析失败 | 不写入无效事实 |
| 事实重复 | 去重，不重复写入事实库 |
| 用户取消任务 | Graph 返回 `research_cancelled`，不继续后续阶段 |

### 13.3 典型案例

以下案例用于说明阶段契约，不代表一次真实线上运行结果。

#### 13.3.1 输入

来自 Step 1 的状态摘要：

```json
{
  "query": "研究 2024-2026 中国 AI 芯片市场格局、主要玩家、技术趋势和投资风险。",
  "phase": "researching",
  "search_web": true,
  "search_local": false,
  "outline": [
    {
      "id": "sec_1",
      "title": "市场规模与增长趋势",
      "search_queries": [
        "2024 中国 AI 芯片 市场规模 报告",
        "2025 中国 AI 加速芯片 增长率"
      ],
      "status": "pending"
    }
  ],
  "facts": [],
  "data_points": [],
  "pending_search_queries": []
}
```

#### 13.3.2 调用链与方案

##### 13.3.2.1 进入研究阶段：把规划大纲转成搜索任务

**当前行为**：Graph 设置 `state["phase"]="researching"`，调用 `DeepScout.process(state)`。

**目标**：明确系统已经从规划阶段进入资料收集阶段，开始根据 Step1 的大纲和搜索词获取外部或本地信息。

**作用**：这是 Research 阶段的路由信号。DeepScout 的职责是补充事实、来源、数据点和实体线索，而不是生成报告正文。

##### 13.3.2.2 选择待研究章节：控制每轮搜索范围

**当前行为**：DeepScout 读取 `outline` 中 `status="pending"` 的章节，每轮最多处理 3 个章节。

**目标**：从大纲中选择当前需要搜索的章节，并控制单轮搜索任务规模。

**作用**：限制每轮最多 3 个章节可以避免搜索任务爆炸，也让前端能够看到分批推进的研究进度。

**当前限制**：`pending` 只表示章节未处理，不等于优先级最高。后续应结合 `priority`、用户关注点、缺口严重程度和 Review 反馈决定处理顺序。

##### 13.3.2.3 执行章节搜索词：把章节问题转成具体检索请求

**当前行为**：对 `sec_1.search_queries` 逐个执行搜索。

**目标**：把 ChiefArchitect 生成的章节搜索词逐条发送给搜索工具，获取与章节目标相关的候选资料。

**作用**：`search_queries` 是 Step1 和 Step2 的连接点。搜索词质量直接决定资料覆盖度、来源质量和后续事实抽取质量。

**当前限制**：当前按搜索词顺序执行，不一定会根据搜索结果质量动态改写 query。后续可增加 query rewriting、去重和搜索意图分类。

##### 13.3.2.4 执行 Web 搜索：获取互联网来源

**当前行为**：因 `search_web=true`，调用 `_execute_search(query)`，当前实现使用 Bocha Web Search API。

**目标**：从互联网搜索结果中获取报告、新闻、官网、研究机构等公开资料。

**作用**：Web 搜索是当前事实来源的主要入口。它为后续 `_analyze_search_results()` 提供标题、URL、摘要和内容片段。

**当前限制**：Web 搜索返回的是候选结果，不等于事实已经验证。搜索结果排序、摘要质量、来源可信度和时效性都需要后续判断。

##### 13.3.2.5 按需执行本地检索：补充私有知识库材料

**当前行为**：因 `search_local=false`，本轮不调用 `_execute_local_search()`；如果为 true，则通过 Milvus 向量检索本地知识库。

**目标**：在需要时从本地资料库检索已有文档、内部报告或历史研究结果。

**作用**：本地检索可以补充 Web 搜索没有覆盖的私有材料，也能降低重复联网搜索成本。

**当前限制**：本案例没有启用本地检索。即使启用，向量检索结果也需要和 Web 来源一样进行来源、时效、相关性和可引用性判断。

##### 13.3.2.6 发送搜索进度：让用户看到增量检索过程

**当前行为**：搜索结果返回后，发送 `search_progress` 和增量 `search_results`。

**目标**：把搜索执行状态和部分结果实时传给前端。

**作用**：这一步提升可观测性。用户可以看到系统正在查什么、查到了哪些来源，而不是等全部搜索结束才看到结果。

**当前限制**：前端展示搜索结果不代表这些结果已经进入事实库。它们仍需经过抽取、去重和可信度判断。

##### 13.3.2.7 抽取结构化研究材料：把搜索结果转成事实和数据

**当前行为**：DeepScout 调用 `_analyze_search_results()`，通过 LLM 把搜索结果抽取为 `extracted_facts/data_points/entities_discovered/key_insights/follow_up_queries/source_tracing_queries`。

**目标**：从原始搜索结果中提取后续阶段可用的结构化材料。

**作用**：

1. `extracted_facts` 进入事实库，支撑写作和审核。
2. `data_points` 提供可分析数据。
3. `entities_discovered` 为知识图谱提供节点和关系线索。
4. `key_insights` 为后续报告提供分析观点。
5. `follow_up_queries/source_tracing_queries` 用于发现资料缺口和追踪源头。

**当前限制**：该抽取依赖 LLM，可能漏抽、误抽或把搜索摘要中的不确定描述写成确定事实。后续应增加来源片段、置信度、原文引用和抽取校验。

##### 13.3.2.8 写入研究状态：去重并沉淀事实、数据和图谱

**当前行为**：系统对事实做指纹去重，把数据点写入 `state["data_points"]`，把实体关系写入 `knowledge_graph`。

**目标**：把本轮搜索得到的结构化材料合并到全局 `ResearchState`，供 Step3-Step6 继续使用。

**作用**：这是 Step2 的核心产物沉淀。后续 DataAnalyst、CodeWizard、LeadWriter 和 CriticMaster 都会消费这些 facts/data_points/knowledge_graph。

**当前限制**：指纹去重主要解决重复文本问题，不能识别语义重复、来源冲突、口径冲突或数据过期。后续需要更强的 fact lineage 和 conflict resolution。

##### 13.3.2.9 触发深度追踪：在预算内继续补充关键缺口

**当前行为**：如果 LLM 返回 `source_tracing_queries` 或 `follow_up_queries`，且未超过搜索预算，则进入深度搜索追踪。

**目标**：对重要但尚未充分支撑的问题继续搜索，追踪更权威的来源或补齐缺失信息。

**作用**：这是 DeepScout 从普通搜索升级为深度研究的关键机制。它能让系统不止满足于第一轮搜索结果，而是沿着缺口继续追问。

**当前限制**：是否继续追踪仍依赖 LLM 给出的 follow-up 判断和预算限制。若 LLM 漏掉关键缺口，系统可能不会继续搜索；若 LLM 过度追踪，也可能浪费搜索预算。

#### 13.3.3 输出

状态写入示例：

```json
{
  "facts": [
    {
      "id": "fact_8a12cdef",
      "content": "多家行业报告将 AI 加速芯片需求增长归因于大模型训练和推理工作负载增加。",
      "source_url": "https://example.com/ai-chip-report",
      "source_name": "示例行业报告",
      "source_type": "report",
      "credibility_score": 0.78,
      "related_sections": ["sec_1"],
      "verified": false
    }
  ],
  "data_points": [
    {
      "id": "dp_3f9a1b2c",
      "name": "中国 AI 芯片市场规模",
      "value": "示例值",
      "unit": "亿元",
      "year": 2024,
      "source": "示例行业报告",
      "confidence": 0.78
    }
  ],
  "knowledge_graph": {
    "nodes": [
      {"id": "ai_chip", "name": "AI 芯片", "type": "technology"}
    ],
    "edges": [
      {"source": "ai_chip", "target": "large_model", "relation": "支撑"}
    ]
  },
  "insights": [
    "推理侧需求增长是 AI 芯片市场扩张的重要线索。"
  ]
}
```

前端事件示例：

```json
{
  "type": "search_results",
  "content": {
    "results": [
      {
        "id": "sr_a1b2c3",
        "title": "AI 芯片市场规模报告摘要",
        "link": "https://example.com/ai-chip-report",
        "content": "报告摘要片段..."
      }
    ],
    "isIncremental": true,
    "searchType": "web"
  }
}
```

#### 13.3.4 验收点

- 每条事实必须有 `content/source_name/source_url/credibility_score/related_sections`。
- 数据点必须保留来源和年份，不能把不确定数值伪装成确定值。
- 搜索结果应能在前端详情面板显示。
- `follow_up_queries` 只能在预算内触发深度搜索。
- 本阶段输出必须足以支撑 DataAnalyst 和 LeadWriter 消费。

## 14. 当前代码依据

| 能力 | 代码位置 |
| --- | --- |
| 阶段状态与全局字段 | `backend/app/service/deep_research_v2/state.py` |
| Step 2 阶段编排 | `backend/app/service/deep_research_v2/graph.py` |
| DeepScout 主处理逻辑 | `backend/app/service/deep_research_v2/agents/scout.py:process` |
| 网络搜索 | `backend/app/service/deep_research_v2/agents/scout.py:_execute_search` |
| 本地知识库搜索 | `backend/app/service/deep_research_v2/agents/scout.py:_execute_local_search` |
| 搜索结果分析 | `backend/app/service/deep_research_v2/agents/scout.py:_analyze_search_results` |
| 搜索结果事件 | `backend/app/service/deep_research_v2/agents/scout.py:_emit_search_results_event` |
| 事实去重 | `backend/app/service/deep_research_v2/agents/scout.py:_is_duplicate_fact` |
| 知识图谱更新 | `backend/app/service/deep_research_v2/agents/scout.py:_update_knowledge_graph` |
| 假设状态更新 | `backend/app/service/deep_research_v2/agents/scout.py:_update_hypothesis_status` |
| 请求入口与取消接口 | `backend/app/router/research_router.py` |
| 前端 SSE 消费 | `frontend/src/pages/chat/index.tsx` |
| 前端详情面板 | `frontend/src/pages/chat/component/research-detail/index.tsx` |

## 15. 边界与不做范围

本阶段不负责：

1. 对数据点做统计建模。
2. 生成 ECharts 图表。
3. 运行 Python 代码。
4. 撰写最终报告。
5. 执行质量审稿。
6. 根据质量评分决定是否返工。

## 16. 后续需求变更候选

这些需求不属于当前反推范围，但建议作为后续版本演进候选。

### 16.1 来源分级过滤

允许用户选择来源偏好：

- 仅官方来源。
- 官方 + 学术 + 行业报告。
- 包含新闻媒体。
- 排除自媒体。

### 16.2 事实冲突检测

当多个来源对同一指标给出不同数值时，系统应：

- 标记冲突。
- 展示冲突来源。
- 优先选择可信度更高或时间更新的来源。
- 将冲突交给后续 Critic 或用户确认。

### 16.3 引用链追踪

对来源中的“据某机构统计”等二手引用自动追溯：

- 查找原始数据源。
- 标记一手/二手/三手来源。
- 报告默认引用一手来源。

### 16.4 搜索预算可配置

用户或系统可配置：

- 每个章节最大搜索词数量。
- 每个搜索词最大结果数。
- 最大递归深度。
- 最大 API 调用次数。
- 是否允许慢速深读网页。

### 16.5 人工来源管理

用户可在搜索结果中：

- 收藏来源。
- 排除来源。
- 标记来源可信或不可信。
- 手动上传补充来源。

### 16.6 本地知识库增强

本地搜索可增强为：

- 按知识库选择范围。
- 展示命中文档名、页码、段落位置。
- 对本地来源也计算可信度或内部权威等级。

### 16.7 搜索结果到大纲的覆盖度反馈

DeepScout 应输出每个章节的信息覆盖情况：

- 已充分。
- 信息不足。
- 来源不足。
- 数据不足。
- 需要补充搜索。

该信息可作为 Step 3 和 Critic 阶段的重要输入。

## 17. 待确认问题

1. 搜索阶段是否允许用户实时暂停某个章节搜索？
2. 低可信度来源是否应该默认进入事实库，还是只进入候选区？
3. 本地知识库搜索是否需要严格按 `kb_name` 限定范围？
4. 事实冲突应在 Step 2 解决，还是交给 Critic 阶段？
5. 搜索结果是否需要支持用户手动编辑后再进入后续阶段？
6. 搜索预算应由系统自动控制，还是暴露给高级用户？
