# Step 4 PRD: CodeWizard Analyze

## 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 阶段 | Step 4: CodeWizard - 代码分析与图表生成阶段 |
| 所属产品 | AI 深度研究助手 |
| 文档类型 | 基于当前代码反推的产品 PRD |
| 当前状态 | Draft |
| 覆盖范围 | 从结构化数据到 Python 分析代码、代码清理、安全检查、沙箱执行、自愈修复、base64 图表产物 |
| 不覆盖范围 | 原始搜索、ECharts 配置生成、报告写作、质量审稿、前端布局设计 |
| 主要代码依据 | `backend/app/service/deep_research_v2/agents/wizard.py`, `backend/app/service/deep_research_v2/state.py`, `backend/app/service/deep_research_v2/graph.py`, `frontend/src/pages/chat/index.tsx`, `frontend/src/pages/chat/component/research-detail/visualization.tsx`, `frontend/src/pages/chat/component/research-detail/process-report.tsx`, `tests/test_deep_research_v2_runtime.py` |

## 2. 产品背景

DataAnalyst 能生成结构化数据和 ECharts 配置，但研究报告中的部分图表需要更强的数据处理能力。例如清洗不同口径的数据、计算关键指标、生成高分辨率商业图表、捕获图片并嵌入报告。普通 LLM 直接输出图表描述无法满足这些需求。

CodeWizard 是 Analyze 阶段的第二位 Agent，也是当前链路中唯一有权执行 Python 代码的 Agent。它把数据点转化为可执行分析代码，在受限沙箱中运行，捕获 stdout、错误和 Matplotlib 图表，并把图表以 base64 形式送给前端和写作阶段。

由于代码执行具有安全和稳定性风险，CodeWizard PRD 的核心不只是“生成图表”，还包括代码清理、语法预检查、禁用危险操作、自愈修复、执行记录和调试可追踪性。

## 3. 问题定义

### 3.1 用户问题

用户希望深度研究报告中出现可信的数据分析图表，而不是静态描述或无法验证的图表截图。

### 3.2 产品需要解决的问题

系统需要在 CodeWizard 阶段完成：

- 判断数据点是否足够执行代码分析。
- 使用 LLM 生成简洁、可执行的 Python 分析代码。
- 清理 LLM 代码中的常见格式错误。
- 在执行前进行语法检查。
- 阻断危险 import、文件操作、网络访问和动态执行。
- 在沙箱中执行代码并捕获输出。
- 捕获 Matplotlib 图表并转换为 base64。
- 执行失败时调用 LLM 自动修复代码。
- 最多对失败代码重试 3 次。
- 记录代码执行结果和调试日志。
- 向前端发送 `code/code_result/code_fix/chart` 事件。

### 3.3 成功定义

CodeWizard 阶段成功的标志是：

- 对可分析数据生成过至少一次可审计代码执行记录。
- 成功执行时，`code_executions` 记录 `success/output/charts/retries/final_code`。
- 生成图表时，`charts` 中存在 `image_base64`。
- 前端能收到 `chart` 事件并渲染图片图表。
- 失败代码不会突破沙箱或中断整体研究流程。
- 代码清理和语法错误能被调试日志追踪。

## 4. 目标用户与使用场景

### 4.1 目标用户

- 投研和咨询用户：需要高质量趋势图、对比图、分布图。
- 行业研究人员：需要可解释的数据清洗和计算过程。
- 演示和面试场景用户：需要看到 Agent 生成代码、执行代码、产出图表的过程透明性。

### 4.2 核心场景

**场景 A：数据点驱动的分析代码**

系统收集 `data_points`，生成 Python 代码，构建 DataFrame，进行类型转换、清洗、绘图，并输出 stdout 或图表。

**场景 B：章节图表生成**

大纲章节标记 `requires_chart=true`，CodeWizard 为对应章节收集数据，生成图表代码，执行后将图片图表绑定 `section_id`。

**场景 C：无章节标记时的备选图表**

如果没有明确 `requires_chart` 的章节，但存在大纲，系统默认取前 2 个章节尝试生成图表。

**场景 D：代码失败自愈**

LLM 生成的代码存在语法或运行时错误。CodeWizard 捕获错误，调用修复 prompt，让 LLM 输出 `fixed_code`，最多重试 3 次。

**场景 E：安全拒绝**

代码包含 `open()`、`exec()`、`eval()`、`requests`、`os.` 等危险模式时，系统拒绝执行并记录错误。

## 5. 产品目标

### 5.1 当前阶段目标

CodeWizard 阶段应完成以下目标：

1. 当 `phase!="analyzing"` 但 `data_points >= 3` 时，可将阶段切换为 `analyzing`。
2. 当 `data_points < 3` 时安全跳过分析。
3. 生成 Python 代码时限制数据规模，避免把所有数据塞入代码。
4. 代码必须使用预导入模块，不依赖任意 import。
5. 执行前清理 Markdown 代码块、转义换行、错误续行符和粘连语句。
6. 执行前使用 `compile()` 做语法预检查。
7. 执行前使用正则黑名单阻断危险操作。
8. 在受限 `__builtins__` 环境中执行代码。
9. 允许使用 `pd/np/plt/sns` 等白名单能力。
10. 使用 `matplotlib` Agg 后端，捕获图片为 base64。
11. 失败时最多自动修复并重试 3 次。
12. 记录每次执行到 `state["code_executions"]`。
13. 生成图表时追加到 `state["charts"]`。
14. 发送代码、修复、执行结果和图表事件。

### 5.2 非目标

CodeWizard 阶段不负责：

- 调用搜索 API。
- 从网页文本提取事实。
- 生成 ECharts JSON 配置。
- 验证报告内容真实性。
- 写最终报告正文。
- 管理前端图表布局。
- 生产级强隔离容器执行。当前代码明确是简化沙箱。

## 6. 功能范围

### 6.1 Must Have

1. 数据点不足时跳过，不抛异常。
2. 支持生成通用分析代码。
3. 支持为最多 2 个章节生成图表代码。
4. 支持清理 LLM 输出代码。
5. 支持语法预检查，语法失败时不进入沙箱执行。
6. 支持危险模式检测。
7. 支持沙箱执行 Python 代码。
8. 支持捕获 stdout 和 stderr。
9. 支持捕获 Matplotlib 图表为 base64。
10. 支持执行失败后的 LLM 自愈重试。
11. 支持记录 `code_executions`。
12. 支持向前端发送 `chart` 事件。

### 6.2 Should Have

1. 生成代码应控制在 40 行以内。
2. 代码应只选取最关键的 5-10 个数据点。
3. 数据定义应使用列字典格式。
4. 创建 DataFrame 后应执行类型转换和 `dropna()`。
5. 图表应使用高分辨率、专业配色和清晰标题。
6. 执行失败应给出错误分析和修复说明。
7. 调试日志应写入可配置目录 `CODEWIZARD_DEBUG_DIR`。

### 6.3 Could Have

1. 支持 Docker 或进程级隔离替代当前线程内简化沙箱。
2. 支持图表像素级质量检查。
3. 支持图表与章节内容自动语义匹配。
4. 支持执行超时限制。
5. 支持对生成代码做 AST 白名单校验。

## 7. 输入输出契约

### 7.1 上游输入

| 字段 | 类型 | 来源 | 用途 |
| --- | --- | --- | --- |
| `query` | string | 用户问题 | 代码分析主题 |
| `phase` | string | Graph/DataAnalyst | 阶段判断 |
| `data_points` | array | DeepScout/DataAnalyst | 代码数据输入 |
| `facts` | array | DeepScout | 章节图表补充数据 |
| `outline` | array | ChiefArchitect | 需要生成图表的章节 |
| `charts` | array | DataAnalyst/CodeWizard | 追加图表产物 |
| `code_executions` | array | CodeWizard | 追加执行记录 |
| `messages` | array | Agent 共享消息区 | 追加事件 |

### 7.2 数据点输入

`data_points` 推荐结构：

```json
{
  "id": "dp_001",
  "name": "中国AI市场规模",
  "value": 5000,
  "unit": "亿元",
  "year": 2024,
  "source": "艾瑞咨询",
  "confidence": 0.9
}
```

CodeWizard 不强制所有字段都存在，但 `name/value/unit/year` 越完整，生成代码越稳定。

### 7.3 分析代码输出

LLM 应返回：

```json
{
  "analysis_plan": "清洗市场规模数据并绘制趋势图",
  "code": "sns.set_theme(style='whitegrid')\ndata = {'Year': [2020, 2024], 'Value': [3200, 8500]}\ndf = pd.DataFrame(data)\ndf['Value'] = pd.to_numeric(df['Value'], errors='coerce')\ndf = df.dropna()\nplt.figure(figsize=(12, 7), dpi=200)\nplt.plot(df['Year'], df['Value'])",
  "expected_outputs": ["市场规模趋势图"]
}
```

代码约束：

- 不写 `import` 语句。
- 不使用反斜杠续行。
- 不使用嵌套复杂列表定义 DataFrame。
- 不访问文件、网络、系统命令。
- 图表保存不是必须，系统会捕获当前 figure。

### 7.4 修复代码输出

执行失败后，LLM 修复结果应返回：

```json
{
  "error_analysis": "Value 列包含非数值字符",
  "fix_description": "使用 pd.to_numeric 并丢弃 NaN",
  "fixed_code": "data = {'Year': [2020, 2024], 'Value': [3200, 8500]}\ndf = pd.DataFrame(data)\ndf['Value'] = pd.to_numeric(df['Value'], errors='coerce')\ndf = df.dropna()"
}
```

### 7.5 代码执行记录

每次执行后追加：

```json
{
  "id": "exec_abcd1234",
  "code": "最终执行代码",
  "output": "stdout 内容",
  "error": null,
  "charts": ["base64_png"],
  "retries": 1,
  "timestamp": "2026-05-11T12:00:00"
}
```

### 7.6 图表输出

CodeWizard 生成的图表对象：

```json
{
  "id": "chart_abcd1234",
  "title": "市场规模",
  "chart_type": "generated",
  "data": [],
  "code": "生成图表的 Python 代码",
  "image_base64": "iVBORw0KGgo...",
  "section_id": "sec_1"
}
```

与 DataAnalyst ECharts 图表不同，CodeWizard 图表主要通过 `image_base64` 渲染。

## 8. 代码分析与执行流程

### 8.1 阶段进入流程

1. Graph 在 DataAnalyst 完成后运行 CodeWizard。
2. CodeWizard 检查 `state["phase"]`。
3. 如果不是 `analyzing` 且 `data_points >= 3`，切换为 `analyzing`。
4. 如果 `data_points < 3`，记录警告并返回。
5. 发送 `thought` 消息说明开始分析。

### 8.2 通用数据分析流程

1. 将所有数据点格式化为文本列表。
2. 调用 LLM 生成 `analysis_plan/code/expected_outputs`。
3. 保存 LLM 原始响应到调试日志。
4. 解析 JSON。
5. 取出 `code` 字段并转换为字符串。
6. 调用 `_clean_code()` 做格式清理。
7. 过滤明显无效代码。
8. 发送 `code` 事件。
9. 调用 `_execute_with_self_correction()` 执行。
10. 写入 `code_executions`。
11. 发送 `code_result` 事件。
12. 若生成图表，追加 `charts` 并发送 `chart` 事件。

### 8.3 章节图表流程

1. 筛选 `outline` 中 `requires_chart=true` 的章节。
2. 如果没有，默认使用前 2 个章节。
3. 最多处理 2 个章节。
4. 调用 `_get_section_data()` 获取章节事实中的数据点和全局数据点。
5. 无数据时跳过该章节。
6. 调用 LLM 生成图表代码。
7. 发送 `code` 事件。
8. 调用 `_execute_code()` 执行。
9. 捕获第一张图表并生成 `chart_entry`。
10. 追加 `state["charts"]`。
11. 发送 `chart` 事件。

### 8.4 代码清理流程

`_clean_code()` 负责：

- 移除 Markdown 代码块。
- 修复 JSON 转义引号。
- 区分字符串内 `\n` 和代码换行。
- 处理 `\\n`、`\[n]`、`[换行]` 等异常换行标记。
- 修复注释和代码粘连。
- 修复多个语句粘连在同一行。
- 移除行首异常反斜杠。
- 移除 `import/from` 语句。
- 移除 `plt.rcParams` 设置。
- 移除行尾反斜杠续行符。

### 8.5 安全执行流程

1. 将输入转换为字符串。
2. 清理代码。
3. 使用 `compile(code, "<string>", "exec")` 做语法预检查。
4. 语法失败时保存调试信息并返回错误。
5. 使用 `FORBIDDEN_PATTERNS` 检测危险代码。
6. 危险代码返回 `Code contains forbidden operations`。
7. 在线程池中调用 `_execute_in_sandbox()`。
8. 沙箱中使用 `matplotlib.use("Agg")`。
9. 预导入 `pandas/numpy/matplotlib/seaborn` 等允许模块。
10. 使用自定义 `safe_import` 限制 import。
11. 构造受限 `__builtins__`，禁用 `open` 和交互输入。
12. 捕获 stdout/stderr。
13. 如果当前 figure 有 axes，则保存为 PNG base64。
14. 返回 `success/output/error/charts`。

### 8.6 自愈重试流程

1. 首次执行失败后读取 `error` 和 `stdout`。
2. 如果已达到最大重试次数，返回失败。
3. 发送 `thought` 消息说明自动修复。
4. 调用 `_fix_code()`。
5. 如果返回 `fixed_code`，更新当前代码。
6. 发送 `code_fix` 事件。
7. 重试执行。
8. 最多重试 3 次。

## 9. 事件与前端展示需求

### 9.1 代码事件

```json
{
  "type": "code",
  "content": {
    "agent": "CodeWizard",
    "language": "python",
    "code": "df = pd.DataFrame(data)",
    "purpose": "数据分析"
  }
}
```

前端可以把该事件展示为过程日志或调试信息。

### 9.2 执行结果事件

```json
{
  "type": "code_result",
  "content": {
    "agent": "CodeWizard",
    "success": true,
    "output": "done",
    "has_chart": true,
    "retries": 1
  }
}
```

### 9.3 代码修复事件

```json
{
  "type": "code_fix",
  "content": {
    "agent": "CodeWizard",
    "error_analysis": "语法错误",
    "fix_description": "移除错误续行符",
    "retry": 1
  }
}
```

### 9.4 图表事件

```json
{
  "type": "chart",
  "content": {
    "agent": "CodeWizard",
    "title": "市场规模",
    "chart_type": "generated",
    "image_base64": "iVBORw0KGgo..."
  }
}
```

前端应：

- 将图表追加到当前消息的 `charts`。
- 将图表追加到当前分析详情 `detail.charts`。
- 在研究步骤条中更新图表数量。
- 在 Visualization 中优先按 `image_base64` 渲染图片。
- 在 ProcessReport 中支持图表内联插入。

### 9.5 检查点恢复

Graph 在整个 Analyze 阶段结束后保存：

```json
{
  "type": "analyzing",
  "status": "completed",
  "stats": {
    "charts": 3
  }
}
```

恢复时应从 checkpoint 的 UI 状态恢复 `charts`，同时兼容 ECharts 图表和 base64 图片图表。

## 10. 安全规则

### 10.1 禁止模式

当前禁止：

- `import os/sys/subprocess/requests/urllib/socket/shutil/pathlib/pickle/glob`
- `os.`
- `sys.`
- `subprocess.`
- `requests.`
- `urllib.`
- `socket.`
- `open(`
- `exec(`
- `eval(`
- `__import__`
- `compile(`
- `__builtins__`
- `__globals__`
- `__code__`

### 10.2 允许能力

允许使用：

- `pd`
- `np`
- `plt`
- `sns`
- `math`
- `statistics`
- `json`
- `collections`
- `re`
- 基础 Python 类型和函数，如 `len/range/enumerate/sorted/sum/min/max/round`。

### 10.3 沙箱边界

当前沙箱是进程内受限执行，不是强隔离容器。产品层应把它定义为“开发/演示级安全执行”，不能承诺生产级多租户隔离。

## 11. 非功能需求

### 11.1 可追踪性

每次执行必须记录原始代码、最终代码、输出、错误、图表和重试次数。

### 11.2 可调试性

调试日志应保存到 `CODEWIZARD_DEBUG_DIR`，未配置时使用系统临时目录下的 `codewizard_debug`。

### 11.3 稳定性

语法错误、危险代码、运行时异常均不能导致整个研究流程崩溃。

### 11.4 可解释性

向前端发送的 `code`、`code_result`、`code_fix` 应让用户理解系统做过哪些分析。

### 11.5 性能

图表章节当前最多处理 2 个，避免长时间阻塞研究流程。

## 12. 验收标准

### 12.1 功能验收

1. `data_points < 3` 时，CodeWizard 跳过并不抛异常。
2. `data_points >= 3` 时，可以生成并执行分析代码。
3. 代码清理能处理转义换行和 Markdown 代码块。
4. 语法错误能在沙箱前被拦截。
5. 禁止模式能阻断 `open()`、`eval()`、`requests` 等危险代码。
6. 成功执行时，`code_executions` 追加记录。
7. 生成 Matplotlib 图表时，`charts` 包含 `image_base64`。
8. 前端收到 `chart` 事件后能渲染图片图表。
9. 执行失败时，会触发自愈修复，最多重试 3 次。
10. 达到最大重试后返回失败记录，不中断整体流程。

### 12.2 异常验收

1. LLM 返回 list 类型 code 时，系统能转换为字符串。
2. LLM 返回非字符串 code 时，系统能转换为字符串。
3. 清理后代码过短或格式明显无效时，系统跳过执行。
4. 沙箱执行异常时，返回错误和 stdout。
5. 图表执行成功但无 figure axes 时，不生成空图表。
6. 调试文件写入目录可跨 Windows/Linux/macOS。

### 12.3 典型案例

以下案例用于说明阶段契约，不代表一次真实线上运行结果。

#### 12.3.1 输入

来自 DataAnalyst 的状态摘要：

```json
{
  "query": "研究 2024-2026 中国 AI 芯片市场格局、主要玩家、技术趋势和投资风险。",
  "phase": "analyzing",
  "data_points": [
    {"name": "中国 AI 芯片市场规模", "value": 500, "unit": "亿元", "year": 2024},
    {"name": "中国 AI 芯片市场规模", "value": 640, "unit": "亿元", "year": 2025},
    {"name": "中国 AI 芯片市场规模", "value": 820, "unit": "亿元", "year": 2026}
  ],
  "outline": [
    {
      "id": "sec_1",
      "title": "市场规模与增长趋势",
      "section_type": "quantitative",
      "requires_chart": true
    }
  ],
  "charts": [],
  "code_executions": []
}
```

#### 12.3.2 调用链与方案

1. Graph 在 DataAnalyst 后调用 `CodeWizard.process(state)`。
2. CodeWizard 检查 `data_points` 数量；本例为 3 条，允许进入分析。
3. `_analyze_data()` 将数据点格式化后，通过 `ANALYSIS_PROMPT` 调用 LLM 生成 Python 代码。
4. `_clean_code()` 清理 Markdown 代码块、转义换行、错误续行符和粘连语句。
5. `_execute_code()` 先用 `compile()` 做语法预检查。
6. `_is_code_safe()` 检查危险模式，如 `open()`、`requests`、`eval()`。
7. `_execute_in_sandbox()` 在线程中运行受限环境，预置 `pd/np/plt/sns`。
8. 如果执行失败，`_execute_with_self_correction()` 调用 `_fix_code()`，最多重试 3 次。
9. 生成 Matplotlib figure 后，系统把 PNG 捕获为 base64，追加到 `state["charts"]`。

#### 12.3.3 输出

代码事件示例：

```json
{
  "type": "code",
  "content": {
    "agent": "CodeWizard",
    "language": "python",
    "purpose": "数据分析",
    "code": "data = {'Year': [2024, 2025, 2026], 'Market': [500, 640, 820]}\ndf = pd.DataFrame(data)\ndf['Market'] = pd.to_numeric(df['Market'], errors='coerce')\nplt.figure(figsize=(12, 7), dpi=200)\nplt.plot(df['Year'], df['Market'], marker='o')"
  }
}
```

状态写入示例：

```json
{
  "code_executions": [
    {
      "id": "exec_a1b2c3d4",
      "code": "最终执行代码",
      "output": "",
      "error": null,
      "charts": ["base64_png_string"],
      "retries": 0,
      "timestamp": "2026-05-11T12:00:00"
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

图表事件示例：

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

#### 12.3.4 验收点

- 不足 3 个数据点时应跳过，不执行代码。
- 代码语法失败时应在沙箱前短路。
- 包含危险模式时应拒绝执行。
- 成功图表必须写入 `charts.image_base64`。
- 每次执行必须写入 `code_executions`，保留最终代码和重试次数。

## 13. 当前代码依据

- `CodeWizard.process()`：阶段判断、数据点数量判断、运行分析和图表生成。
- `CodeWizard._analyze_data()`：生成通用分析代码、执行、自愈、记录结果、发送图表事件。
- `CodeWizard._execute_with_self_correction()`：失败后修复重试。
- `CodeWizard._fix_code()`：调用 LLM 生成修复代码。
- `CodeWizard._generate_charts()`：按章节生成最多 2 个图表。
- `CodeWizard._get_section_data()`：按章节和全局数据点收集图表数据。
- `CodeWizard._clean_code()`：清理 LLM 代码输出。
- `CodeWizard._execute_code()`：清理、语法预检查、安全检查和调用沙箱。
- `CodeWizard._is_code_safe()`：正则黑名单检测。
- `CodeWizard._execute_in_sandbox()`：受限执行环境、stdout/stderr 捕获、图片捕获。
- `ResearchState`：定义 `charts/code_executions/data_points/messages`。
- `frontend/src/pages/chat/index.tsx`：处理 `chart/charts/code_result` 等事件。
- `tests/test_deep_research_v2_runtime.py`：覆盖 CodeWizard 调试目录、非法代码处理、语法失败短路等运行时行为。

## 14. 边界与不做范围

- 不承诺生产级安全沙箱。
- 不执行任意用户上传代码，只执行 LLM 在受控 prompt 下生成的代码。
- 不保证每次都会生成图表，数据不足或代码失败时可以为空。
- 不把 CodeWizard 生成的图片图表转换为 ECharts 配置。
- 不负责最终报告是否引用所有图表。

## 15. 当前实现限制与专业化改造建议

本节记录当前 Step 4 的实现边界和后续专业化改造方向。以下内容不改变当前代码行为，作为后续统一处理的产品和工程依据。

### 15.1 输入数据来源限制

当前 CodeWizard 读取的是同一个 `ResearchState` 中已经累积的 `data_points/facts/outline/charts`，不是只读取 Step 3 的单独产物。

`data_points` 可能来自：

1. DeepScout 从搜索结果事实中抽取的数据点。
2. DataAnalyst 从事实库中二次抽取的数据点。
3. 补充搜索或后续迭代追加的数据点。

因此，Step 4 的真实输入应定义为“截至当前 Analyze 阶段的累计结构化数据”，而不是“Step 3 输出文件”。后续如果要提高可追踪性，应为每个 `data_point` 增加：

- `origin_agent`
- `origin_fact_id`
- `source_url`
- `extraction_step`
- `confidence`
- `lineage`

### 15.2 上下文承载限制

当前 `_analyze_data()` 会把 `state["data_points"]` 全量格式化为文本后放入 prompt：

```python
for dp in state["data_points"]:
    data_summary.append(f"- {dp.get('name')}: {dp.get('value')} {dp.get('unit', '')} ({dp.get('year', 'N/A')})")
```

这意味着数据量稍大时会出现三个问题：

1. prompt 上下文迅速膨胀。
2. LLM 可能漏读、误读或改写数据。
3. 无法保证生成代码中的数值与输入数据完全一致。

章节图表路径当前稍有限制，会额外取 `state["data_points"][:10]`，但仍会把章节相关数据 JSON 化后交给 LLM 生成代码。

专业化目标方案应改为：

1. 原始数据存储在结构化表、DataFrame、数据库或文件中，不直接全量进入 prompt。
2. LLM 只读取字段 schema、样本、统计摘要和可选分析目标。
3. 数据筛选、聚合、排序、单位换算由确定性代码完成。
4. 图表生成只接收 chart-ready dataset。
5. 每个图表 series 中的数值必须能回溯到输入数据点。

### 15.3 代码生成方式限制

当前 CodeWizard 不是“从预置函数库中选择分析函数”。当前实现是：

1. LLM 根据数据点摘要生成 Python 代码。
2. 后端清理 LLM 代码。
3. 后端做语法预检查和危险模式检测。
4. 后端在简化沙箱中执行该代码。
5. 执行失败时再次调用 LLM 生成 `fixed_code`。

关键风险是：分析逻辑和绘图逻辑均由 LLM 即时生成，系统只能做有限的代码安全检查，不能保证分析方法、数值处理和图表选择完全正确。

专业化目标方案应改为：

```text
LLM 判断分析意图
    -> 选择预置 AnalysisPlan
    -> 后端确定性函数执行
    -> 后端生成 chart-ready data
    -> 后端模板生成 ECharts 或图片
    -> LLM 只负责解释图表含义
```

推荐预置能力包括：

- `normalize_units(data_points)`
- `filter_data_points(metric, section_id, year_range)`
- `calculate_growth_rate(series)`
- `calculate_cagr(start_value, end_value, start_year, end_year)`
- `build_time_series_dataset(metric, values)`
- `build_category_comparison_dataset(categories, values)`
- `build_distribution_dataset(categories, shares)`
- `validate_chart_data(chart_data, source_data)`
- `render_chart_from_template(chart_type, chart_data)`

### 15.4 图表选择限制

当前图表类型主要由 LLM 在 prompt 中根据规则自行选择。虽然 prompt 中写了“时间序列用折线图、分类比较用柱状图、占比分布用饼图”，但这不是确定性规则。

专业化目标方案应引入图表选择规则引擎：

| 数据形态 | 推荐图表 | 规则 |
| --- | --- | --- |
| 单指标跨年份 | line | `x=year`, `y=value`, 年份数量 >= 2 |
| 多类别同一指标 | bar | `x=category`, `y=value` |
| 占比结构 | pie 或 stacked_bar | 单位为 `%`，类别总量可校验 |
| 多指标多主体 | grouped_bar 或 radar | 主体数和指标数均大于 1 |
| 排名 | horizontal_bar | 存在 rank 或可排序 value |
| 实体关系 | graph | 输入为 nodes/edges |

LLM 可以给出图表建议和解释理由，但最终图表类型应由规则引擎或用户确认决定。

### 15.5 数据一致性校验要求

后续生产化版本中，CodeWizard 输出任何图表前必须通过数据一致性校验：

1. 图表使用的所有数值必须来自 `data_points` 或确定性计算结果。
2. 图表不得引入 prompt 中不存在的新数值。
3. 单位必须一致；单位不同必须先显式换算。
4. x/y 轴长度必须一致。
5. 时间序列年份不得乱序。
6. 百分比图表必须检查合计范围。
7. 每个图表应保留 `source_data_point_ids`。
8. 每个计算指标应保留公式和输入值。

当前文档中的 CodeWizard 能力应被理解为 demo/prototype 级能力；面向高敏、金融、医疗、政策、投研等场景时，必须完成上述改造后才可作为严肃分析链路。

## 16. 后续需求变更候选

### 16.1 容器化沙箱

**变更说明**：使用 Docker 或隔离执行服务运行代码。

**价值**：提升安全边界，适合生产多租户。

**影响范围**：CodeWizard 执行器、部署配置、超时和资源限制。

### 16.2 执行超时

**变更说明**：为每次代码执行设置超时。

**价值**：避免 LLM 生成死循环或超慢计算阻塞流程。

**影响范围**：`_execute_code()`、线程池或进程池实现、错误展示。

### 16.3 AST 白名单校验

**变更说明**：使用 Python AST 校验替代或补充正则黑名单。

**价值**：降低绕过安全规则的风险。

**影响范围**：安全检查模块、测试覆盖。

### 16.4 图表质量检查

**变更说明**：对生成的图表做尺寸、非空、标题、轴标签检查。

**价值**：减少空白图、乱码图和不可读图。

**影响范围**：图表捕获流程、前端降级展示、测试。

### 16.5 章节图表匹配优化

**变更说明**：按章节语义和数据点来源选择图表，而不是默认前 2 个章节。

**价值**：提高图表与正文相关性。

**影响范围**：`_get_section_data()`、LeadWriter 图文混排。

### 16.6 分析计划与预置函数库

**变更说明**：将 LLM 生成代码改为 LLM 输出 `AnalysisPlan`，由后端调用预置确定性分析函数。

**价值**：降低 LLM 改写数据、生成错误代码和选择错误图表的风险。

**影响范围**：CodeWizard prompt、分析函数库、图表模板、数据一致性测试。

### 16.7 图表数据一致性校验

**变更说明**：生成图表前后校验图表数据是否全部来自输入数据或可解释计算。

**价值**：保障严肃数据分析场景中的数值可信度。

**影响范围**：`charts` schema、`code_executions` schema、Review 阶段质量规则。

## 17. 待确认问题

1. 当前沙箱是否只定位演示环境，还是计划进入生产？
2. CodeWizard 的图表数量上限是否固定为 2，还是后续根据报告章节动态调整？
3. 用户是否需要在前端看到完整代码，还是只展示执行摘要？
4. 失败代码的调试日志是否需要进入数据库，还是保留在本地文件即可？
5. 后续生产方案是否接受“LLM 只输出 AnalysisPlan，不再直接生成执行代码”？
6. 图表类型是否由规则引擎确定，还是需要用户在前端确认？
