# Step 6 PRD: CriticMaster Review

## 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 阶段 | Step 6: CriticMaster - 质量审核与闭环路由阶段 |
| 所属产品 | AI 深度研究助手 |
| 文档类型 | 基于当前代码反推的产品 PRD |
| 当前状态 | Draft |
| 覆盖范围 | 报告质量审核、问题分级、质量评分、审核事件、补充搜索路由、文字修订路由、最大迭代、完成条件 |
| 不覆盖范围 | 首次搜索、数据分析、代码执行、报告正文生成、前端审稿 UI 设计细节 |
| 主要代码依据 | `backend/app/service/deep_research_v2/agents/critic.py`, `backend/app/service/deep_research_v2/agents/scout.py`, `backend/app/service/deep_research_v2/agents/writer.py`, `backend/app/service/deep_research_v2/state.py`, `backend/app/service/deep_research_v2/graph.py`, `frontend/src/pages/chat/index.tsx` |

## 2. 产品背景

深度研究报告如果只完成“生成”，很容易出现无来源数据、逻辑跳跃、事实幻觉、过时信息和遗漏关键维度。用户真正需要的是可交付的研究结果，因此系统必须在写作后加入质量门。

CriticMaster 是整个多 Agent 研究工作流的质量守门人。它以严苛审稿人和事实核查专家的角色审核报告，给出质量分、结论、问题列表和修订建议。更重要的是，它会判断问题属于“缺信息，需要补充搜索”还是“表达和逻辑问题，只需要修订文字”，并把流程路由回 DeepScout 或 LeadWriter。

当前图中的 Review 阶段不是单点结束，而是一个闭环：Review 通过则完成；Review 不通过则进入 Re-Research 或 Revise；达到最大迭代次数时强制完成并提示风险。

## 3. 问题定义

### 3.1 用户问题

用户希望最终报告经过审稿和事实核查，避免把带有幻觉、缺来源或逻辑问题的内容当成可交付成果。

### 3.2 产品需要解决的问题

系统需要在 Review 阶段完成：

- 审核章节草稿或最终报告。
- 对事实、数据点和大纲覆盖情况进行检查。
- 识别无来源、逻辑错误、偏见、幻觉、过时和不完整问题。
- 给出 `quality_score` 和 `verdict`。
- 按严重程度统计 critical、major、minor 问题。
- 把问题写入 `critic_feedback`。
- 向前端发送审核摘要和严重问题。
- 决定报告是通过、修订、补充搜索还是强制完成。
- 维护迭代次数。

### 3.3 成功定义

CriticMaster 阶段成功的标志是：

- 每次审核产生结构化 `review` 结果。
- `quality_score` 写入全局状态。
- `unresolved_issues` 反映 critical/major 问题数量。
- `critic_feedback` 保存可修订的问题。
- 当 `verdict="pass"` 且质量分达标时，流程进入 completed。
- 当问题需要补充搜索时，生成 `pending_search_queries` 并进入 `re_researching`。
- 当问题只需文字修订时，进入 `revising`。
- 达到最大迭代时强制 completed 并发送 warning。

## 4. 目标用户与使用场景

### 4.1 目标用户

- 研究报告使用者：需要知道报告是否可靠。
- 内容审核者：需要看到问题类型、严重程度和修改建议。
- 产品演示用户：需要理解多 Agent 闭环如何提升质量。

### 4.2 核心场景

**场景 A：报告通过**

LeadWriter 生成的报告来源充分、逻辑完整。CriticMaster 给出 `quality_score >= 7` 且 `verdict="pass"`，流程结束。

**场景 B：文字修订**

报告有表达、结构或轻中度逻辑问题，但不缺新信息。CriticMaster 设置 `phase="revising"`，LeadWriter 根据反馈修订后再次审核。

**场景 C：补充搜索**

报告缺少来源、关键维度不完整或数据过时。CriticMaster 生成 `pending_search_queries`，设置 `phase="re_researching"`，DeepScout 补充搜索后 LeadWriter 重写，再回到审核。

**场景 D：达到最大迭代**

多轮审核仍未通过，但 `iteration >= max_iterations`。系统强制完成，并提示部分问题可能未解决。

## 5. 产品目标

### 5.1 当前阶段目标

CriticMaster 阶段应完成以下目标：

1. 只在 `phase="reviewing"` 时执行审核。
2. 发送 `thought` 事件说明开始严格审核。
3. 优先从 `draft_sections` 构造待审内容。
4. 如果没有章节草稿，则使用 `final_report`。
5. 收集前 20 条事实摘要。
6. 收集前 15 条数据点摘要。
7. 收集大纲章节状态摘要。
8. 调用 LLM 输出结构化审核 JSON。
9. 为每个 issue 生成系统唯一 ID。
10. 将 issue 追加到 `critic_feedback`。
11. 写入 `quality_score`。
12. 统计 critical/major 问题为 `unresolved_issues`。
13. 发送 `review` 事件。
14. 最多发送 3 条 critical `critic_feedback` 事件。
15. 根据 verdict 和问题类型设置下一阶段。
16. 维护 `iteration`。

### 5.2 路由目标

路由规则应完成：

1. `verdict="pass"` 时进入 `completed`。
2. `iteration >= max_iterations` 时进入 `completed` 并发送 warning。
3. 存在信息缺失类问题时，进入 `re_researching`。
4. 信息缺失类问题包括 `missing_source/incomplete/outdated`。
5. 只有 critical/major 的信息缺失问题才计入补充搜索判断。
6. 明确的 `search_query` 和 `missing_aspects` 会进入 `pending_search_queries`。
7. 最多保留 5 个去重搜索查询。
8. 不需要搜索时进入 `revising`。
9. 每轮非通过审核后 `iteration += 1`。

### 5.3 非目标

CriticMaster 不负责：

- 自己执行搜索。
- 自己修改报告正文。
- 验证所有外部网页实时真实性。
- 给出最终 UI 展示形式。
- 重新设计研究大纲。

## 6. 功能范围

### 6.1 Must Have

1. 支持报告质量评分。
2. 支持审核结论 `pass/needs_revision/major_issues`。
3. 支持 issue 类型分类。
4. 支持 issue 严重程度分级。
5. 支持 fact check 结果输出。
6. 支持 missing aspects 输出。
7. 支持问题写入全局状态。
8. 支持审核摘要事件。
9. 支持 critical 问题事件。
10. 支持补充搜索路由。
11. 支持文字修订路由。
12. 支持最大迭代保护。

### 6.2 Should Have

1. `quality_score >= 7` 才允许 `verdict="pass"`。
2. critical 问题必须阻止直接通过。
3. missing_source、incomplete、outdated 应优先考虑补充搜索。
4. 搜索查询应具体可执行。
5. 审核摘要应能让用户快速理解质量风险。
6. 每条 issue 应包含 location、evidence 和 suggestion。

### 6.3 Could Have

1. 支持逐引用事实核查。
2. 支持最终审稿模式 `final_check()` 接入主流程。
3. 支持审核 diff。
4. 支持按 rubric 输出评分维度。
5. 支持用户配置质量阈值。

## 7. 输入输出契约

### 7.1 上游输入

| 字段 | 类型 | 来源 | 用途 |
| --- | --- | --- | --- |
| `query` | string | 用户问题 | 审核上下文 |
| `phase` | string | Graph/LeadWriter | 必须为 `reviewing` |
| `outline` | array | ChiefArchitect | 检查覆盖度 |
| `draft_sections` | object | LeadWriter | 首选待审内容 |
| `final_report` | string | LeadWriter | 无草稿时待审内容 |
| `facts` | array | DeepScout | 事实核查依据 |
| `data_points` | array | DataAnalyst | 数据核查依据 |
| `critic_feedback` | array | CriticMaster | 累积问题 |
| `iteration` | number | Graph/CriticMaster | 当前迭代 |
| `max_iterations` | number | Graph/State | 最大迭代 |

### 7.2 审核输出

LLM 应返回：

```json
{
  "overall_assessment": {
    "quality_score": 7,
    "verdict": "pass",
    "summary": "整体质量良好，少量引用可加强"
  },
  "issues": [
    {
      "id": "issue_1",
      "target_section": "sec_1",
      "issue_type": "missing_source",
      "severity": "major",
      "location": "第一章市场规模段落",
      "description": "市场规模数据缺少来源",
      "evidence": "正文中出现具体数值但没有链接",
      "suggestion": "补充权威报告引用",
      "requires_new_search": true,
      "search_query": "2024 中国 AI 市场规模 权威报告"
    }
  ],
  "fact_check_results": [
    {
      "fact_id": "fact_001",
      "status": "verified",
      "reason": "与引用来源一致"
    }
  ],
  "missing_aspects": ["政策风险"],
  "strength_points": ["结构完整"]
}
```

### 7.3 Issue 规范

系统会为每条 issue 覆盖或补充唯一 ID：

```json
{
  "id": "issue_abcd1234",
  "target_section": "sec_1",
  "issue_type": "missing_source",
  "severity": "major",
  "location": "具体位置",
  "description": "问题描述",
  "evidence": "证据",
  "suggestion": "修改建议",
  "requires_new_search": true,
  "search_query": "搜索关键词",
  "resolved": false
}
```

`issue_type` 允许值：

- `missing_source`
- `logic_error`
- `bias`
- `hallucination`
- `outdated`
- `incomplete`

`severity` 允许值：

- `critical`
- `major`
- `minor`

### 7.4 状态输出

| 字段 | 写入方式 | 说明 |
| --- | --- | --- |
| `critic_feedback` | append | 所有审核问题 |
| `quality_score` | replace | 本轮质量分 |
| `unresolved_issues` | replace | 本轮 critical/major 数量 |
| `pending_search_queries` | replace | 需要补充搜索时写入 |
| `phase` | replace | completed/re_researching/revising |
| `iteration` | increment | 未通过且未达到终态时递增 |
| `messages` | append | 审核事件 |

## 8. 审核与路由流程

### 8.1 阶段进入流程

1. Graph 进入 Review 循环。
2. Graph 发送 `phase="reviewing"` 事件。
3. Graph 设置 `state["phase"] = "reviewing"`。
4. Graph 调用 `CriticMaster.process(state)`。
5. CriticMaster 校验阶段，不是 `reviewing` 则跳过。

### 8.2 审核内容准备流程

1. 从 `draft_sections` 拼接章节草稿。
2. 如果章节草稿为空，使用 `final_report`。
3. 草稿截断到当前 prompt 预算。
4. 汇总前 20 条事实，每条保留 ID、内容、来源和可信度。
5. 汇总前 15 条数据点，每条保留名称、值、单位和来源。
6. 汇总大纲章节 ID、标题和状态。
7. 调用 LLM 进行严格审核。

### 8.3 审核结果写入流程

1. 解析审核 JSON。
2. 为每条 issue 分配 `issue_<uuid>`。
3. 设置 `resolved=false`。
4. 追加到 `state["critic_feedback"]`。
5. 从 `overall_assessment.quality_score` 写入 `quality_score`。
6. 统计 severity 为 critical 或 major 的问题，写入 `unresolved_issues`。
7. 发送 `review` 事件。
8. 取最多 3 条 critical issue，发送 `critic_feedback` 事件。

### 8.4 路由流程

1. 读取 `overall_assessment.verdict`。
2. 如果 verdict 为 `pass`，设置 `phase="completed"`。
3. 如果已达到最大迭代，设置 `phase="completed"` 并发送 warning。
4. 否则调用 `_analyze_issues_for_routing()`。
5. 如果 `should_research=true`，设置 `phase="re_researching"`，写入 `pending_search_queries`。
6. 如果 `should_research=false`，设置 `phase="revising"`。
7. `iteration += 1`。

### 8.5 补充搜索闭环

Graph 发现 `phase="re_researching"` 后：

1. 发送 `phase="re_researching"` 事件。
2. 运行 DeepScout。
3. DeepScout 读取 `pending_search_queries`。
4. 执行补充搜索并追加事实、数据点、洞察。
5. 清空 `pending_search_queries`。
6. Graph 发送 `phase="rewriting"`。
7. 设置 `phase="writing"`。
8. 运行 LeadWriter 重新写作。
9. 回到 Review 循环。

### 8.6 文字修订闭环

Graph 发现 `phase="revising"` 后：

1. 发送 `phase="revising"` 事件。
2. 运行 LeadWriter。
3. LeadWriter 根据未解决反馈修订报告。
4. LeadWriter 设置 `phase="reviewing"`。
5. 回到 Review 循环。

## 9. 事件与前端展示需求

### 9.1 Review 阶段事件

Graph 发送：

```json
{
  "type": "phase",
  "phase": "reviewing",
  "content": "审核中（第 1 轮）..."
}
```

CriticMaster 发送 thought：

```json
{
  "type": "thought",
  "content": {
    "agent": "CriticMaster",
    "content": "开始严格审核研究报告，准备找出所有问题..."
  }
}
```

### 9.2 审核摘要事件

```json
{
  "type": "review",
  "content": {
    "agent": "CriticMaster",
    "verdict": "needs_revision",
    "quality_score": 6,
    "issues_count": 4,
    "critical_issues": 1,
    "major_issues": 2,
    "summary": "报告存在缺来源和遗漏维度",
    "missing_aspects": ["政策风险"]
  }
}
```

前端应：

- 更新 reviewing 步骤状态。
- 展示质量分。
- 展示问题数量和摘要。
- 在必要时提示仍需修订或补充搜索。

### 9.3 严重问题事件

```json
{
  "type": "critic_feedback",
  "content": {
    "agent": "CriticMaster",
    "issue_type": "hallucination",
    "severity": "critical",
    "description": "核心数据没有来源",
    "suggestion": "补充权威来源或删除该数据"
  }
}
```

当前最多发送 3 条 critical 问题给前端。

### 9.4 补充搜索事件

当需要补充搜索时，CriticMaster 发送：

```json
{
  "type": "thought",
  "content": {
    "agent": "CriticMaster",
    "content": "发现信息缺失问题，需要补充搜索: 2024 AI市场规模"
  }
}
```

Graph 随后发送：

```json
{
  "type": "phase",
  "phase": "re_researching",
  "content": "根据审核反馈补充搜索..."
}
```

### 9.5 完成事件

Review 通过或达到最大迭代后，Graph 最终发送：

```json
{
  "type": "research_complete",
  "final_report": "完整报告",
  "quality_score": 7,
  "facts_count": 24,
  "charts_count": 3,
  "iterations": 1,
  "references": []
}
```

前端应把最终报告、质量分、来源和图表写入最终消息。

## 10. 质量规则

### 10.1 评分规则

- 9-10：优秀，几乎无问题，可直接发布。
- 7-8：良好，有小问题但不影响整体质量，可通过。
- 5-6：一般，有明显问题，需要修订。
- 3-4：较差，问题较多，需要大幅修改。
- 1-2：很差，存在严重问题或大量错误。

### 10.2 通过规则

- `quality_score >= 7` 才允许 `verdict="pass"`。
- 有 critical 问题时不应通过。
- major 问题数量较多时不应通过。

### 10.3 严重程度规则

- `critical`：必须修复，否则报告不可用。
- `major`：强烈建议修复，影响报告质量。
- `minor`：建议修复，用于提升质量。

### 10.4 补充搜索判断规则

问题类型属于以下集合时，可能需要补充搜索：

- `missing_source`
- `incomplete`
- `outdated`

且应满足：

- severity 为 `critical` 或 `major`。
- 有明确 `search_query`，或 `missing_aspects` 非空。
- 信息缺失类问题在严重问题中占比超过当前阈值，或有明确搜索建议。

## 11. 非功能需求

### 11.1 可解释性

审核结论必须包含 summary、issue、evidence 和 suggestion，不能只有分数。

### 11.2 可追踪性

每轮 issue 都应写入 `critic_feedback`，修订阶段可按 ID 标记 resolved。

### 11.3 稳定性

LLM 审核失败或无结果时，不应误判为通过。当前代码在无 `review_result` 时保持状态不变。

### 11.4 可控性

审核循环受 `max_iterations` 限制，避免无限循环。

### 11.5 前端可理解性

前端应至少展示质量分、审核结论、问题数量和是否进入补充搜索或修订。

## 12. 验收标准

### 12.1 功能验收

1. `phase!="reviewing"` 时，CriticMaster 不执行审核。
2. 有 `draft_sections` 时，优先审核章节草稿。
3. 无 `draft_sections` 时，审核 `final_report`。
4. 审核成功后写入 `quality_score`。
5. 审核成功后 `critic_feedback` 数量增加。
6. `unresolved_issues` 等于本轮 critical/major 数量。
7. 前端能收到 `review` 事件。
8. 有 critical issue 时，前端能收到最多 3 条 `critic_feedback`。
9. `verdict="pass"` 时，阶段进入 `completed`。
10. 需要补充搜索时，阶段进入 `re_researching` 并写入搜索查询。
11. 不需要补充搜索但需修改时，阶段进入 `revising`。
12. 达到最大迭代时，阶段进入 `completed` 并发送 warning。

### 12.2 异常验收

1. `final_report` 为空时，审核 prompt 中显示暂无内容，不抛异常。
2. `facts` 为空时，审核仍可指出缺少事实依据。
3. `data_points` 为空时，审核仍可指出缺少数据支持。
4. `missing_aspects` 为空但有文字问题时，进入 `revising`。
5. 搜索查询重复时，去重后最多保留 5 条。
6. 多轮审核中历史反馈不应被清空。

### 12.3 典型案例

以下案例用于说明阶段契约，不代表一次真实线上运行结果。

#### 12.3.1 输入

来自 LeadWriter 的状态摘要：

```json
{
  "query": "研究 2024-2026 中国 AI 芯片市场格局、主要玩家、技术趋势和投资风险。",
  "phase": "reviewing",
  "iteration": 0,
  "max_iterations": 3,
  "draft_sections": {
    "sec_1": "中国 AI 芯片市场将在 2026 年达到很高规模，但该段没有提供来源链接。"
  },
  "final_report": "## 执行摘要\n\n...\n\n## 1 市场规模与增长趋势\n\n...",
  "facts": [
    {
      "id": "fact_market_001",
      "content": "示例行业报告称，AI 芯片需求受大模型推理部署拉动。",
      "source_name": "示例行业报告",
      "credibility_score": 0.78
    }
  ],
  "data_points": [
    {"name": "中国 AI 芯片市场规模", "value": 500, "unit": "亿元", "source": "示例行业报告"}
  ],
  "critic_feedback": []
}
```

#### 12.3.2 调用链与方案

##### 12.3.2.1 进入审核阶段：让流程从写作转入质量控制

**当前行为**：Graph 进入 Review 循环，发送 `phase="reviewing"`。

**目标**：明确告诉系统“报告已经从写作阶段进入审核阶段”，后续不再继续生成正文，而是检查现有报告质量。

**作用**：这是流程路由信号。没有这个阶段切换，CriticMaster 不应开始审核，LeadWriter 也可能继续停留在写作或修订逻辑中。

##### 12.3.2.2 校验执行条件：防御非 Review 阶段的误调用

**当前行为**：CriticMaster 先检查 `state["phase"]`。只有 `phase == "reviewing"` 时才进入 `_review_content()`；如果不是 `reviewing`，直接返回原 `state`。

**目标**：在正常 Graph 流程之外提供一道防御式门禁。正常情况下，Graph 应该在写作完成后先把 `phase` 设置为 `reviewing`，再调用 CriticMaster；这个判断用于防止测试、断点恢复、异常路由或未来流程改造时误调用 CriticMaster。

**作用**：如果 CriticMaster 被错误调用，例如当前仍是 `planning/researching/analyzing/writing/revising/re_researching/completed`，它不会调用审核 LLM，不会写入 `critic_feedback`，不会修改 `quality_score`，也不会改变后续路由。

**当前限制**：该门禁只检查 `phase`，不等于完整的输入就绪校验。如果 Graph 错误地设置了 `phase="reviewing"`，但 `draft_sections/final_report` 为空，当前 CriticMaster 仍可能进入审核。后续应补充“报告内容非空、章节草稿存在、iteration 未超限”等检查。

##### 12.3.2.3 选择待审内容：确定 CriticMaster 具体审核什么文本

**当前行为**：系统优先拼接 `draft_sections` 作为待审内容；如果为空，则使用 `final_report`。

**目标**：把可审核内容整理成一段完整文本，交给审核 prompt 使用。

**作用**：`draft_sections` 更接近章节级写作结果，便于定位具体章节问题；`final_report` 是兜底输入，保证系统在只有完整报告字符串时也能继续审核。

**当前限制**：拼接后的文本会丢失部分结构化上下文，例如每个段落对应的 `fact_id/data_point_id/chart_id`。后续如果引入 claim ledger，应优先审核结构化 claim，而不是只审核自然语言文本。

##### 12.3.2.4 汇总审核依据：给 CriticMaster 提供事实、数据和结构上下文

**当前行为**：系统汇总前 20 条事实、前 15 条数据点和大纲章节状态。

**目标**：让 CriticMaster 不只看报告正文，还能对照上游事实、数据点和大纲，判断报告是否有遗漏、错配或缺少来源。

**作用**：

1. `facts` 用于检查正文中的关键判断是否有来源支撑。
2. `data_points` 用于检查数字、趋势、市场规模等表述是否有数据依据。
3. `outline` 用于检查报告是否覆盖了原计划章节。

**当前限制**：这里的“前 20 条”和“前 15 条”是截断策略，不代表最相关或最可信的材料。后续应改为按章节、相关性、可信度和引用频次选择审核依据。

##### 12.3.2.5 调用审核模型：生成结构化质量评估结果

**当前行为**：通过 `REVIEW_PROMPT` 调用 LLM，要求输出 `overall_assessment/issues/fact_check_results/missing_aspects/strength_points`。

**目标**：让模型从完整性、事实支撑、数据准确性、逻辑结构、引用质量等维度识别报告问题。

**作用**：这一阶段把自然语言报告转成结构化审核结果，供后续流程判断是否通过、修订还是补充搜索。

关键输出含义：

- `overall_assessment`：整体判断和质量分。
- `issues`：需要修复的问题列表。
- `fact_check_results`：事实核查结果或疑点。
- `missing_aspects`：报告缺失但应覆盖的方面。
- `strength_points`：报告已经做得较好的点。

**当前限制**：这里是 LLM 审核，不是确定性 fact checker。它能发现明显问题，但不能保证所有事实都被真实验证。

##### 12.3.2.6 标准化问题对象：把模型反馈转成可追踪任务

**当前行为**：系统为每条 issue 生成唯一 ID，设置 `resolved=false`，追加到 `critic_feedback`。

**目标**：把 LLM 输出的审核意见变成系统可追踪的结构化问题。

**作用**：

1. `id` 用于后续修订、复审和前端展示。
2. `resolved=false` 表示问题尚未处理。
3. `critic_feedback` 成为 LeadWriter 修订和 DeepScout 补充搜索的任务来源。

如果没有这一步，审核意见只是一段文本，后续 Agent 很难知道哪些问题已经处理、哪些仍然未解决。

##### 12.3.2.7 计算质量状态：决定报告是否达到通过门槛

**当前行为**：系统写入 `quality_score`，并按 critical/major 数量更新 `unresolved_issues`。

**目标**：把审核结果压缩成流程可判断的状态指标。

**作用**：

1. `quality_score` 用于判断报告是否可以通过。
2. `critical/major` 问题数量用于判断是否必须继续修复。
3. `unresolved_issues` 用于控制循环是否还需要继续。

在当前规则中，`quality_score >= 7` 且没有阻断性问题，才有机会进入完成状态；否则需要修订或补充搜索。

##### 12.3.2.8 判断后续路由：决定是补充搜索、修订，还是完成

**当前行为**：`_analyze_issues_for_routing()` 判断问题是否需要补充搜索。

**目标**：根据问题类型决定下一步应该由哪个阶段处理。

**作用**：

1. 如果问题是缺少来源、信息不完整、数据过旧，并且需要新材料，则进入 `re_researching`，由 DeepScout 补充搜索。
2. 如果问题主要是表达、结构、引用格式或逻辑组织，则进入 `revising`，由 LeadWriter 修订报告。
3. 如果质量分和问题数量达到通过条件，则进入完成路径。

这一步是 Review 阶段的闭环控制点。CriticMaster 不直接修改报告，也不直接联网；它负责判断问题性质，并把流程路由给最合适的上游阶段。

#### 12.3.3 输出

审核结果示例：

```json
{
  "quality_score": 6,
  "unresolved_issues": 1,
  "critic_feedback": [
    {
      "id": "issue_a1b2c3d4",
      "target_section": "sec_1",
      "issue_type": "missing_source",
      "severity": "major",
      "location": "市场规模预测段落",
      "description": "2026 年市场规模预测没有明确来源。",
      "evidence": "正文出现具体预测但没有引用链接。",
      "suggestion": "补充权威报告来源，或删除未验证预测。",
      "requires_new_search": true,
      "search_query": "2026 中国 AI 芯片 市场规模 预测 报告",
      "resolved": false
    }
  ],
  "phase": "re_researching",
  "pending_search_queries": [
    "2026 中国 AI 芯片 市场规模 预测 报告"
  ],
  "iteration": 1
}
```

前端审核事件示例：

```json
{
  "type": "review",
  "content": {
    "agent": "CriticMaster",
    "verdict": "needs_revision",
    "quality_score": 6,
    "issues_count": 1,
    "critical_issues": 0,
    "major_issues": 1,
    "summary": "报告结构可用，但市场规模预测缺少来源。",
    "missing_aspects": []
  }
}
```

#### 12.3.4 验收点

- `quality_score >= 7` 才允许通过。
- critical/major 问题必须写入 `critic_feedback`。
- `missing_source/incomplete/outdated` 且需要新信息时，应生成 `pending_search_queries`。
- 纯文字或结构问题应进入 `revising`。
- 达到 `max_iterations` 时应强制完成并发出 warning。

## 13. 当前代码依据

- `CriticMaster.process()`：阶段判断、审核、状态写入、路由。
- `CriticMaster._review_content()`：构造审核 prompt，调用 LLM，解析审核 JSON。
- `CriticMaster._analyze_issues_for_routing()`：判断补充搜索或文字修订。
- `CriticMaster.final_check()`：最终检查能力，目前未接入主 Graph 循环。
- `ResearchState`：定义 `critic_feedback/unresolved_issues/quality_score/pending_search_queries/iteration/max_iterations`。
- `DeepResearchGraph._run_simplified()`：Review/Revise/Re-Research 循环。
- `DeepScout._supplementary_research()`：读取 `pending_search_queries` 并补充搜索。
- `LeadWriter._revise_report()`：根据 feedback 修订报告。
- `frontend/src/pages/chat/index.tsx`：处理 `review/revision_complete/research_complete`。

## 14. 边界与不做范围

- CriticMaster 不直接联网验证事实。
- CriticMaster 不修改报告，只提供反馈和路由。
- CriticMaster 当前审核依赖 LLM 判断，不是确定性 fact checker。
- CriticMaster 当前 `final_check()` 未进入主流程，不能把最终检查视为已启用能力。
- 达到最大迭代后可能仍有未解决问题，系统会强制完成并提示风险。

## 15. 当前实现限制与专业化改造建议

本节记录当前 Step 6 的核心问题和后续专业化改造方向。以下内容不改变当前代码行为，作为后续统一处理的产品和工程依据。

Step 6 的本质不是普通文本润色，而是质量门控与流程路由评测。它要判断当前报告是否达标、问题在哪里、问题严重程度如何、是否需要继续迭代，以及下一步应该回到 Research、Analyze、Write 还是人工处理。

### 15.1 核心风险：LLM 评测不稳定会放大为路由错误

当前 CriticMaster 主要依赖 LLM 阅读报告和上游素材后输出审核结论。这个设计可以快速形成闭环，但核心风险是：LLM 对当前进展的评估不一定准确，后续路由也可能随之错误。

典型错误包括：

| 错误类型 | 表现 | 影响 |
| --- | --- | --- |
| 漏判 | 报告存在缺来源、数字不一致或逻辑跳跃，但 LLM 未发现 | 系统可能误判为可完成 |
| 误判 | 报告已有足够依据，但 LLM 认为缺资料 | 系统可能错误进入 `re_researching` |
| 错分问题类型 | 真实问题是引用绑定差，但 LLM 判断为缺少事实 | 本应回 Step5 修订，却错误回 Step2 补搜 |
| 严重程度不稳 | 同一问题在不同轮被判为 `major/minor` 不一致 | 影响 `quality_score` 和是否继续迭代 |
| 路由依据过粗 | 只依赖 `missing_source/incomplete/outdated` 等 issue type | 难以区分补搜、修订、数据修复、人工确认 |

因此，当前链路的风险传导是：

```text
LLM 审核结果不稳定
    -> issue 识别可能不准
    -> issue 类型和严重程度可能不准
    -> quality_score 可能不准
    -> re_researching / revising / completed 路由可能不准
```

### 15.2 当前做得较好的部分

当前实现已经具备 Review 闭环的基础骨架：

1. **阶段门禁**：只有 `phase="reviewing"` 时才执行审核，能防御非 Review 阶段误调用。
2. **结构化审核输出**：要求 LLM 返回 `overall_assessment/issues/fact_check_results/missing_aspects/strength_points`，不是只返回自然语言评价。
3. **Issue 任务化**：每个 issue 会生成 `id`，设置 `resolved=false`，并写入 `critic_feedback`。
4. **自动路由意识**：`_analyze_issues_for_routing()` 会判断是否需要补充搜索，而不是所有问题都回到写作阶段。
5. **最大迭代保护**：达到 `max_iterations` 后强制完成并提示 warning，避免无限循环。

这些能力说明 Step 6 已经不是单纯“打分器”，而是 Review/Revise/Re-Research 循环的控制点。

### 15.3 当前主要不足

#### 15.3.1 审核依据截断

当前审核依据会截取前 20 条 `facts`、前 15 条 `data_points` 和大纲状态。这是上下文控制策略，但不等于相关性选择。

风险：

- 前 N 条不一定是当前报告最关键的证据。
- 高可信来源可能排在后面而未进入审核 prompt。
- 某个章节的问题可能需要章节级证据，而不是全局摘要。
- LLM 可能基于不完整上下文给出错误路由。

#### 15.3.2 缺少 claim 级审核

当前 CriticMaster 审核的是拼接后的报告文本，不是结构化 claim。它很难严格回答：

- 这句话对应哪个 `fact_id`？
- 这个数字对应哪个 `data_point_id`？
- 这个图表解释是否超出了 `chart_id` 所表达的数据？
- 这个结论是否由来源直接支持，还是 LLM 推断？

没有 claim 级结构，Step6 很难做精确 fact checking，也很难稳定复查 issue 是否解决。

#### 15.3.3 路由规则过粗

当前路由主要判断是否存在 `missing_source/incomplete/outdated` 且需要搜索。这个规则方向正确，但粒度不够。

现实问题至少应区分：

| 问题类型 | 应路由到 |
| --- | --- |
| 缺新来源或新事实 | Step2 / Re-Research |
| 已有事实未正确引用 | Step5 / Revise |
| 数据点单位、年份、口径不一致 | Step3 / Re-Analyze |
| 图表数据或图表解释错误 | Step4 / Re-Analyze |
| 报告结构、表达、摘要质量问题 | Step5 / Revise |
| 高风险、模型无法判断 | Human Review |

#### 15.3.4 Issue 生命周期不完整

当前 issue 初始状态是 `resolved=false`，但后续缺少严格的生命周期管理。

缺失点：

- issue 是否已分配给某个阶段。
- 修订是否真的处理了该 issue。
- 解决证据是什么。
- 下一轮审核是否验证通过。
- 无法处理的问题是否被用户豁免。

#### 15.3.5 缺少确定性校验

当前审核主要依赖 LLM。后续应加入规则校验，先处理可以确定判断的问题：

- Markdown 中的 URL 是否存在。
- `chart_id` 是否真实存在于 `charts`。
- 图表标题是否匹配。
- 报告数字是否能匹配 `data_points`。
- 章节是否覆盖 `outline`。
- critical issue 是否阻止完成。
- `quality_score` 是否与 issue 严重程度一致。

### 15.4 推荐目标架构

后续 Step 6 应从“LLM 审稿”升级为“规则校验 + claim/evidence 对照 + LLM 语义评审 + 路由决策”的质量门控系统。

推荐链路：

```text
final_report + draft_sections + claim_ledger + evidence_packs
    -> deterministic_checks
    -> claim_evidence_review
    -> LLM_semantic_review
    -> issue_normalization
    -> route_decision
    -> issue_lifecycle_update
```

各模块职责：

| 模块 | 职责 | 输出 |
| --- | --- | --- |
| deterministic_checks | 检查 URL、chart_id、数字匹配、章节覆盖 | hard rule issues |
| claim_evidence_review | 对照 claim 与 fact/data/chart 关系 | unsupported/weak claims |
| LLM_semantic_review | 判断逻辑、完整性、表达、洞察质量 | semantic issues |
| issue_normalization | 合并重复问题、统一严重程度 | normalized issues |
| route_decision | 决定补搜、重分析、修订、人工处理或完成 | next_phase |
| issue_lifecycle_update | 记录 issue 状态、处理证据和复审结果 | updated critic_feedback |

### 15.5 路由决策应由多信号共同决定

后续不应让 LLM 独占最终路由权。路由应综合：

1. 确定性规则结果。
2. claim/evidence 对照结果。
3. LLM 语义审核结果。
4. issue 严重程度。
5. 当前迭代次数。
6. 是否存在高风险领域或人工确认要求。

推荐路由规则：

```text
if hard_rule_critical_issue:
    route = "revising" or "re_analyzing"
elif missing_required_source and no_existing_fact_support:
    route = "re_researching"
elif missing_citation_but_existing_fact_support:
    route = "revising"
elif numeric_or_chart_mismatch:
    route = "re_analyzing"
elif semantic_quality_issue:
    route = "revising"
elif high_risk_uncertainty:
    route = "human_review"
elif quality_score >= threshold and no_blocking_issue:
    route = "completed"
```

### 15.6 Issue 生命周期建议

Issue 不应只有 `resolved=true/false`。推荐状态：

```json
{
  "id": "issue_001",
  "status": "open",
  "assigned_to": "LeadWriter",
  "route": "revising",
  "resolution_evidence": [],
  "verified_by": null,
  "verified_at_iteration": null,
  "waived_by_user": false
}
```

状态流转：

```text
open -> routed -> fixed -> verified
open -> routed -> unable_to_fix -> human_review
open -> waived
```

这样 Step6 才能回答“问题是否真的解决”，而不是每轮重新生成一批无关联的审核意见。

### 15.7 推荐优化优先级

| 优先级 | 优化项 | 目标 |
| --- | --- | --- |
| P0 | 明确 Step6 是质量门控与路由评测器 | 防止把 Review 简化为文本打分 |
| P0 | 增加确定性校验 | 先发现 URL、chart_id、数字、章节覆盖等硬问题 |
| P1 | 引入 claim ledger 审核 | 支持 claim 级事实和数据核查 |
| P1 | 使用 Evidence Pack 替代前 N 条素材截断 | 提升审核依据相关性 |
| P1 | 细化路由类型 | 区分补搜、修订、重分析和人工处理 |
| P2 | 建立 issue 生命周期 | 支持跨轮追踪和复审 |
| P2 | 接入 `final_check()` 到主流程 | 最后一轮确认旧问题已解决且未引入新问题 |
| P2 | 高风险领域人工审核门 | 避免 LLM 单独决定完成 |

当前文档中的 CriticMaster 能力应被理解为 demo/prototype 级质量闭环能力；面向高敏、金融、医疗、政策、投研等场景时，必须完成结构化评测和路由治理后才可作为严肃交付门控。

## 16. 后续需求变更候选

### 16.1 Rubric 化评分

**变更说明**：把质量分拆成事实准确性、来源质量、逻辑完整性、覆盖度、表达质量等维度。

**价值**：让用户知道扣分原因。

**影响范围**：CriticMaster prompt、前端质量展示、验收标准。

### 16.2 最终检查接入主流程

**变更说明**：在最后一轮修订后调用 `final_check()`。

**价值**：确认旧问题是否解决，避免修订引入新问题。

**影响范围**：Graph 循环、CriticMaster 输出、前端最终状态。

### 16.3 用户审核门

**变更说明**：CriticMaster 给出结果后允许用户决定继续补搜、修订或强制完成。

**价值**：提高人机协作可控性。

**影响范围**：Graph 中断恢复、前端交互、状态保存。

### 16.4 事实级引用核查

**变更说明**：对报告中的每个关键事实映射到来源并检查是否存在引用。

**价值**：降低幻觉风险。

**影响范围**：LeadWriter 引用映射、CriticMaster fact check、数据结构。

### 16.5 审核结果可视化

**变更说明**：按章节展示问题热力图和严重程度。

**价值**：用户更容易定位报告薄弱环节。

**影响范围**：CriticMaster issue schema、前端详情页。

## 17. 待确认问题

1. 质量通过阈值是否固定为 7，还是应允许用户或配置调整？
2. 达到最大迭代后是否应强制完成，还是停在“需要人工处理”状态？
3. critical 问题是否应始终阻止完成，即使达到最大迭代？
4. 用户是否需要在每轮 Review 后手动确认下一步路由？
