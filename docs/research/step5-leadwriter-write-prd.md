# Step 5 PRD: LeadWriter Write

## 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 阶段 | Step 5: LeadWriter - 报告写作阶段 |
| 所属产品 | AI 深度研究助手 |
| 文档类型 | 基于当前代码反推的产品 PRD |
| 当前状态 | Draft |
| 覆盖范围 | 从大纲、事实、数据点、洞察、图表到章节草稿、完整报告、引用列表、审核后文字修订 |
| 不覆盖范围 | 搜索、数据抽取、代码执行、质量审稿、最终是否通过审核 |
| 主要代码依据 | `backend/app/service/deep_research_v2/agents/writer.py`, `backend/app/service/deep_research_v2/state.py`, `backend/app/service/deep_research_v2/graph.py`, `frontend/src/pages/chat/index.tsx`, `frontend/src/pages/chat/component/research-detail/process-report.tsx` |

## 2. 产品背景

前几个阶段已经生成研究计划、事实证据、数据点、知识图谱和图表，但这些内容还不是用户最终需要的研究成果。用户需要的是一份结构完整、逻辑连贯、可引用、可阅读的 Markdown 深度研究报告。

LeadWriter 是写作阶段的核心 Agent，负责把碎片化材料组织成章节草稿，再把章节整合成完整报告。它需要同时兼顾专业表达、证据引用、图表嵌入、格式规范和后续可审稿性。

当前实现中，LeadWriter 有两种工作模式：

- `phase="writing"`：首次撰写报告。
- `phase="revising"`：根据 CriticMaster 的审核反馈修订报告。

因此本 PRD 以首次写作为主，同时覆盖 Review 后的文字修订闭环。

## 3. 问题定义

### 3.1 用户问题

用户希望系统最终输出一份可以直接阅读和继续编辑的深度研究报告，而不是一堆事实、数据和图表。

### 3.2 产品需要解决的问题

系统需要在写作阶段完成：

- 按研究大纲逐章节撰写正文。
- 为每个章节选择相关事实、数据点、洞察和图表。
- 在正文中使用可点击引用链接。
- 使用 Markdown 形成专业报告结构。
- 收集并整理参考文献。
- 发送章节内容供前端过程报告实时展示。
- 生成完整报告，包括执行摘要、章节正文、结论展望和参考文献。
- 审核失败后按反馈修订报告。

### 3.3 成功定义

LeadWriter 阶段成功的标志是：

- `draft_sections` 至少包含一个章节草稿。
- 每个已写章节状态更新为 `drafted`。
- `final_report` 包含完整 Markdown 报告。
- `references` 包含可用于前端展示的引用来源。
- 前端能收到 `section_content` 和 `report_draft` 事件。
- 写作完成后阶段切换为 `reviewing`。
- 修订完成后能发送 `revision_complete` 并回到 `reviewing`。

## 4. 目标用户与使用场景

### 4.1 目标用户

- 行业研究人员：需要结构化、可引用的行业研究报告。
- 咨询和投研用户：需要专业语气、结论明确、图文结合的分析材料。
- 企业知识工作者：需要把搜索和知识库结果整理成内部报告。

### 4.2 核心场景

**场景 A：首次报告生成**

系统完成规划、搜索和分析后进入写作阶段。LeadWriter 逐章节撰写内容，再合成为完整报告。

**场景 B：图文混排**

Analyze 阶段生成图表后，LeadWriter 在章节中按 `![图表标题](chart_id)` 格式插入图表引用，前端报告组件再尝试匹配图表并内联展示。

**场景 C：引用整理**

章节写作产生的 `citations` 和事实来源被汇总到 `references`，完整报告末尾生成参考文献。

**场景 D：审核后修订**

CriticMaster 发现问题但不需要补充搜索时，Graph 设置 `phase="revising"`。LeadWriter 根据未解决反馈修订 `final_report`，标记已解决问题并回到审核阶段。

## 5. 产品目标

### 5.1 当前阶段目标

LeadWriter 首次写作应完成以下目标：

1. 只在 `phase="writing"` 时进入首次写作流程。
2. 发送 `research_step` running 事件，标记内容生成开始。
3. 发送 `thought` 事件说明开始写作。
4. 遍历 `outline`，为非 `final/drafted` 章节生成正文。
5. 为章节收集相关事实；无章节关联时回退使用前 10 条事实。
6. 为章节收集前 10 条数据点。
7. 为章节收集前 5 条洞察。
8. 为章节收集匹配 `section_id` 的图表信息。
9. 调用 LLM 生成章节正文、要点、引用和改进建议。
10. 写入 `draft_sections[section_id]`。
11. 将章节状态改为 `drafted`。
12. 追加章节引用到 `references`。
13. 发送 `section_content` 事件。
14. 发送章节完成 `observation`。
15. 汇总章节内容和来源，调用 LLM 合成完整报告。
16. 写入 `final_report`。
17. 追加合成阶段返回的参考文献。
18. 发送 `report_draft` 事件。
19. 发送 `research_step` completed 事件。
20. 将阶段切换为 `reviewing`。

### 5.2 修订目标

LeadWriter 修订流程应完成：

1. 只在 `phase="revising"` 时执行修订流程。
2. 收集 `critic_feedback` 中未解决的问题。
3. 收集最新事实作为补充信息。
4. 调用 LLM 输出 `revised_content/changes_made/addressed_issues/unable_to_address`。
5. 用 `revised_content` 覆盖 `final_report`。
6. 标记已解决 issue。
7. 发送 `revision_complete` 事件。
8. 将阶段切换回 `reviewing`。

### 5.3 非目标

LeadWriter 不负责：

- 发现新的事实来源。
- 判断事实是否真实。
- 生成或执行图表代码。
- 决定报告是否通过质量门。
- 管理审核循环终止条件。

## 6. 功能范围

### 6.1 Must Have

1. 按 `outline` 逐章节写作。
2. 支持章节级素材收集。
3. 支持 Markdown 正文输出。
4. 支持可点击引用格式 `[来源名称](URL)`。
5. 支持图表引用格式 `![图表标题](chart_id)`。
6. 支持章节草稿写入 `draft_sections`。
7. 支持完整报告合成。
8. 支持参考文献整理。
9. 支持 `section_content` 事件流。
10. 支持 `report_draft` 事件流。
11. 支持审核后修订。
12. 支持修订完成事件。

### 6.2 Should Have

1. 每个章节正文建议 500-1000 字。
2. 报告应包含执行摘要。
3. 报告应包含结论与展望。
4. 标题编号应保持层级清晰。
5. 不应重复章节标题。
6. 数据和事实观点应尽量带来源链接。
7. 合成失败时应使用章节内容生成备选报告。

### 6.3 Could Have

1. 支持按章节字数预算动态调节。
2. 支持引用去重和排序。
3. 支持脚注式引用。
4. 支持报告模板选择。
5. 支持人工编辑后再进入 Review。

## 7. 输入输出契约

### 7.1 上游输入

| 字段 | 类型 | 来源 | 用途 |
| --- | --- | --- | --- |
| `query` | string | 用户问题 | 报告主题 |
| `phase` | string | Graph/CriticMaster | 写作或修订判断 |
| `outline` | array | ChiefArchitect | 报告章节结构 |
| `facts` | array | DeepScout | 事实和引用素材 |
| `data_points` | array | DataAnalyst/CodeWizard | 数据支撑 |
| `insights` | array | DataAnalyst | 洞察素材 |
| `charts` | array | DataAnalyst/CodeWizard | 图表素材 |
| `references` | array | DeepScout/LeadWriter | 来源列表 |
| `critic_feedback` | array | CriticMaster | 修订反馈 |
| `final_report` | string | LeadWriter | 修订输入 |

### 7.2 章节输入

每个章节至少应包含：

```json
{
  "id": "sec_1",
  "title": "市场概况",
  "description": "分析市场规模与增长趋势",
  "section_type": "quantitative",
  "status": "pending",
  "requires_chart": true
}
```

字段要求：

- `id` 必须唯一，用作 `draft_sections` key。
- `title` 必须适合作为报告标题。
- `description` 用于指导章节写作。
- `section_type` 可为 `qualitative/quantitative/mixed`。
- `status` 为 `final` 或 `drafted` 时首次写作跳过。

### 7.3 章节写作输出

LLM 应返回：

```json
{
  "content": "章节正文内容（Markdown，不包含章节标题）",
  "key_points": ["核心要点1", "核心要点2"],
  "citations": [
    {
      "source": "艾瑞咨询",
      "url": "https://example.com/report"
    }
  ],
  "suggested_improvements": ["可补充更多竞品数据"]
}
```

系统写入：

```json
{
  "draft_sections": {
    "sec_1": "章节正文内容"
  },
  "outline[sec_1].status": "drafted"
}
```

### 7.4 完整报告输出

LLM 合成阶段应返回：

```json
{
  "executive_summary": "执行摘要",
  "full_report": "完整 Markdown 报告",
  "conclusions": ["核心结论1"],
  "outlook": "未来展望",
  "references": [
    {
      "id": 1,
      "title": "来源标题",
      "url": "https://example.com",
      "author": "机构",
      "date": "2026"
    }
  ]
}
```

报告结构建议：

```markdown
## 执行摘要

...

---

## 1 市场概况

### 1.1 市场规模

...

---

## 结论与展望

### 核心结论

1. ...

### 未来展望

...

---

## 参考文献

1. [来源标题](URL) - 作者/机构, 日期
```

### 7.5 修订输出

修订阶段应返回：

```json
{
  "revised_content": "修订后的完整报告",
  "changes_made": ["补充了市场规模来源"],
  "addressed_issues": ["issue_1234"],
  "unable_to_address": ["缺少公开数据，无法验证"]
}
```

## 8. 写作流程

### 8.1 阶段进入流程

1. Graph 发送 `phase` 事件：`phase="writing"`。
2. Graph 设置 `state["phase"] = "writing"`。
3. Graph 调用 `LeadWriter.process(state)`。
4. LeadWriter 根据 `phase` 进入 `_write_report()`。

### 8.2 章节写作流程

1. 发送 `research_step` running。
2. 发送 `thought`：开始撰写深度研究报告。
3. 遍历 `outline`。
4. 跳过 `status in ["final", "drafted"]` 的章节。
5. 针对章节收集关联事实。
6. 无关联事实时回退到前 10 条事实。
7. 格式化事实、数据点、洞察和图表信息。
8. 调用 LLM 生成章节内容。
9. 如果 `content` 存在，写入 `draft_sections`。
10. 更新章节状态为 `drafted`。
11. 把 citations 追加到 `references`。
12. 发送 `section_content` 事件。
13. 发送 `observation` 事件。

### 8.3 完整报告合成流程

1. 发送 `thought`：正在整合各章节。
2. 从 `draft_sections` 汇总章节内容。
3. 汇总 `references` 和 `facts` 来源。
4. 调用 LLM 生成执行摘要、完整报告、结论、展望、参考文献。
5. 如果 `full_report` 存在，写入 `state["final_report"]`。
6. 追加新参考文献。
7. 如果解析失败，使用章节内容生成备选报告。
8. 发送 `report_draft` 事件。
9. 发送 `research_step` completed。
10. 设置 `phase="reviewing"`。

### 8.4 修订流程

1. Graph 或 CriticMaster 设置 `phase="revising"`。
2. LeadWriter 收集未解决 `critic_feedback`。
3. 收集最新 5 条事实作为新信息。
4. 调用 LLM 修订报告。
5. 如果有 `revised_content`，覆盖 `final_report`。
6. 根据 `addressed_issues` 标记反馈 resolved。
7. 发送 `revision_complete`。
8. 设置 `phase="reviewing"`。

## 9. 事件与前端展示需求

### 9.1 写作阶段事件

Graph 发送：

```json
{
  "type": "phase",
  "phase": "writing",
  "content": "开始撰写报告..."
}
```

LeadWriter 开始发送：

```json
{
  "type": "research_step",
  "content": {
    "step_type": "writing",
    "title": "内容生成",
    "subtitle": "撰写研究报告",
    "status": "running",
    "stats": {
      "sections_count": 5,
      "word_count": 0
    }
  }
}
```

### 9.2 章节内容事件

```json
{
  "type": "section_content",
  "content": {
    "agent": "LeadWriter",
    "section_id": "sec_1",
    "section_title": "市场概况",
    "content": "完整章节内容",
    "word_count": 1200,
    "key_points": ["市场规模扩大", "竞争加剧"]
  }
}
```

前端应：

- 自动创建或选中 `writing` 详情。
- 把章节内容加入 `detail.sections`。
- 在过程报告 tab 实时展示章节。

### 9.3 报告草稿事件

```json
{
  "type": "report_draft",
  "content": {
    "agent": "LeadWriter",
    "content": "完整报告",
    "executive_summary": "执行摘要",
    "conclusions": ["结论1"],
    "word_count": 8000,
    "references_count": 12
  }
}
```

前端应：

- 写入 `detail.streamingReport`。
- 在 report tab 展示完整报告。
- 与 `charts` 和 `knowledgeGraph` 结合渲染图文报告。

### 9.4 写作完成事件

```json
{
  "type": "research_step",
  "content": {
    "step_type": "writing",
    "title": "内容生成",
    "subtitle": "撰写研究报告",
    "status": "completed",
    "stats": {
      "sections_count": 5,
      "word_count": 8000,
      "references_count": 12
    }
  }
}
```

### 9.5 修订事件

```json
{
  "type": "revision_complete",
  "content": {
    "agent": "LeadWriter",
    "changes_count": 3,
    "addressed_issues": ["issue_1234"],
    "unable_to_address": []
  }
}
```

前端应：

- 更新当前报告内容。
- 标记修订阶段完成。
- 保留审核反馈与修订记录供用户追踪。

## 10. 报告格式规则

### 10.1 标题规则

- 完整报告开头不要使用 `#` 一级标题。
- 从 `## 执行摘要` 开始。
- 正文一级章节使用 `## 1 章节标题`。
- 子章节使用 `### 1.1 子章节标题`。
- 三级标题可使用 `#### 1.1.1 三级标题`。
- 标题不得重复。

### 10.2 引用规则

- 行内引用使用 `[来源名称](URL)`。
- 数据引用应尽量紧跟数据后。
- 文末参考文献使用有序列表。
- URL 为空时不应伪造链接。

### 10.3 图表规则

- 图表引用使用 `![图表标题](chart_id)`。
- 图表标题应能与 `charts.title` 匹配。
- 如果图表无法匹配，前端可以按章节位置插入未使用图表。

### 10.4 风格规则

- 使用专业行业研究报告风格。
- 避免泛泛而谈的开头。
- 关键观点需要事实或数据支撑。
- 避免在正文开头重复章节标题。

## 11. 非功能需求

### 11.1 可追踪性

章节正文、完整报告、引用和修订记录都应进入状态或事件，便于前端展示和后续审稿。

### 11.2 可读性

Markdown 应能直接在前端渲染，避免输出破碎 JSON 或未闭合格式。

### 11.3 稳定性

合成阶段 JSON 解析失败时，系统应使用章节内容生成备选报告。

### 11.4 可审稿性

写作结果必须保留 `draft_sections` 和 `references`，CriticMaster 可基于这些材料审查。

### 11.5 性能

章节写作和合成都设置较高 token 上限，但仍应只传必要事实、数据点和来源摘要。

## 12. 验收标准

### 12.1 功能验收

1. `phase="writing"` 时，LeadWriter 能执行首次写作。
2. 每个 pending 章节生成后写入 `draft_sections`。
3. 已写章节状态变为 `drafted`。
4. 章节写作成功时发送 `section_content`。
5. 完整报告合成成功时写入 `final_report`。
6. 合成成功时发送 `report_draft`。
7. 写作完成后发送 `research_step` completed。
8. 写作完成后 `phase` 变为 `reviewing`。
9. 修订阶段能读取未解决反馈。
10. 修订成功后覆盖 `final_report` 并发送 `revision_complete`。

### 12.2 异常验收

1. 某章节没有关联事实时，使用全局事实回退。
2. 某章节没有数据点或图表时，仍能生成文字章节。
3. 章节写作 LLM 返回空内容时，不写入空草稿。
4. 合成报告 LLM JSON 解析失败时，生成备选报告。
5. 修订 LLM 未返回 `revised_content` 时，不覆盖现有报告。
6. `addressed_issues` 中找不到对应反馈时，不抛异常。

### 12.3 典型案例

以下案例用于说明阶段契约，不代表一次真实线上运行结果。

#### 12.3.1 输入

来自前序阶段的状态摘要：

```json
{
  "query": "研究 2024-2026 中国 AI 芯片市场格局、主要玩家、技术趋势和投资风险。",
  "phase": "writing",
  "outline": [
    {
      "id": "sec_1",
      "title": "市场规模与增长趋势",
      "description": "分析市场规模、增速和需求来源。",
      "section_type": "quantitative",
      "status": "pending"
    }
  ],
  "facts": [
    {
      "content": "示例行业报告称，AI 芯片需求受大模型推理部署拉动。",
      "source_name": "示例行业报告",
      "source_url": "https://example.com/ai-chip-report",
      "credibility_score": 0.78,
      "related_sections": ["sec_1"]
    }
  ],
  "data_points": [
    {"name": "中国 AI 芯片市场规模", "value": 500, "unit": "亿元", "year": 2024}
  ],
  "insights": [
    "推理侧需求增长是市场扩张的重要线索。"
  ],
  "charts": [
    {"id": "chart_market_trend", "title": "中国 AI 芯片市场增长趋势", "section_id": "sec_1"}
  ],
  "draft_sections": {},
  "references": []
}
```

#### 12.3.2 调用链与方案

##### 12.3.2.1 进入写作阶段：把流程从分析产物转为报告产物

**当前行为**：Graph 发送 `phase="writing"`，设置 `state["phase"]="writing"`。

**目标**：明确告诉系统前序 Research/Analyze 阶段已经结束，当前任务从“继续收集和分析信息”切换为“生成可阅读报告”。

**作用**：这是写作阶段的路由信号。LeadWriter 只应在 `writing` 或 `revising` 阶段处理内容，避免在搜索或分析阶段提前生成报告。

##### 12.3.2.2 启动 LeadWriter：建立章节写作任务上下文

**当前行为**：LeadWriter 进入 `_write_report()`，发送 `research_step` running。

**目标**：初始化本轮写作任务，并向前端或事件流说明“报告撰写正在进行”。

**作用**：让用户看到系统已经从数据处理转入写作，同时为后续章节内容、报告草稿和完成事件建立统一上下文。

##### 12.3.2.3 遍历大纲章节：确定哪些章节需要生成

**当前行为**：`_write_section()` 遍历 `outline`，跳过 `final/drafted` 章节。

**目标**：按 ChiefArchitect 规划的大纲逐章写作，并避免重复生成已经完成或已确认的章节。

**作用**：`outline` 是 Step5 的结构主轴。LeadWriter 不应该自由决定报告结构，而应该沿用 Step1 生成的大纲，把上游素材填入对应章节。

**当前限制**：当前跳过逻辑主要依赖章节 `status`。如果章节状态维护不准确，可能出现应写未写、已写重复写或旧章节未刷新等问题。

##### 12.3.2.4 收集章节事实：为当前章节准备证据素材

**当前行为**：对 `sec_1` 收集 `related_sections` 包含当前 `section_id` 的事实；如果没有关联事实，则回退到前 10 条事实。

**目标**：为当前章节提供事实依据，避免章节正文完全依赖模型自由发挥。

**作用**：事实素材决定章节能否写出有来源支撑的判断。相关事实会进入 `SECTION_WRITING_PROMPT`，供 LLM 生成带引用的段落。

**当前限制**：回退到前 10 条事实只是兜底策略，不代表这些事实与章节真正相关。后续应使用章节级 Evidence Pack 替代“相关事实 + 前 N 条回退”。

##### 12.3.2.5 收集数据、洞察和图表：把分析产物转成章节写作素材

**当前行为**：收集前 10 条 `data_points`、前 5 条 `insights` 和匹配 `section_id` 的图表。

**目标**：让章节不仅有事实叙述，也能包含数据支撑、分析洞察和图表引用。

**作用**：

1. `data_points` 支撑数字、规模、趋势等表述。
2. `insights` 提供分析性观点。
3. `charts` 让报告正文可以引用已有可视化结果。

**当前限制**：前 10 条数据点和前 5 条洞察是截断策略，不等于最相关、最新或最可信。图表匹配也主要依赖 `section_id`，缺少对图表数据和正文解释的一致性校验。

##### 12.3.2.6 调用章节写作模型：生成章节正文、要点和引用

**当前行为**：通过 `SECTION_WRITING_PROMPT` 调用 LLM，要求输出章节正文、要点和引用。

**目标**：把当前章节的大纲说明、事实、数据点、洞察和图表整理成自然语言章节草稿。

**作用**：这是 Step5 的核心生成动作。它把上游结构化/半结构化材料转为用户可阅读的 Markdown 文本。

**当前限制**：LLM 可能改写数字、弱化来源、引入未提供的新判断，或者生成不存在的图表引用。后续应要求章节输出同时包含 claim ledger，用于 Step6 审核。

##### 12.3.2.7 写入章节草稿：把生成结果保存为可复用状态

**当前行为**：写入 `draft_sections["sec_1"]`，并把章节状态改为 `drafted`。

**目标**：把章节生成结果从一次性 LLM 输出固化为系统状态，供完整报告合成、前端展示和后续 Review 使用。

**作用**：

1. `draft_sections` 是 `_synthesize_report()` 的输入。
2. 章节状态 `drafted` 可防止重复写作。
3. 前端可以收到 `section_content` 事件并展示章节进度。

**当前限制**：当前 `draft_sections` 主要保存 Markdown 文本，缺少结构化 claim、引用映射和图表引用映射，后续审查粒度有限。

##### 12.3.2.8 合成完整报告：把章节草稿组织成最终报告草稿

**当前行为**：`_synthesize_report()` 汇总章节内容、事实来源和引用，通过 `SYNTHESIS_PROMPT` 合成完整报告。

**目标**：将多个章节草稿统一成一份完整报告，包括执行摘要、正文、结论、展望和参考文献。

**作用**：章节写作解决“每一章怎么写”，报告合成解决“整份报告是否连贯、格式统一、可以直接阅读”。最终结果写入 `state["final_report"]`，并进入 Review 阶段。

**当前限制**：完整报告合成仍由 LLM 完成，可能改写章节内容、重新组织事实或遗漏章节细节。后续应优先采用确定性拼装章节，再让 LLM 只生成摘要和衔接句。

##### 12.3.2.9 生成 fallback 报告：保证合成失败时仍有可审查产物

**当前行为**：如果合成 JSON 解析失败，使用已有章节内容生成 fallback 报告。

**目标**：避免因为 LLM 输出格式错误导致 Step5 完全失败。

**作用**：fallback 报告至少能保留已生成章节内容，让流程继续进入 Review，由 CriticMaster 或用户发现质量问题。

**当前限制**：fallback 是稳定性兜底，不是质量保证。它可能缺少执行摘要、结论、参考文献整理和统一格式，因此应在前端或 Review 中标记为降级产物。

#### 12.3.3 输出

章节草稿示例：

```json
{
  "draft_sections": {
    "sec_1": "2024 年以来，中国 AI 芯片需求继续增长，核心驱动来自大模型推理部署和国产算力替代。根据[示例行业报告](https://example.com/ai-chip-report)，相关需求正在从训练侧扩展到推理侧。![中国 AI 芯片市场增长趋势](chart_market_trend)"
  },
  "references": [
    {
      "id": 1,
      "source": "示例行业报告",
      "url": "https://example.com/ai-chip-report"
    }
  ]
}
```

前端章节事件示例：

```json
{
  "type": "section_content",
  "content": {
    "agent": "LeadWriter",
    "section_id": "sec_1",
    "section_title": "市场规模与增长趋势",
    "content": "章节正文内容...",
    "word_count": 238,
    "key_points": ["推理需求拉动增长", "国产替代是重要变量"]
  }
}
```

完整报告事件示例：

```json
{
  "type": "report_draft",
  "content": {
    "agent": "LeadWriter",
    "content": "## 执行摘要\n\n...\n\n## 1 市场规模与增长趋势\n\n...",
    "executive_summary": "本报告分析 2024-2026 年中国 AI 芯片市场。",
    "conclusions": ["推理需求是主要驱动力"],
    "word_count": 3200,
    "references_count": 8
  }
}
```

#### 12.3.4 验收点

- 每个生成章节必须写入 `draft_sections`。
- 章节正文中的数据观点应尽量包含可点击来源。
- 图表引用应使用 `![图表标题](chart_id)`。
- `final_report` 必须为 Markdown 字符串。
- 写作完成后 `phase` 必须变为 `reviewing`。

## 13. 当前代码依据

- `LeadWriter.process()`：按 `WRITING/REVISING` 分发流程。
- `LeadWriter._write_report()`：发送写作步骤事件、逐章节写作、合成报告、进入审核。
- `LeadWriter._write_section()`：收集素材、调用章节写作 prompt、写入草稿、发送章节事件。
- `LeadWriter._synthesize_report()`：合成完整报告，失败时生成 fallback。
- `LeadWriter._revise_report()`：根据审核反馈修订报告，发送修订完成事件。
- `ResearchState`：定义 `draft_sections/final_report/references/critic_feedback/charts/insights`。
- `DeepResearchGraph._run_simplified()`：写作阶段和审核后的 rewriting/revising 路由。
- `frontend/src/pages/chat/index.tsx`：处理 `section_content/report_draft/revision_complete`。
- `process-report.tsx`：渲染 Markdown 报告并匹配图表。

## 14. 边界与不做范围

- LeadWriter 不主动联网，也不补充事实。
- LeadWriter 不验证事实真伪，只使用上游状态提供的素材。
- LeadWriter 不负责图表生成，只引用已有图表。
- LeadWriter 不决定报告是否最终完成。
- 修订流程只基于已有反馈和补充事实，不重新规划大纲。

## 15. 当前实现限制与专业化改造建议

本节记录当前 Step 5 的实现边界和后续专业化改造方向。以下内容不改变当前代码行为，作为后续统一处理的产品和工程依据。

Step 5 的核心不应被理解为“让 LLM 文笔更好”。它是用户最终看到研究价值的交付层，真正难点是 evidence-bound writing：基于证据包写作、关键判断可追溯、数字不失真、图表引用可校验。

### 15.1 素材选择限制

当前 `_write_section()` 会按章节收集素材：

1. 优先使用 `related_sections` 包含当前 `section_id` 的事实。
2. 如果没有关联事实，则回退到 `state["facts"][:10]`。
3. 数据点使用 `state["data_points"][:10]`。
4. 洞察使用前 5 条。
5. 图表按 `chart.section_id == section_id` 匹配。

这个策略适合 demo，但不适合严肃报告。主要风险是：

- 回退到前 10 条事实不代表事实与章节真正相关。
- 前 10 条数据点不一定是最重要、最新或最可信的数据。
- `insights` 没有强制绑定来源、章节或数据点。
- 写作 prompt 看到的是素材摘要，不是严格可审计的数据包。

专业化目标方案应引入章节级 Evidence Pack：

```json
{
  "section_id": "sec_market_size",
  "section_title": "市场规模与增长趋势",
  "allowed_fact_ids": ["fact_001", "fact_008"],
  "allowed_data_point_ids": ["dp_003", "dp_010"],
  "allowed_chart_ids": ["chart_market_trend"],
  "required_claim_ids": [],
  "forbidden_claims": ["无来源市场规模判断"],
  "writing_constraints": {
    "allow_new_facts": false,
    "allow_numeric_recalculation": false,
    "require_citation_for_key_claims": true
  }
}
```

LeadWriter 只能基于 Evidence Pack 写作，不应自由从全局 `facts/data_points/charts` 中选择素材。

### 15.2 Claim-Citation 机制缺失

当前报告主要输出 Markdown。虽然 prompt 要求引用来源，但系统没有结构化记录每个关键判断对应哪些事实、数据点或图表。

后续应在 Markdown 外同步输出 claim ledger：

```json
{
  "claims": [
    {
      "claim_id": "claim_001",
      "section_id": "sec_market_size",
      "text": "中国 AI 芯片市场在 2024 年达到 500 亿元。",
      "source_fact_ids": ["fact_001"],
      "source_data_point_ids": ["dp_003"],
      "source_chart_ids": ["chart_market_trend"],
      "confidence": 0.82
    }
  ]
}
```

这个结构的价值是：

1. CriticMaster 可以逐条审核 claim，而不是只读自然语言报告。
2. 前端可以展示段落引用依据。
3. 修订时可以判断新增、删除、改写了哪些 claim。
4. 导出报告时可以生成更可靠的参考文献和脚注。

### 15.3 数字和图表引用锁定

Step 5 不应重新计算数据，也不应改写上游数值。当前 LLM 写作可能出现：

- 把 `500 亿元` 改写为 `约 500 亿`。
- 把年份、地区或单位合并表达。
- 把多个来源的不同口径混在同一段。
- 引用不存在或不匹配的 `chart_id`。
- 用自然语言解释图表时引入图表中不存在的结论。

后续应强制以下规则：

1. 报告中的关键数字必须来自 `data_point_id` 或确定性计算结果。
2. LLM 不得新增数字、改写单位或重新计算指标。
3. 每个图表引用必须使用存在的 `chart_id`。
4. 每个图表解释必须绑定对应 `chart_id` 和 `source_data_point_ids`。
5. 图表标题、章节位置和正文解释必须一致。
6. 如果素材证据不足，LeadWriter 应输出“不足以支持该判断”，而不是补写推断。

推荐增加报告后处理校验：

```text
Markdown report
    -> extract numeric mentions
    -> match data_point_id or calculated_metric_id
    -> validate chart_id references
    -> validate cited source URLs
    -> block or flag unsupported claims
```

### 15.4 写作与合成职责拆分

当前 LeadWriter 同时承担章节写作、完整报告合成、摘要生成、参考文献整理和修订。后续可拆成更清晰的内部职责：

| 子职责 | 输入 | 输出 | 约束 |
| --- | --- | --- | --- |
| Evidence Pack Builder | outline, facts, data_points, charts | section evidence packs | 不调用自由写作 |
| Section Writer | section evidence pack | section draft + claims | 只使用允许素材 |
| Report Composer | section drafts | final_report | 不新增事实 |
| Executive Summary Writer | final_report claims | executive_summary | 只总结已出现结论 |
| Citation Normalizer | claims, references | normalized references | 去重、补齐 URL |
| Consistency Checker | report, claims, charts | validation result | 标记无来源判断 |

这样可以把“写得通顺”和“写得可信”拆开验证。

### 15.5 修订闭环限制

当前 `_revise_report()` 会读取 `critic_feedback`、最近事实和原报告片段，然后调用 LLM 生成 `revised_content`。这个机制可以形成闭环，但还不够可审计。

后续修订输出应明确：

```json
{
  "revised_content": "修订后的 Markdown",
  "changes_made": [
    {
      "issue_id": "issue_001",
      "change_type": "added_citation",
      "section_id": "sec_market_size",
      "before": "市场增长较快。",
      "after": "根据示例行业报告，市场需求受推理部署拉动。",
      "source_fact_ids": ["fact_001"]
    }
  ],
  "added_claim_ids": ["claim_009"],
  "removed_claim_ids": ["claim_004"],
  "updated_claim_ids": ["claim_001"],
  "unable_to_address": [
    {
      "issue_id": "issue_007",
      "reason": "缺少可引用来源"
    }
  ]
}
```

修订完成后，CriticMaster 应能复查：

1. 每个高优先级 issue 是否被处理。
2. 修订是否引入了新事实。
3. 新增 claim 是否有来源。
4. 数字和图表引用是否仍然一致。
5. 无法处理的问题是否被明确说明。

### 15.6 推荐优化优先级

| 优先级 | 优化项 | 目标 |
| --- | --- | --- |
| P0 | 章节级 Evidence Pack | 防止全局素材混用和无关事实进入章节 |
| P0 | 数字和图表引用锁定 | 防止报告中出现无法追溯的数字和图表解释 |
| P1 | Claim-Citation ledger | 支持 CriticMaster 做结构化审核 |
| P1 | 报告后处理校验 | 自动发现无来源 claim、错误 chart_id、数字不匹配 |
| P2 | 写作/合成/摘要/引用职责拆分 | 提升可维护性和可测试性 |
| P2 | 修订 diff 和 issue 映射 | 让用户和审核 Agent 看清楚改了什么 |

当前文档中的 LeadWriter 能力应被理解为 demo/prototype 级写作能力；面向高敏、金融、医疗、政策、投研等场景时，必须完成 evidence-bound writing 改造后才可作为严肃报告交付链路。

## 16. 后续需求变更候选

### 16.1 引用去重

**变更说明**：按 URL 或来源标题对 `references` 去重。

**价值**：减少参考文献重复。

**影响范围**：LeadWriter 合成、前端来源展示、CriticMaster 审核。

### 16.2 章节级引用映射

**变更说明**：记录每个章节使用了哪些引用。

**价值**：审核时可精准定位缺来源段落。

**影响范围**：`draft_sections` schema、CriticMaster prompt、前端报告展示。

### 16.3 人工编辑检查点

**变更说明**：写作后允许用户编辑报告，再进入 Review。

**价值**：支持人机协同出稿。

**影响范围**：前端编辑器、状态保存、审核入口。

### 16.4 报告模板系统

**变更说明**：支持咨询报告、投研报告、竞品分析、技术调研等模板。

**价值**：让不同场景的报告结构更稳定。

**影响范围**：ChiefArchitect 大纲、LeadWriter prompt、前端导出。

### 16.5 修订 diff 展示

**变更说明**：修订完成后生成变更前后 diff。

**价值**：用户能看到系统改了什么。

**影响范围**：LeadWriter 修订输出、前端修订详情。

## 17. 待确认问题

1. 报告默认是否需要严格限制字数，还是按大纲自然展开？
2. 用户是否需要人工确认草稿后再进入 Review？
3. 图表插入应由 LeadWriter 明确控制，还是继续由前端语义匹配？
4. 参考文献是否需要按学术格式输出，还是当前可点击链接足够？
