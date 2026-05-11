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

1. Graph 进入 Review 循环，发送 `phase="reviewing"`。
2. CriticMaster 校验 `phase` 后进入 `_review_content()`。
3. 系统优先拼接 `draft_sections` 作为待审内容；如果为空，则使用 `final_report`。
4. 系统汇总前 20 条事实、前 15 条数据点和大纲章节状态。
5. 通过 `REVIEW_PROMPT` 调用 LLM，要求输出 `overall_assessment/issues/fact_check_results/missing_aspects/strength_points`。
6. 系统为每条 issue 生成唯一 ID，设置 `resolved=false`，追加到 `critic_feedback`。
7. 系统写入 `quality_score`，并按 critical/major 数量更新 `unresolved_issues`。
8. `_analyze_issues_for_routing()` 判断问题是否需要补充搜索。

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

## 15. 后续需求变更候选

### 15.1 Rubric 化评分

**变更说明**：把质量分拆成事实准确性、来源质量、逻辑完整性、覆盖度、表达质量等维度。

**价值**：让用户知道扣分原因。

**影响范围**：CriticMaster prompt、前端质量展示、验收标准。

### 15.2 最终检查接入主流程

**变更说明**：在最后一轮修订后调用 `final_check()`。

**价值**：确认旧问题是否解决，避免修订引入新问题。

**影响范围**：Graph 循环、CriticMaster 输出、前端最终状态。

### 15.3 用户审核门

**变更说明**：CriticMaster 给出结果后允许用户决定继续补搜、修订或强制完成。

**价值**：提高人机协作可控性。

**影响范围**：Graph 中断恢复、前端交互、状态保存。

### 15.4 事实级引用核查

**变更说明**：对报告中的每个关键事实映射到来源并检查是否存在引用。

**价值**：降低幻觉风险。

**影响范围**：LeadWriter 引用映射、CriticMaster fact check、数据结构。

### 15.5 审核结果可视化

**变更说明**：按章节展示问题热力图和严重程度。

**价值**：用户更容易定位报告薄弱环节。

**影响范围**：CriticMaster issue schema、前端详情页。

## 16. 待确认问题

1. 质量通过阈值是否固定为 7，还是应允许用户或配置调整？
2. 达到最大迭代后是否应强制完成，还是停在“需要人工处理”状态？
3. critical 问题是否应始终阻止完成，即使达到最大迭代？
4. 用户是否需要在每轮 Review 后手动确认下一步路由？
