# v2 Design Spec — 证券广告主基本面研究系统

> 创建：2026-04-27（重写版，旧版本废弃）
> 状态：Draft（待 spec review + user review）
> 项目：industry-information-assistant · v2

---

## 1. 背景与定位

### 1.1 业务背景（应用逻辑）

证券广告投放线上公式：

```
ECPM = ctr × cvr × cpa × 扰动系数
```

扰动系数针对**意愿中等用户**做精准曝光（意愿高不扰动、意愿低打压）。扰动模型主要用 embedding + 浅 NLP，缺少**广告主基本面**类信号。

业务流：

```
[本项目] 针对证券广告主 → 做 deep research → 输出基本面研究报告（含结构化评分）
                                                    │
                                                    ▼
[项目外业务] 拿这份判断 → 由人 / 下游模型决定怎么用（调整扰动系数 / 编辑策略 / 黑白名单）
```

**项目边界明确**：v2 只生产研究报告 + 结构化评分。**怎么使用**这份评分不在本项目范围。

### 1.2 v2 的定位

> 面向**单家金融广告主**（证券 / 银行 / 保险 / 基金类）的多智能体 Deep Research 系统。给定一个广告主主体，输出一份 markdown 研究报告，**报告末尾包含 5 维度量化评分**（rubric-based，可追溯）。

**说明**：v1 rubric 是金融广告主通用版，重心在证券类；银行 / 保险 / 基金类使用同一份 rubric 作为 baseline，跨类目 rubric 微调列入 future work（见 §7 R6）。

### 1.3 现状（已存在的能力）

引擎本体已经成熟，**本次改造不动**：

- LangGraph 状态机：plan → research → analyze → write → review →（必要时 revise）
- 6 Agent：ChiefArchitect / DeepScout / CodeWizard / DataAnalyst / LeadWriter / CriticMaster
- 多源检索：Bocha web + Milvus + Elasticsearch + 本地 KB + source_tracing 递归
- 检查点续传 / SSE 14 种事件流 / 知识图谱抽取 / ECharts 图表生成
- 前端 30+ 事件解析 / 可视化渲染

实测：单 query 跑通端到端约 24 分钟，抓取 ~200 信源，自动生成 6 章大纲 + KG + 图表。

---

## 2. Goals & Non-Goals

### 2.1 Goals

| # | Goal | 验收 |
|---|------|------|
| **G1** | 业务定位重塑：4 行业卡片改证券广告主类目（证券 / 银行 / 保险 / 基金）+ 关键词 + 推荐问题对位 | 首页视觉对位；从卡片进入 chat 默认 query 形态为「{广告主} 基本面研究」 |
| **G2** | 5 维度评分 rubric 系统：定义 + 权重 + 5 档锚点 | `scoring_rubric.yaml` 包含 D1-D5 完整定义；可独立加载验证 |
| **G3** | LeadWriter 加 SCORING_PROMPT：报告写完后 LLM 按 rubric 给每维度评分 + reasoning | 输出严格 JSON，含 score / anchor / evidence_facts / reasoning |
| **G4** | 报告末尾 markdown 渲染：综合得分 + 5 维度表 + 评分依据明细 + 引用一致性检查 | 渲染格式与 §5.5 一致 |
| **G5** | 数据不足异常处理：信源 < 3 个的维度标 "数据不足"，分数固定 50（中性）+ 警告 | 测试用例覆盖 |
| **G6** | Frontend U2 改造：chat-trace 页面 LangSmith 风格重建 | 视觉与 `ui-mockups.html` U2 tab 一致 |
| **G7** | interview-prep.md 同步更新：新定位 + 新故事 + Demo 流程 | 替换为 v2 当前定位 |

### 2.2 Non-Goals（明确不做）

| 不做 | 原因 |
|---|---|
| 行业级研究 pipeline | 研究单位 = 单广告主，行业 context 内嵌在公司研究里，不另起 pipeline |
| pydantic SignalFeatureVector schema / Feature Store / Batch Scheduler | over-engineer，不需要持久化 / 批处理基础设施 |
| 离线评估 demo（sklearn AUC 对比等） | 不号称效果验证，避免假数据陷阱 |
| 接下游扰动模型 / 业务系统 | 项目边界外 |
| Mode A / Mode B 双输出引擎 | 单一输出 = 报告（含 rubric 评分），不做特征向量产出 |
| antd 替换 / 全局 UI 重写 | 仅 chat-trace 页面改，其他 8 页面不动 |
| 重写 LangGraph 状态机 / 6 Agent 实现 | 已成熟，仅追加 SCORING_PROMPT |
| 监管文件解读 / 合规审计场景 | 不在范围 |

---

## 3. 改造范围一览

| 维度 | 现状 | 改造后 |
|---|---|---|
| 后端 LangGraph 状态机 | 6 Agent / plan→research→analyze→write→review→revise | **不动** |
| 后端 11 router / 22 service | 已存在 | **不动** |
| 多源检索 / KG / 图表 / 检查点 / SSE | 全部已有 | **不动** |
| 前端框架（React 19 + antd + ECharts） | 已存在 | **不动** |
| 8 个非 chat 页面 | antd 默认 | **不动** |
| **首页 4 行业卡片** | 智慧交通 / 金融科技 / 医疗 / 能源 | **改**：证券 / 银行 / 保险 / 基金（广告主类目） |
| **关键词 / 推荐问题** | 4 行业各自的 keywords | **改**：换成对应广告主基本面研究词 |
| **chat-trace 页面 UI** | 步骤条 + drawer + KG 面板 | **改**：LangSmith 风格可折叠 span 树（暗色 inset 嵌浅色 antd shell） |
| **报告末尾产出** | 6 章 markdown + 引用列表 | **加**：综合得分 + 5 维度评分表 + 评分依据明细 |
| **新增配置文件** | — | **新建** `scoring_rubric.yaml` |
| **评分逻辑位置** | — | **新建** `scoring_service.py`（在 service 层 post-graph 调用，**不在 LeadWriter 内**，避免 revise 循环重复评分） |
| **ResearchState 字段** | 无 advertiser_name | **加** `advertiser_name: Optional[str]`，由 ChiefArchitect 在 plan 阶段从 query 提取 |

---

## 4. 5 维度评分系统（核心）

### 4.1 维度定义与权重

| # | 维度 | 含义 | 权重 | 关键信号源 |
|---|------|------|-----|-----------|
| **D1** | 业务扩张度 | 营收增长 / 新业务线 / 市场拓展 | 25% | 财报、公告、新闻、官网 |
| **D2** | 监管态度 | 牌照变化 / 处罚记录 / 合规事件 | 25% | 证监会、交易所、自律协会公告 |
| **D3** | 品牌活跃度 | 媒体声量 / 舆情极性 / 高管曝光 / 行业奖项 | 20% | 财经媒体、行业排行榜、自媒体 |
| **D4** | 竞争地位 | 同业排名变化 / 客户结构 / 差异化战略 | 15% | 同业研报、市占率数据 |
| **D5** | 创新与数字化 | 科技投入 / 新产品 / 数字化转型 | 15% | 公司公告、科技新闻、专利 |
|   | **总计** | | **100%** |  |

权重为默认值，由 `scoring_rubric.yaml` 配置，可调。

### 4.2 Rubric 锚点（5 档评分尺度）

每维度按 0-100 分，分 5 档锚点。LLM 按 rubric 给分，必须在档位区间内并选择档位上 / 中 / 下沿位置。

#### D1 业务扩张度

| 分数 | 档位 | 触发条件锚点 |
|---|---|---|
| 85-100 | 强扩张 | 季度营收同比 > +30% **或** 新业务线 ≥ 2 **或** 跨区域重大扩张 |
| 65-84 | 稳扩张 | 季度营收同比 +10~+30% **或** 1 项重大新产品 / 战略合作 |
| 45-64 | 平稳 | 营收同比 -10~+10% **或** 维持现状无重大动作 |
| 25-44 | 收缩 | 营收同比 -10~-30% **或** 主动退出某业务 / 关键客户流失 |
| 0-24 | 危机 | 营收同比 < -30% **或** 业务暴雷 / 大规模裁员 / 流动性危机 |

#### D2 监管态度

| 分数 | 档位 | 触发条件锚点 |
|---|---|---|
| 85-100 | 监管利好 | 获新业务许可 / 被树为典型 / 牌照范围扩展 |
| 65-84 | 监管中性偏好 | 通过例行检查无问题 / 主动合规升级 |
| 45-64 | 监管中性 | 无重大事件 / 也无利好（混合或空白） |
| 25-44 | 监管警示 | 收到警告 / 行政指导 / 媒体披露的合规问题 |
| 0-24 | 监管危机 | 立案调查 / 重大处罚 / 牌照撤销风险 / 高管被采取措施 |

#### D3 品牌活跃度

| 分数 | 档位 | 触发条件锚点 |
|---|---|---|
| 85-100 | 强活跃 | 大型行业奖项 / 头部财经媒体头条 / 高管多次公开发声 |
| 65-84 | 偏活跃 | 中等媒体曝光 / 行业活动参与 / 高管 1-2 次访谈 |
| 45-64 | 平稳 | 常规曝光 / 维持媒体存在 |
| 25-44 | 偏冷 | 媒体声量明显下降 / 行业奖项空白 |
| 0-24 | 冷却 | 长期无媒体曝光 / 负面话题主导 |

#### D4 竞争地位

| 分数 | 档位 | 触发条件锚点 |
|---|---|---|
| 85-100 | 行业领先 | 市占率 top 3 持续提升 / 关键差异化优势确立 |
| 65-84 | 稳中偏强 | 市占率维持 top 5-10 / 在某细分领先 |
| 45-64 | 中位 | 中段位置无明显变化 |
| 25-44 | 边缘化 | 市占率下滑 / 关键客户流失 |
| 0-24 | 出清 | 退居末位 / 关键业务被对手吃掉 |

#### D5 创新与数字化

| 分数 | 档位 | 触发条件锚点 |
|---|---|---|
| 85-100 | 强创新 | 业界首发新产品 / 重大科技合作 / AI / 大模型重大投入 |
| 65-84 | 持续推进 | 数字化项目按节奏推进 / 1-2 项新功能上线 |
| 45-64 | 跟跑 | 跟随同业做基础数字化 |
| 25-44 | 落后 | 关键科技投入显著落后同业 |
| 0-24 | 停滞 | 长期无数字化进展 / 数字化项目失败 |

### 4.3 配置文件 `scoring_rubric.yaml`

```yaml
# backend/app/service/deep_research_v2/scoring_rubric.yaml
version: "1.0"
domain: "securities_advertiser"
score_range: [0, 100]
neutral_score: 50
min_evidence_count: 3   # 信源数 < 此值 → 标记"数据不足"

dimensions:
  D1:
    name: "业务扩张度"
    weight: 0.25
    description: "营收增长 / 新业务线 / 市场拓展"
    signal_sources: [财报, 公告, 新闻, 官网]
    rubric:
      - { range: [85, 100], anchor: "强扩张", trigger: "季度营收同比 > +30% 或 新业务线 ≥ 2 或 跨区域重大扩张" }
      - { range: [65, 84],  anchor: "稳扩张", trigger: "季度营收同比 +10~+30% 或 1 项重大新产品/战略合作" }
      - { range: [45, 64],  anchor: "平稳",   trigger: "营收同比 -10~+10% 或 维持现状无重大动作" }
      - { range: [25, 44],  anchor: "收缩",   trigger: "营收同比 -10~-30% 或 主动退出某业务/关键客户流失" }
      - { range: [0,  24],  anchor: "危机",   trigger: "营收同比 < -30% 或 业务暴雷/大规模裁员/流动性危机" }
  
  D2:
    name: "监管态度"
    weight: 0.25
    description: "牌照变化 / 处罚记录 / 合规事件"
    signal_sources: [证监会, 银保监会, 交易所, 自律协会]  # 覆盖证券+银行+保险+基金
    rubric:
      - { range: [85, 100], anchor: "监管利好",     trigger: "获新业务许可 / 被树为典型 / 牌照范围扩展" }
      - { range: [65, 84],  anchor: "监管中性偏好", trigger: "通过例行检查无问题 / 主动合规升级" }
      - { range: [45, 64],  anchor: "监管中性",     trigger: "无重大事件 / 也无利好（混合或空白）" }
      - { range: [25, 44],  anchor: "监管警示",     trigger: "收到警告 / 行政指导 / 媒体披露的合规问题" }
      - { range: [0,  24],  anchor: "监管危机",     trigger: "立案调查 / 重大处罚 / 牌照撤销风险" }
  
  D3:
    name: "品牌活跃度"
    weight: 0.20
    description: "媒体声量 / 舆情极性 / 高管曝光 / 行业奖项"
    signal_sources: [财经媒体, 行业排行榜, 自媒体]
    rubric:
      - { range: [85, 100], anchor: "强活跃", trigger: "大型行业奖项 / 头部财经媒体头条 / 高管多次公开发声" }
      - { range: [65, 84],  anchor: "偏活跃", trigger: "中等媒体曝光 / 行业活动参与 / 高管 1-2 次访谈" }
      - { range: [45, 64],  anchor: "平稳",   trigger: "常规曝光 / 维持媒体存在" }
      - { range: [25, 44],  anchor: "偏冷",   trigger: "媒体声量明显下降 / 行业奖项空白" }
      - { range: [0,  24],  anchor: "冷却",   trigger: "长期无媒体曝光 / 负面话题主导" }
  
  D4:
    name: "竞争地位"
    weight: 0.15
    description: "同业排名变化 / 客户结构 / 差异化战略"
    signal_sources: [同业研报, 市占率数据]
    rubric:
      - { range: [85, 100], anchor: "行业领先",   trigger: "市占率 top 3 持续提升 / 关键差异化优势确立" }
      - { range: [65, 84],  anchor: "稳中偏强",   trigger: "市占率维持 top 5-10 / 在某细分领先" }
      - { range: [45, 64],  anchor: "中位",       trigger: "中段位置无明显变化" }
      - { range: [25, 44],  anchor: "边缘化",     trigger: "市占率下滑 / 关键客户流失" }
      - { range: [0,  24],  anchor: "出清",       trigger: "退居末位 / 关键业务被对手吃掉" }
  
  D5:
    name: "创新与数字化"
    weight: 0.15
    description: "科技投入 / 新产品 / 数字化转型"
    signal_sources: [公司公告, 科技新闻, 专利]
    rubric:
      - { range: [85, 100], anchor: "强创新",     trigger: "业界首发新产品 / 重大科技合作 / AI/大模型重大投入" }
      - { range: [65, 84],  anchor: "持续推进",   trigger: "数字化项目按节奏推进 / 1-2 项新功能上线" }
      - { range: [45, 64],  anchor: "跟跑",       trigger: "跟随同业做基础数字化" }
      - { range: [25, 44],  anchor: "落后",       trigger: "关键科技投入显著落后同业" }
      - { range: [0,  24],  anchor: "停滞",       trigger: "长期无数字化进展 / 数字化项目失败" }
```

### 4.4 SCORING_PROMPT 设计

#### 调用位置：service 层 post-graph hook（**不在 LeadWriter 内**）

为什么不放 LeadWriter 内：
- LangGraph 有 review→revise 循环，若评分嵌入 `_synthesize_report`，每轮 revise 都重新评分（浪费 LLM 调用 + 评分目标在变化中）
- 评分应基于**最终稳定的 final_report + facts**，不应被 revise 中间态触发

实施位置：`backend/app/service/deep_research_v2/scoring_service.py`（新建）

```python
# scoring_service.py
async def score_after_research(state: ResearchState) -> dict:
    """
    在 LangGraph 跑完（state["phase"] == "completed"）后调用。
    输入完整最终 state，返回评分结果 + 渲染后的 markdown 段落。
    """
    rubric = load_rubric()
    score_json = await _llm_score(state, rubric)        # LLM 调用
    score_json = _clamp_to_anchor_range(score_json, rubric)  # Python 区间夹紧
    consistency = _compute_consistency_metrics(state)   # Python 派生
    overall, tier = _compute_overall(score_json, rubric)  # Python 加权
    markdown = _render_scoring_markdown(score_json, consistency, overall, tier)
    return {"json": score_json, "consistency": consistency, "overall": overall, "tier": tier, "markdown": markdown}
```

`DeepResearchV2Service.research()` 在 graph 跑完且 `final_report` 非空后调用 `score_after_research()`，将返回的 markdown 拼到 `final_report` 末尾，再发 SSE event `research_complete`。

#### advertiser_name 提取

ChiefArchitect 的 plan 节点扩展 prompt：要求从 query 中提取 advertiser_name 写入 state。Fallback：若提取失败，advertiser_name = state["query"][:30]（截断 query 前 30 字符）。

#### Evidence anchor：用 source_url，不依赖 fact_id

state["facts"] 是 List[Dict]，DeepScout 创建时 `id` 字段不一定保证存在。改用 `source_url + summary` 作为证据锚点。

#### SCORING_PROMPT（注意 JSON 模板的 `{{` `}}` 转义）

```python
SCORING_PROMPT = """你是金融行业资深分析师，需要按 rubric 对广告主基本面打分。

## 评分对象
广告主：{advertiser_name}
研究主题：{query}

## 评分 Rubric
{rubric_yaml_content}

## 可用事实（共 {fact_count} 条）
{facts}

## 任务
按 rubric 对每个维度（D1-D5）评分。每个维度必须：
1. 选定档位（rubric 里的 anchor 之一）
2. 给出该档位区间内的具体分数（如稳扩张档 65-84 内选 72，并在 reasoning 说明为什么是中位而非上下沿）
3. 列出至少 3 个独立信源（distinct source_url）支持该评分
4. 在 reasoning 中说明为什么不是相邻档位

## 数据不足规则
若某维度相关独立信源数 < 3：
- score 固定为 50（中性）
- anchor 标 "数据不足"
- evidence 列出已有的（少于 3 也列）
- reasoning 必须说明信源不足，不要硬套档位

## 输出格式（严格 JSON）
{{
  "scores": {{
    "D1": {{
      "score": 72,
      "anchor": "稳扩张",
      "evidence": [
        {{"summary": "Q1 营收同比 +18%", "source_url": "https://..."}},
        {{"summary": "新业务线启动", "source_url": "https://..."}}
      ],
      "reasoning": "增速 +18% 落入 +10~+30% 区间，新业务线尚未贡献营收，故选档位中位 72，未到上沿 84。"
    }},
    "D2": {{ ... }},
    "D3": {{ ... }},
    "D4": {{ ... }},
    "D5": {{ ... }}
  }}
}}

注意：所有 JSON 字符串使用双引号；不要输出 Markdown 代码围栏；不要在 JSON 外加任何文字。
"""
```

`consistency_check` 字段（total_sources / official_source_ratio / activity_density_7d/30d）**不让 LLM 计算**，由 `_compute_consistency_metrics(state)` Python 端从 `state["facts"]` 派生（见 §4.5）。

### 4.5 Python-side 后处理（综合得分 + 一致性 + 渲染）

LLM 返回 JSON 后，`scoring_service.py` 内 4 个 helper 完成所有后处理，**避免 LLM 计算数值类指标**：

#### 4.5.1 区间夹紧（防 LLM 越档）

```python
def _clamp_to_anchor_range(score_json: dict, rubric: dict) -> dict:
    """anchor 优先：若 LLM 给的 score 不在 anchor 对应 range，夹紧到 range 内（向 anchor 中位夹）"""
    for dim_id, data in score_json["scores"].items():
        anchor = data["anchor"]
        if anchor == "数据不足":
            data["score"] = 50  # 强制中性
            continue
        # 找到 anchor 对应的 range
        rubric_dim = rubric["dimensions"][dim_id]
        range_for_anchor = next(
            (r["range"] for r in rubric_dim["rubric"] if r["anchor"] == anchor),
            None
        )
        if range_for_anchor and not (range_for_anchor[0] <= data["score"] <= range_for_anchor[1]):
            # 越档：夹到最近边界
            data["score"] = max(range_for_anchor[0], min(range_for_anchor[1], data["score"]))
            data["_clamped"] = True  # 标记已夹紧
    return score_json
```

#### 4.5.2 综合得分

```python
def _compute_overall(scores_json: dict, rubric: dict) -> tuple[float, str]:
    weighted = sum(
        scores_json["scores"][dim]["score"] * rubric["dimensions"][dim]["weight"]
        for dim in scores_json["scores"]
    )
    if weighted >= 75: tier = "强正向"
    elif weighted >= 60: tier = "偏正向"
    elif weighted >= 45: tier = "中性"
    elif weighted >= 30: tier = "偏负向"
    else: tier = "强负向"
    return weighted, tier
```

#### 4.5.3 一致性指标（Python 端从 state 派生，**不让 LLM 算**）

```python
def _compute_consistency_metrics(state: ResearchState) -> dict:
    facts = state["facts"]
    
    # 独立信源数：基于 source_url 去重
    distinct_urls = {f.get("source_url") for f in facts if f.get("source_url")}
    total_sources = len(distinct_urls)
    
    # 官方源占比：source_type == "official" 的 fact 数 / 总 fact 数
    OFFICIAL_TYPES = {"official"}  # rubric 也可定义扩展集
    official_count = sum(1 for f in facts if f.get("source_type") in OFFICIAL_TYPES)
    official_ratio = official_count / len(facts) if facts else 0.0
    
    # 时间分布：基于 extracted_at（ISO 字符串），缺失时跳过（不算入）
    now = datetime.utcnow()
    def in_window(f, days):
        s = f.get("extracted_at")
        if not s: return False
        try: return parse(s) >= now - timedelta(days=days)
        except: return False
    
    return {
        "total_sources": total_sources,
        "official_source_ratio": round(official_ratio, 2),
        "activity_density_7d": sum(1 for f in facts if in_window(f, 7)),
        "activity_density_30d": sum(1 for f in facts if in_window(f, 30)),
    }
```

#### 4.5.4 Markdown 渲染（追加到 final_report 末尾）：

```markdown
## 基本面判断（{date}）

### 综合得分：{overall_score:.1f} / 100  [{tier}]

| 维度 | 得分 | 权重 | 加权贡献 | 档位 |
|---|---:|---:|---:|---|
| D1 业务扩张度  | {D1.score} | 25% | {D1.score*0.25:.1f} | {D1.anchor} |
| D2 监管态度    | {D2.score} | 25% | {D2.score*0.25:.1f} | {D2.anchor} |
| D3 品牌活跃度  | {D3.score} | 20% | {D3.score*0.20:.1f} | {D3.anchor} |
| D4 竞争地位    | {D4.score} | 15% | {D4.score*0.15:.1f} | {D4.anchor} |
| D5 创新与数字化| {D5.score} | 15% | {D5.score*0.15:.1f} | {D5.anchor} |
| **综合**     | — | 100% | **{overall_score:.1f}** | **{tier}** |

---

### 评分依据明细

#### D1 业务扩张度: {score} / {anchor}
**对照 rubric**：{anchor} 档 ({range}) 触发条件 = {trigger}

**关键事实**：
- {fact_summary}（[{source_name}]({source_url})）
- ...

**评分理由**：{reasoning}

[D2-D5 同结构]

---

### 引用一致性检查
- 共引用 {total_sources} 个独立信源
- 官方信源占比 {official_ratio:.0%}
- 信源时间分布：7 天内 {act_7d} 件 / 30 天内 {act_30d} 件
- 信源充足维度：{ok_dims}
- 数据不足维度：{insufficient_dims}（已置中性 50）
```

### 4.6 异常处理

| 异常 | 处理 |
|---|---|
| LLM 输出 JSON 格式错误 | 重试 1 次（用更严格的 prompt 提示）；仍失败 → 报告末尾标 "评分失败"，不阻塞主报告输出 |
| 某维度信源 < 3 | score = 50（中性）+ anchor = "数据不足" + 警告标注；综合得分仍按 50 加权计算 |
| 全部维度都数据不足 | 综合得分按 50 给出 + 整体警告 "信源严重不足"  |
| LLM 给出超出 rubric 区间的分数（如 D1 给 90 但解释只是稳扩张档） | 用 rubric 区间夹紧到档位上沿（如夹到 84） |
| 同维度多个事实矛盾（利好 + 利空同时） | LLM 必须在 reasoning 里解释如何取舍，不强制截断 |

---

## 5. Frontend 改造

### 5.1 业务定位重塑（`frontend/src/store/industry.ts`）

4 卡片重新设计，**ID 也要换**（不是只改 name），并处理旧 localStorage 兼容：

| 旧 ID | 新 ID | 旧 name | 新 name | 描述 | 推荐问题示例 |
|---|---|---|---|---|---|
| `smart_transportation` | `securities` | 智慧交通 | 证券 | 头部 / 大型证券公司广告主 | "中信证券 基本面研究" |
| `finance` | `bank` | 金融科技 | 银行 | 银行类广告主（含信用卡 / 数字银行） | "招商银行 信用卡业务基本面" |
| `healthcare` | `insurance` | 医疗健康 | 保险 | 保险类广告主 | "平安保险 业务扩张研究" |
| `energy` | `fund` | 能源电力 | 基金 | 基金 / 资管类广告主 | "易方达 基金公司基本面" |

每个新类目的 `researchKeywords`、`newsKeywords`、`biddingKeywords` 同步换成对应词表。

#### localStorage 迁移

`getStoredIndustryId()` 加迁移层：

```typescript
const ID_MIGRATION: Record<string, string> = {
  smart_transportation: 'securities',
  finance: 'bank',
  healthcare: 'insurance',
  energy: 'fund',
};

const getStoredIndustryId = (): string => {
  const raw = localStorage.getItem('selected_industry_id');
  if (!raw) return 'securities';  // 默认改为新 ID
  if (raw in ID_MIGRATION) {
    const migrated = ID_MIGRATION[raw];
    localStorage.setItem('selected_industry_id', migrated);
    return migrated;
  }
  // 已是新 ID 或未知 ID → 直接返回，未知 ID 由 fallback 处理
  return INDUSTRY_CONFIGS.find(i => i.id === raw) ? raw : 'securities';
};
```

默认行业从 `smart_transportation` → `securities`。

### 5.2 chat-trace 页面 LangSmith 风格重建

参考 `docs/exec-plans/active/ui-mockups.html` 的 U2 tab。改造范围：

- `frontend/src/pages/chat/index.tsx` 主体重排：左侧 trace 视图（暗色 inset card），右侧输出面板（特征向量 tab 改为「基本面评分」tab）
- `frontend/src/pages/chat/component/research-detail.tsx` 内部 trace 树渲染（可折叠 span，每行显示状态点 / agent / 工具 / 计时 / token）
- 顶部 + sidebar 保留 antd 默认（U2 折中策略）
- 暗色 LangSmith trace card 与浅色 antd shell 视觉清晰分隔

### 5.3 不动的部分

- `frontend/src/pages/{auth,bidding,database,index,knowledge,memory,news,404}/` 全部不动
- antd ConfigProvider 主题 / 全局 CSS / 字体不动
- ECharts / valtio store / api 层不动

---

## 6. 数据流

### 6.1 单广告主单次研究

```
用户在前端选广告主类目 + 输入 query（或点推荐问题）
  → POST /research/stream { query: "中信证券 基本面研究", search_modes: ["web"] }
  → DeepResearchV2Service.research(query)（现有调用，不改签名）
  → ChiefArchitect plan 节点：从 query 提取 advertiser_name 写入 state
  → LangGraph: plan → research → analyze → write → review →（必要时 revise→review）→ END
  → 【post-graph hook】scoring_service.score_after_research(final_state)
       ├─ _llm_score(state, rubric)              ← 唯一新增 LLM 调用
       ├─ _clamp_to_anchor_range(json, rubric)   ← Python 区间夹紧
       ├─ _compute_consistency_metrics(state)    ← Python 派生指标
       ├─ _compute_overall(json, rubric)         ← Python 加权
       └─ _render_scoring_markdown(...)          ← 拼接 markdown
  → final_report += scoring_markdown
  → SSE event "research_complete" 携带含评分的完整 final_report
```

**关键点**：
- 评分在 service 层 post-graph 调用，**不嵌入 LeadWriter**，避免 revise 循环重复评分
- LangGraph 状态机 / 6 Agent / graph.py **零修改**
- 仅新增：`scoring_service.py` + `scoring_rubric.yaml` + ChiefArchitect 提取 advertiser_name 的 prompt 微调

### 6.2 渲染流

```
前端收到 final_report SSE 事件
  → 现有 markdown 渲染逻辑展示（含末尾评分表）
  → 右侧 ResearchDetail 面板「基本面评分」tab 也展示同份评分（结构化卡片形式）
```

---

## 7. 风险

| Risk | 缓解 |
|---|---|
| **R1**: LLM 长链路连接异常（实测 24min Connection error） | SCORING_PROMPT 是单次独立 LLM 调用，跑挂了不影响主报告；失败时报告末尾标 "评分失败" 而非整个 pipeline 失败 |
| **R2**: LLM 输出 JSON 破格 | 用 `json.loads` + 校验关键字段；失败重试一次；仍失败兜底降级 |
| **R3**: LLM 不严格遵循 rubric（给出超档位分数） | Python 端区间夹紧 + 在 reasoning 里强制要求"为什么不是相邻档位" |
| **R4**: 信源不足导致评分不可靠 | min_evidence_count = 3 硬阈值，自动降级为中性 + 透明标注 |
| **R5**: rubric 设计需要业务专家校准 | yaml 配置可调，先用通用版上线，逐步校准 |
| **R6**: 不同广告主类目（证券/银行/保险/基金）的 D2 监管口径不同 | v1 rubric 用泛金融 baseline（D2 signal_sources 同时含证监会+银保监会+交易所+自律协会）。跨类目 specialized rubric 列入 future work |
| **R7**: 评分 LLM 调用增加端到端耗时（~30-60s） | 单次额外 LLM 调用，在主报告完成后异步追加；不阻塞前端先看到主报告（SSE 分批推送） |
| **R8**: ChiefArchitect 提取 advertiser_name 失败 | Fallback 到 query[:30]，并在 reasoning 中标注 |

---

## 8. Out of Scope

- 行业级研究 pipeline
- pydantic SignalFeatureVector schema / Feature Store / Batch Scheduler
- 离线评估 demo（sklearn AUC 等）
- 接下游扰动模型 / 业务系统
- Mode A / Mode B 双输出引擎
- antd 替换 / 其他页面 UI 重写
- LangGraph 状态机 / 6 Agent 实现重写
- 监管文件解读 / 合规审计
- advertiser_type-specific rubric 微调（默认证券通用）
- BatchScheduler / 多广告主批处理

---

## 9. 验收标准

| Goal | 验收 |
|---|---|
| G1 业务定位 | 浏览器打开首页，4 卡片显示证券 / 银行 / 保险 / 基金；点击进入 chat 默认 query 含广告主名字 |
| G2 rubric yaml | `python -c "import yaml; yaml.safe_load(open('scoring_rubric.yaml'))"` 解析通过；5 维度 + 完整 5 档锚点 |
| G3 SCORING_PROMPT | 给定 mock facts，调 LLM 返回 JSON，能正常 parse + 5 个 dim 都有 score/anchor/evidence/reasoning |
| G4 Markdown 渲染 | 报告末尾出现 §5 一致的「基本面判断」段落，含综合得分表 + 评分依据明细 + 一致性检查 |
| G5 数据不足 | 构造 mock 场景：D5 维度只有 1 个信源 → 输出标 "数据不足"，分数 50 |
| G6 Frontend U2 | chat-trace 页面视觉与 ui-mockups U2 一致；其他 8 页面对比改造前无视觉差异 |
| G7 interview-prep 更新 | §A pitch / §B 架构图 / §C Q&A / §F 指标 / §G demo flow 均反映新定位（rubric-based 评分系统） |

---

## 10. Open Questions（待用户确认）

| # | 问题 | 当前默认 |
|---|------|---------|
| Q1 | 4 个广告主类目的具体名称 | 证券 / 银行 / 保险 / 基金 |
| Q2 | 默认权重 25/25/20/15/15 是否合理 | 是（D1 D2 占 50% 反映业务+监管对扰动影响最直接） |
| Q3 | rubric 触发条件锚点是否符合业务理解 | 见 §4.2，可逐档调整 |
| Q4 | min_evidence_count 设置 3 是否合理 | 是（与一般 fact-check 标准对齐） |
| Q5 | 分数范围 0-100 vs -100~+100 | 0-100（与信用评级范式对齐，方向通过 anchor 表达） |
| Q6 | demo 用的具体广告主例子 | 中信证券 |
| Q7 | 综合档位映射阈值（75/60/45/30） | 默认值，可调 |

---

## 11. 实施依赖与排序

不按时间，按依赖顺序：

```
A. scoring_rubric.yaml 设计 + 5 维度 + 锚点确定          [独立]
B. SCORING_PROMPT 设计                                    [依赖 A]
C. scoring_service.score_after_research() 调 SCORING_PROMPT  [依赖 B]
D. Python 加权计算 + markdown 渲染                       [依赖 C]
E. 异常处理（JSON 破格 / 数据不足 / 区间夹紧）            [依赖 D]
F. frontend/store/industry.ts 4 类目重命名               [独立，可与 A-E 并行]
G. frontend/pages/chat/ U2 重建                          [独立，可与 A-F 并行]
H. interview-prep.md 更新                                [依赖全部完成]
```

复杂度层级：
- 🟢 低：A / F / H
- 🟡 中：B / C / D / E
- 🔴 高：G（前端组件重排，受现有 30+ SSE 事件解析耦合影响）

---

## 12. 面试 Talk Track 集成

完成实施后更新 `docs/exec-plans/active/interview-prep.md`：

### 新 60 秒 pitch

> 我做了一个面向**单家证券广告主**的多智能体 Deep Research 系统。给定一个广告主主体（如中信证券），LangGraph 编排 6 个 Agent 协作 — 架构师拆问题、侦察兵多源抓取（Bocha web + Milvus + ES + 本地 KB）、分析师生成图表、写手出报告、审查官 fact-check、必要时回退修订。**核心创新在评分层** — 报告末尾用 rubric-based 5 维度量化评分（业务扩张度 25% / 监管态度 25% / 品牌活跃度 20% / 竞争地位 15% / 创新与数字化 15%），LLM 按预定义 rubric 锚点打分，每分都有信源依据 + 档位 reasoning。这套报告由我们的扰动模型团队 / 编辑团队消费，怎么使用是他们的决定 — 我的项目边界就到生产研究为止。

### 新 demo 流程

1. 打开 http://localhost:5183/
2. 点「证券」卡片 → 进入 chat（默认开启深度搜索）
3. 输入「中信证券 基本面研究」
4. 现场展示：左侧 LangSmith 风格的 trace 树流式跑（plan → research → analyze → write → review）
5. 右侧依次切换：研究步骤详情 / 知识图谱 / ECharts 图表 / 流式报告
6. **重点停留在报告末尾**：综合得分表 + 5 维度评分依据明细 + 引用一致性检查
7. 杀手句："这套评分是 rubric-based，跨广告主可比。我们的扰动模型团队会消费这份评分，但**这个项目只到生产为止 — 怎么消费这份判断不在我的边界**。"

### 高频追问对答（替换原 §C）

| 问 | 答 |
|---|---|
| 为什么不让 LLM 直接打综合分 | 黑盒不可解释，业务方拿到分不知凭据；rubric 把"打分逻辑"锁在配置里，跨广告主一致 |
| 为什么是 rubric 而不是 ML 学权重 | 没有 ground truth label（"中信证券真实基本面 = 0.7"无法验证），rubric 是人工专家锚定的，至少可解释、可对齐业务 |
| 为什么权重是 25/25/20/15/15 | yaml 可调，默认值反映业务直觉 — D1 业务 + D2 监管对当期扰动最直接，D5 数字化是中长期信号 |
| 信源不足怎么办 | 硬阈值 3，不足则中性 50 + 显式标注 "数据不足"；不让 LLM 在弱信号下硬猜 |
| LLM 不遵守 rubric 给超分怎么办 | Python 端区间夹紧 + reasoning 强制要求"为什么不是相邻档位"，给 LLM 自我约束的提示 |
| 跑一次多久 | 实测 ~24 分钟，瓶颈在 Writer LLM 调用（每节 50-60s），SCORING 是单次额外调用，多 30-60s |
| 与 v1（之前你做过的早期原型）对比有什么进步 | 不在场景里的版本不必展开 — 重心讲当前版本 |

---

## 附录 A：关键文件索引

| 文件 | 性质 | 内容 |
|---|---|---|
| `backend/app/service/deep_research_v2/scoring_rubric.yaml` | 新建 | rubric 配置（5 维度 + 权重 + 锚点） |
| `backend/app/service/deep_research_v2/scoring_service.py` | 新建 | post-graph 评分流水线（LLM 调用 + 区间夹紧 + 一致性派生 + 渲染） |
| `backend/app/service/deep_research_v2/state.py` | 改 | 加 `advertiser_name: Optional[str]` 字段 |
| `backend/app/service/deep_research_v2/agents/architect.py` | 改 | plan prompt 加 advertiser_name 提取 |
| `backend/app/service/deep_research_v2/service.py` | 改 | research() 在 graph 跑完后调 score_after_research |
| `frontend/src/store/industry.ts` | 改 | 4 类目重命名（含 ID 迁移） + 关键词 |
| `frontend/src/pages/chat/index.tsx` | 改 | LangSmith 风格 trace 视图 |
| `frontend/src/pages/chat/component/research-detail.tsx` | 改 | 右侧面板「基本面评分」tab |
| `docs/exec-plans/active/interview-prep.md`（已存在） | 改 | 同步新定位 + 新 talk track |
