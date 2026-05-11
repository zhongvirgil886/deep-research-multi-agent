# DeepResearch Workflow Canonical Examples

本文档补充 `step1` 到 `step6` PRD 中的阶段案例，提供一条端到端的代表性状态流转。本文档不是运行日志，不承诺数值和来源为真实结果；它用于说明“输入什么、调用什么、采用什么方案、输出什么”。

## 1. 案例范围

| 项目 | 内容 |
| --- | --- |
| 用户问题 | 研究 2024-2026 中国 AI 芯片市场格局、主要玩家、技术趋势和投资风险。 |
| 搜索模式 | `search_web=true`, `search_local=false` |
| 最大迭代 | `max_iterations=3` |
| 目标 | 生成一份带事实、数据点、图谱、图表、引用和质量审核的研究报告 |
| 不覆盖 | 真实 API 响应、真实市场规模数值、完整报告正文 |

## 2. 初始请求

前端或 API 传入：

```json
{
  "query": "研究 2024-2026 中国 AI 芯片市场格局、主要玩家、技术趋势和投资风险。",
  "session_id": "sess_ai_chip_001",
  "search_web": true,
  "search_local": false
}
```

后端创建初始状态：

```json
{
  "phase": "init",
  "iteration": 0,
  "max_iterations": 3,
  "outline": [],
  "facts": [],
  "data_points": [],
  "charts": [],
  "draft_sections": {},
  "final_report": "",
  "critic_feedback": []
}
```

## 3. Step 1: ChiefArchitect / Planning

### 3.1 输入

```json
{
  "query": "研究 2024-2026 中国 AI 芯片市场格局、主要玩家、技术趋势和投资风险。",
  "phase": "init"
}
```

### 3.2 调用与方案

- 调用 Agent：`ChiefArchitect`
- 主要方法：`_initial_planning()`
- 主要模型调用：`BaseAgent.call_llm()` + `PLANNING_PROMPT`
- 失败处理：非 JSON、缺少 `outline`、章节少于 3 个时重试；扁平格式用 `_convert_flat_to_outline()` 转换。

### 3.3 输出摘要

```json
{
  "phase": "planning",
  "outline": [
    {
      "id": "sec_1",
      "title": "市场规模与增长趋势",
      "section_type": "quantitative",
      "requires_data": true,
      "requires_chart": true,
      "search_queries": [
        "2024 中国 AI 芯片 市场规模 报告",
        "2025 中国 AI 加速芯片 增长率"
      ],
      "status": "pending"
    },
    {
      "id": "sec_2",
      "title": "主要玩家与竞争格局",
      "section_type": "mixed",
      "requires_data": true,
      "requires_chart": false,
      "search_queries": [
        "中国 AI 芯片 主要厂商 寒武纪 昇腾 壁仞"
      ],
      "status": "pending"
    }
  ],
  "research_questions": [
    "市场规模和增速如何变化？",
    "主要玩家的竞争优势是什么？"
  ],
  "hypotheses": [
    {
      "id": "h_1",
      "content": "推理算力需求增长会推动国产 AI 芯片市场扩张。",
      "status": "untested"
    }
  ]
}
```

前端核心事件：

```json
{
  "type": "research_step",
  "content": {
    "step_type": "planning",
    "status": "completed",
    "stats": {
      "sections_count": 5,
      "questions_count": 4
    }
  }
}
```

## 4. Step 2: DeepScout / Research

### 4.1 输入

```json
{
  "phase": "researching",
  "search_web": true,
  "search_local": false,
  "outline": [
    {
      "id": "sec_1",
      "title": "市场规模与增长趋势",
      "search_queries": [
        "2024 中国 AI 芯片 市场规模 报告"
      ],
      "status": "pending"
    }
  ]
}
```

### 4.2 调用与方案

- 调用 Agent：`DeepScout`
- 网络搜索：`_execute_search()`，当前使用 Bocha Web Search API
- 本地搜索：本例关闭；开启时走 `_execute_local_search()` 和 Milvus
- 抽取：`_analyze_search_results()` 用 LLM 生成事实、数据点、实体和后续搜索词
- 质量控制：事实指纹去重；搜索预算限制深度追踪

### 4.3 输出摘要

```json
{
  "facts": [
    {
      "id": "fact_market_001",
      "content": "示例行业报告称，中国 AI 芯片市场需求受大模型推理部署拉动。",
      "source_name": "示例行业报告",
      "source_url": "https://example.com/ai-chip-report",
      "source_type": "report",
      "credibility_score": 0.78,
      "related_sections": ["sec_1"]
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
    "nodes": [
      {"id": "ai_chip", "name": "AI 芯片", "type": "technology"}
    ],
    "edges": [
      {"source": "ai_chip", "target": "large_model", "relation": "支撑"}
    ]
  }
}
```

前端核心事件：

```json
{
  "type": "search_results",
  "content": {
    "results": [
      {
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

## 5. Step 3: DataAnalyst / Analyze

### 5.1 输入

```json
{
  "phase": "analyzing",
  "facts": ["fact_market_001", "fact_vendor_001"],
  "data_points": ["dp_market_2024"]
}
```

### 5.2 调用与方案

- 调用 Agent：`DataAnalyst`
- 数据提取：`_extract_data()` + `DATA_EXTRACTION_PROMPT`
- 图谱构建：`_build_knowledge_graph()` + `KNOWLEDGE_GRAPH_PROMPT`
- 图表配置：`_generate_charts()` + `CHART_GENERATION_PROMPT`
- 输出形式：ECharts `echarts_option`，不是 Python 图片

### 5.3 输出摘要

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
      {"id": "ai_chip", "name": "AI 芯片", "type": "core", "importance": 10, "size": 50}
    ],
    "edges": []
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

前端核心事件：

```json
{
  "type": "charts",
  "content": {
    "charts": [
      {"id": "chart_market_trend", "title": "中国 AI 芯片市场增长趋势", "echarts_option": {}}
    ]
  }
}
```

## 6. Step 4: CodeWizard / Analyze

### 6.1 输入

```json
{
  "phase": "analyzing",
  "data_points": [
    {"name": "中国 AI 芯片市场规模", "value": 500, "unit": "亿元", "year": 2024},
    {"name": "中国 AI 芯片市场规模", "value": 640, "unit": "亿元", "year": 2025},
    {"name": "中国 AI 芯片市场规模", "value": 820, "unit": "亿元", "year": 2026}
  ]
}
```

### 6.2 调用与方案

- 调用 Agent：`CodeWizard`
- 代码生成：`ANALYSIS_PROMPT`
- 代码清理：`_clean_code()`
- 安全检查：`compile()` 语法预检 + `_is_code_safe()`
- 执行环境：`_execute_in_sandbox()`，预置 `pd/np/plt/sns`
- 自愈：`_execute_with_self_correction()` 最多重试 3 次
- 输出形式：Matplotlib PNG base64

### 6.3 输出摘要

```json
{
  "code_executions": [
    {
      "id": "exec_a1b2c3d4",
      "code": "最终执行代码",
      "output": "",
      "error": null,
      "charts": ["base64_png_string"],
      "retries": 0
    }
  ],
  "charts": [
    {
      "id": "chart_analysis_a1b2c3d4",
      "title": "数据分析图表 1",
      "chart_type": "generated",
      "image_base64": "base64_png_string",
      "section_id": "analysis"
    }
  ]
}
```

前端核心事件：

```json
{
  "type": "chart",
  "content": {
    "agent": "CodeWizard",
    "title": "数据分析图表 1",
    "chart_type": "generated",
    "image_base64": "base64_png_string"
  }
}
```

## 7. Step 5: LeadWriter / Write

### 7.1 输入

```json
{
  "phase": "writing",
  "outline": ["sec_1", "sec_2"],
  "facts": ["fact_market_001"],
  "data_points": ["dp_market_2024", "dp_growth_2025"],
  "insights": ["AI 芯片市场增长与大模型推理部署密切相关。"],
  "charts": ["chart_market_trend", "chart_analysis_a1b2c3d4"]
}
```

### 7.2 调用与方案

- 调用 Agent：`LeadWriter`
- 章节写作：`_write_section()` + `SECTION_WRITING_PROMPT`
- 报告合成：`_synthesize_report()` + `SYNTHESIS_PROMPT`
- 引用策略：章节内使用 `[来源名称](URL)`
- 图表策略：正文中使用 `![图表标题](chart_id)`，前端再匹配图表
- 失败回退：完整报告合成失败时，用章节草稿拼接 fallback 报告

### 7.3 输出摘要

```json
{
  "draft_sections": {
    "sec_1": "2024 年以来，中国 AI 芯片需求继续增长。根据[示例行业报告](https://example.com/ai-chip-report)，需求正在从训练侧扩展到推理侧。![中国 AI 芯片市场增长趋势](chart_market_trend)"
  },
  "final_report": "## 执行摘要\n\n...\n\n## 1 市场规模与增长趋势\n\n...",
  "references": [
    {
      "id": 1,
      "source": "示例行业报告",
      "url": "https://example.com/ai-chip-report"
    }
  ],
  "phase": "reviewing"
}
```

前端核心事件：

```json
{
  "type": "report_draft",
  "content": {
    "content": "## 执行摘要\n\n...\n\n## 1 市场规模与增长趋势\n\n...",
    "word_count": 3200,
    "references_count": 8
  }
}
```

## 8. Step 6: CriticMaster / Review

### 8.1 输入

```json
{
  "phase": "reviewing",
  "iteration": 0,
  "max_iterations": 3,
  "draft_sections": {
    "sec_1": "中国 AI 芯片市场将在 2026 年达到很高规模，但该段没有提供来源链接。"
  },
  "facts": ["fact_market_001"],
  "data_points": ["dp_market_2024"]
}
```

### 8.2 调用与方案

- 调用 Agent：`CriticMaster`
- 审核内容：优先 `draft_sections`，否则 `final_report`
- 模型调用：`REVIEW_PROMPT`
- 输出结构：`overall_assessment/issues/fact_check_results/missing_aspects`
- 路由方案：
  - `verdict="pass"` -> `completed`
  - 信息缺失类 major/critical -> `re_researching`
  - 文字结构问题 -> `revising`
  - 达到 `max_iterations` -> 强制 `completed` 并发送 warning

### 8.3 输出摘要

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
      "description": "2026 年市场规模预测没有明确来源。",
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

前端核心事件：

```json
{
  "type": "review",
  "content": {
    "verdict": "needs_revision",
    "quality_score": 6,
    "issues_count": 1,
    "major_issues": 1,
    "summary": "报告结构可用，但市场规模预测缺少来源。"
  }
}
```

## 9. 闭环样例

如果 Step 6 输出 `phase="re_researching"`：

1. Graph 发送 `phase="re_researching"`。
2. DeepScout 读取 `pending_search_queries`，执行补充搜索。
3. DeepScout 追加新事实并清空 `pending_search_queries`。
4. Graph 发送 `phase="rewriting"`。
5. LeadWriter 重新写作。
6. CriticMaster 再次审核。
7. 如果质量分达到阈值，则 Graph 发送 `research_complete`。

最终完成事件示例：

```json
{
  "type": "research_complete",
  "final_report": "完整报告 Markdown",
  "quality_score": 7,
  "facts_count": 24,
  "charts_count": 3,
  "iterations": 1,
  "references": [
    {
      "id": 1,
      "title": "示例行业报告",
      "link": "https://example.com/ai-chip-report",
      "source": "web"
    }
  ]
}
```

## 10. 端到端验收点

1. Step 1 产出可搜索的大纲，不少于 3 个章节。
2. Step 2 产出可追溯事实、数据点和前端搜索结果。
3. Step 3 产出结构化分析资产，包括数据点、图谱或 ECharts 图表。
4. Step 4 在数据足够时产出代码执行记录和 base64 图片图表。
5. Step 5 产出 Markdown 报告、章节草稿和引用列表。
6. Step 6 产出质量分、问题列表和明确路由。
7. 如果进入补充搜索或修订，`iteration` 必须递增并受 `max_iterations` 约束。
8. 最终 `research_complete` 必须包含报告、质量分、事实数、图表数、迭代数和引用。
