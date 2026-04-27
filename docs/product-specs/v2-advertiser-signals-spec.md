# v2 Design Spec — 广告主基本面信号特征工程

> 创建：2026-04-27
> 状态：Draft（待 spec review + user review）
> 项目：industry-information-assistant · v2 升级
> 上游讨论：本会话 brainstorming 全过程，用户最终确认主线 + UI 范围

---

## 1. 背景与问题陈述

### 1.1 v1 的位置

去年用 Dify 搭过一个 Deep Research v1，作为「信贷风险信息识别」场景的探索性 PoC。验证了 multi-agent 思路在「非结构化信息整合」上的潜力，但暴露了三个核心局限：

| 局限 | 表现 |
|---|---|
| Chain 抽象不支持条件循环 | review→revise 这样的对抗式修订循环用 Dify 链式抽象做不出来 |
| 输出形态单一 | 只能产出文字报告，下游系统消费不了 |
| 工程化不够 | 无 schema 校验、无 audit、无可观测 |

v1 没有继续深入。回到本职 — **证券广告投放的扰动模型工程** — 我意识到那里有一个 v1 工具更好对接的场景，且能解决真实业务痛点。

### 1.2 当前业务系统状况

广告投放线上公式：

```
ECPM = ctr × cvr × cpa × 扰动系数
```

**扰动系数离线学习架构**：
- 离线模型从用户特征 / 广告主特征 / 上下文特征学习扰动系数
- 优化目标：在「意愿中等」用户上提升开户转化（意愿高的用户不扰动，意愿低的打压）
- **ctr / cvr 不受影响**，扰动只作用在系数层
- 现有特征以 **embedding + 浅 NLP 为主**，LLM 特征覆盖率低

### 1.3 现有扰动模型的三个固有缺口

| 缺口 | 原因 | 业务后果 |
|---|---|---|
| 冷启动失效 | 新广告主无历史交互 → embedding 没学到 → 扰动 ≈ 1.0 | 新广告主曝光被老广告主吃光 |
| 事件不敏感 | embedding 反应慢，要重训才 reflect 新事件 | 中信证券今天拿牌照，模型要等下次重训才"知道" |
| 不可解释 | embedding 是 dense vector，"为什么扰动 1.2" 答不出 | 工程 debug 难、运营/法务无法理解 |

### 1.4 v2 的角色

> v2 是面向**embedding-主导扰动模型**配套的「**广告主基本面特征生成层**」。用 multi-agent Deep Research 把公网 + 私域信息转成 15 维结构化 SignalFeatureVector，写入 feature store，作为离线扰动模型的特征源之一。

**v2 直接补这三个缺口**：

| 缺口 | v2 的解 |
|---|---|
| 冷启动 | LLM 直接读公网 + 基本面，新广告主 day 1 就有特征 |
| 事件敏感 | 周更 + 事件触发，LLM 立刻 reflect 新事件 |
| 不可解释 | 15 维 named features，每维可解释、可监控、可消融 |

---

## 2. Goals & Non-Goals

### 2.1 Goals

| # | Goal | 怎么验收 |
|---|------|---------|
| G1 | 同一个 multi-agent engine 支持 dual-output：Mode A（人看的报告）+ Mode B（模型用的特征向量） | 单 query 能切换 mode 跑通两种产出 |
| G2 | 15 个特征字段 schema（5 LLM-derived + 1 NLP + 7 确定性 + 2 标签） | pydantic 模型定义；输出能 round-trip 序列化 |
| G3 | SignalCritic：feature schema 校验（强信号 ≥3 源、矛盾互斥、置信度上界） | 不合规特征被拒回 |
| G4 | Feature Store mock：Redis Hash 存最新 + PostgreSQL 存历史 | 可写入 / 读取 / 拉取广告主时间序列 |
| G5 | BatchScheduler mock：1000+ 广告主轮转调度 | 演示队列 / 优先级 / 失败重试 |
| G6 | 离线评估 demo：合成数据 + sklearn AUC 对比 baseline vs +v2 features | 一份对比图，方法论清晰 |
| G7 | Frontend U2：chat-trace 页面 LangSmith 风重建（其他页保持 antd 现状） | 对应 `ui-mockups.html` U2 视觉 |
| G8 | 完整 audit trail：每个特征值能回溯到具体研究 session + 信源 | feature 含 `research_session_id` 字段，前端可点查 |

### 2.2 Non-Goals（明确不做）

| 不做 | 原因 |
|---|---|
| Tier 1 实时信号（新闻 webhook / 流式 sentiment） | 超出范围，且需要 Kafka 等基础设施 |
| 在线扰动模型 / 在线推理服务 | 项目重心在离线特征工程，不动线上 |
| 政策解读 / 合规审计 / 监管文件深度研究 | brainstorming 过程已论证：deep research 不适合「精准 + 同行交流」类任务 |
| 知识图谱前端可视化作为核心展示 | feature 向量不需要图可视化，KG 仅作为内部 evidence |
| 替换 antd UI 框架 | UI 范围仅 chat-trace 页，其他页保留 antd 不动 |
| 重写 LangGraph 状态机 | 现有 plan→research→analyze→write→review→revise 适用，仅扩展 |
| 上线 / 真实流量 A/B | 项目演示性质，不接真实业务系统 |

---

## 3. 架构总览

### 3.1 分层位置

```
┌────────────────────────────────────────────────────────────┐
│ 离线扰动模型 (existing)                                      │
│  features: [embeddings, shallow_NLP, ► SignalFeatureVector] │
│                                              ▲              │
│                                              │ feature 注入  │
│  ─────────────────────────────────────────── ┼──────────── │
│                                              │              │
│  v2 Pipeline (new):                          │              │
│                                              │              │
│  [BatchScheduler] ─→ [DeepResearchEngine] ─→ │             │
│       │                  (LangGraph)         │              │
│       │                  Mode A / Mode B     │              │
│       │                       │              │              │
│       │                       ▼              │              │
│       │              [FeatureExtractor]      │              │
│       │                       │              │              │
│       │                       ▼              │              │
│       └──────────────► [FeatureStore]  ──────┘              │
│                          (Redis + PG)                        │
└────────────────────────────────────────────────────────────┘
```

### 3.2 模块清单

| 模块 | 性质 | 路径 |
|---|---|---|
| `state.py` 字段扩展 | 改 | `backend/app/service/deep_research_v2/state.py` |
| `writer.py` dual-mode | 改 | `backend/app/service/deep_research_v2/agents/writer.py` |
| `critic.py` SignalCritic | 改 | `backend/app/service/deep_research_v2/agents/critic.py` |
| `feature_extractor.py` | 新 | `backend/app/service/deep_research_v2/feature_extractor.py` |
| `feature_pipeline/` | 新目录 | `backend/app/service/feature_pipeline/` |
| `└─ feature_store.py` | 新 | feature 写入 / 查询 |
| `└─ batch_scheduler.py` | 新 | 广告主轮转调度 |
| `└─ schemas.py` | 新 | pydantic feature schema |
| `research_router.py` 扩展 | 改 | `backend/app/router/research_router.py` |
| `backend/app/service/feature_pipeline/eval.py` | 新 | 离线 AUC 对比业务逻辑 |
| `backend/test/feature_pipeline/test_eval.py` | 新 | 评估入口脚本 + 验证 |
| `frontend/src/pages/chat/` 重建 | 改 | LangSmith 风格 trace 视图 |
| `frontend/src/store/industry.ts` | 改 | 4 行业卡片改证券广告主类目 |

---

## 4. 详细组件设计

### 4.1 ResearchState 扩展

新增两个字段：

```python
class ResearchState(TypedDict):
    # ... 现有 22 个字段保留 ...
    output_mode: Literal["report", "features", "both"]  # 新增
    feature_vector: Dict[str, Any]                      # 新增（15 字段填入）
```

`create_initial_state()` 签名扩展 + 字段必须显式初始化，避免 KeyError：

```python
def create_initial_state(
    query: str,
    session_id: str,
    search_web: bool = True,
    search_local: bool = False,
    output_mode: Literal["report", "features", "both"] = "both"  # 新增
) -> ResearchState:
    return ResearchState(
        # ... 现有 22 个字段保留 ...
        output_mode=output_mode,    # 新增初始化
        feature_vector={},          # 新增初始化（空 dict，不是 None）
    )
```

### 4.2 Writer Dual-Mode

`LeadWriter.process()` 内部根据 `state["output_mode"]` 分支。**LangGraph 节点和边不变**，分支在 Writer 内部：

| Mode | Writer 行为 | 后续 Critic |
|---|---|---|
| `"report"` | 现有逻辑不变：SECTION_WRITING_PROMPT × N 节 → SYNTHESIS_PROMPT 合成 → 写 `final_report` | 走原 REVIEW_PROMPT（校验报告） |
| `"features"` | 跳过 SYNTHESIS_PROMPT 与 final_report 写入；改跑 FEATURE_EXTRACTION_PROMPT，写 `state["feature_vector"]` 的 5 个 LLM 维度（business_health / regulatory_pressure / competitive_position / innovation_signal / boost_recommendation）；`final_report` 留空字符串 | 走 SignalCritic 分支（见 §4.3） |
| `"both"` | 先按 "report" 跑完，再追加跑 FEATURE_EXTRACTION_PROMPT 写 feature_vector | Critic 同时校验 report 与 features，二者 issue 累计到 unresolved_issues |

新增 `FEATURE_EXTRACTION_PROMPT`：

```python
FEATURE_EXTRACTION_PROMPT = """
你是广告主基本面分析师。基于已收集的事实和数据，对该广告主输出 5 个 LLM-derived 信号维度。

广告主：{advertiser_name}
事实库：{facts}
数据点：{data_points}

按以下 schema 输出（每维 [-1, 1] 或 [0, 1]，含置信度）：

{
  "business_health": {"value": -1.0~1.0, "confidence": 0~1, "reasoning": "..."},
  "regulatory_pressure": {"value": -1.0~1.0, "confidence": 0~1, "reasoning": "..."},
  "competitive_position": {"value": -1.0~1.0, "confidence": 0~1, "reasoning": "..."},
  "innovation_signal": {"value": 0~1.0, "confidence": 0~1, "reasoning": "..."},
  "boost_recommendation": {"value": -1.0~1.0, "confidence": 0~1, "reasoning": "..."}
}

要求：
- 每个 value 必须有事实库中至少 2 个独立信源支持
- value 与 reasoning 必须一致
- 不能引入事实库外的信息
"""
```

### 4.3 SignalCritic（CriticMaster 扩展）

`CriticMaster.process()` 根据 `state["output_mode"]` 分两类校验：

#### A. 报告校验（mode in ["report", "both"]）
现有 REVIEW_PROMPT 路径不动，输出 critic_feedback 列表。

#### B. 特征校验（mode in ["features", "both"]）
**两段实现，不混入同一 LLM 调用**：

**B1. 确定性 Python 检查（直接代码，不走 LLM）**:

```python
def _validate_features_deterministic(state, feature_vector) -> List[CriticFeedback]:
    issues = []
    facts_by_topic = group_facts_by_topic(state["facts"])
    
    # Rule 1: 强信号 (abs(value) > 0.7) 必须 ≥3 个独立源
    for dim_name in LLM_DERIVED_DIMS:
        v = feature_vector.get(dim_name, {}).get("value", 0)
        if abs(v) > 0.7:
            related_facts = find_facts_for_dim(state, dim_name)
            sources = {f["source_url"] for f in related_facts}
            if len(sources) < 3:
                issues.append(CriticFeedback(
                    issue_type="insufficient_sources",
                    severity="major",
                    target_section=dim_name,
                    description=f"{dim_name}={v} 是强信号但仅 {len(sources)} 源支撑"
                ))
    
    # Rule 3: confidence ≤ source_count / 5
    for dim_name in LLM_DERIVED_DIMS:
        c = feature_vector.get(dim_name, {}).get("confidence", 0)
        sc = count_sources_for_dim(state, dim_name)
        if c > sc / 5:
            issues.append(CriticFeedback(
                issue_type="confidence_overstated",
                severity="major",
                description=f"{dim_name} confidence={c} 超过 source_count/5={sc/5}"
            ))
    
    # Rule 5: event_types 与 risk_flags 互斥
    et = set(feature_vector.get("event_types", []))
    rf = set(feature_vector.get("risk_flags", []))
    if et & rf:
        issues.append(CriticFeedback(
            issue_type="signal_inconsistency",
            severity="critical",
            description=f"event_types 与 risk_flags 重叠: {et & rf}"
        ))
    
    return issues
```

**B2. LLM 主观一致性检查（FEATURE_REVIEW_PROMPT，独立 LLM 调用）**:

只校验 Rule 2 + Rule 4（需要语义判断的部分）：

```python
FEATURE_REVIEW_PROMPT = """
检查 feature_vector 的语义一致性：

Rule 2: 矛盾信号互斥（如 regulatory_pressure < -0.5 但 business_health > 0.5 → 矛盾）
Rule 4: boost_recommendation 与 (business_health + competitive_position + innovation_signal) 三维方向应当一致

输入 feature_vector：{feature_vector_json}

输出 issues JSON list，每个 issue 含：
{ "rule": "rule_2" or "rule_4", "severity": "...", "description": "..." }
"""
```

#### C. issue type 扩展
- 现有：`missing_source / logic_error / bias / hallucination / outdated / incomplete`
- 新增：`signal_inconsistency / insufficient_sources / confidence_overstated`

#### D. unresolved_issues 累计
B1 + B2 产生的 issue（severity in {critical, major}）累加到 `state["unresolved_issues"]`。`_should_revise` 现有逻辑（`unresolved_issues > 0 && iteration < max_iterations`）继续触发 revise → review 循环。

#### E. 防误拒兜底
当 `iteration >= 3`，所有 issue 降级为 warning（不阻塞 complete），写入 critic_feedback 但不计入 unresolved_issues。

### 4.4 FeatureExtractor（核心新模块）

**关键设计原则**：15 个特征字段中
- **5 个 LLM 主观打分**（Writer Mode B 写入 state["feature_vector"]）
- **7 个确定性函数派生**（FeatureExtractor 直接计算）
- **1 个 NLP/sentiment**（先用 LLM fallback，后续可换独立 classifier）
- **2 个 LLM 标签提取**（半 LLM，从 key_entities + critic_feedback 抽取）

避免 LLM 数值幻觉，将主观与客观维度分离。

```python
# backend/app/service/deep_research_v2/feature_extractor.py

class FeatureExtractor:
    """从 ResearchState 派生 SignalFeatureVector"""
    
    def extract(self, state: ResearchState, advertiser_id: str) -> SignalFeatureVector:
        # LLM-derived（5 维）从 state["feature_vector"] 取（Writer Mode B 写入）
        llm_features = state["feature_vector"]
        
        # 确定性派生（7 维）从 facts/data_points/references 计算
        det_features = {
            "source_diversity": self._source_diversity(state),
            "source_authority": self._source_authority(state),
            "consensus_score": self._consensus_score(state),
            "activity_density_7d": self._activity_density(state, days=7),
            "activity_density_30d": self._activity_density(state, days=30),
            "trend_direction": self._trend_direction(state),
            "boost_confidence": state["quality_score"] * self._source_diversity(state),
        }
        
        # 半 LLM（2 维）：从 key_entities + critic_feedback 提取标签
        tag_features = {
            "event_types": self._extract_event_types(state),
            "risk_flags": self._extract_risk_flags(state),
        }
        
        # media_sentiment 由独立 sentiment classifier 给（可选；先用 LLM fallback）
        nlp_features = {
            "media_sentiment": self._sentiment(state),
        }
        
        return SignalFeatureVector(
            advertiser_id=advertiser_id,
            snapshot_time=datetime.utcnow(),
            research_session_id=state["session_id"],
            **llm_features, **det_features, **tag_features, **nlp_features,
        )
```

**确定性函数公式**（部分示例）：

```python
def _source_diversity(self, state) -> float:
    domains = {extract_domain(f["source_url"]) for f in state["facts"] if f.get("source_url")}
    return min(len(domains) / 10, 1.0)

def _source_authority(self, state) -> float:
    official_count = sum(1 for f in state["facts"] if f.get("source_type") == "official")
    return official_count / max(len(state["facts"]), 1)

def _consensus_score(self, state) -> float:
    # 简化版：相同主题被多源提及的比例
    fact_topics = [_extract_topic(f.get("content", "")) for f in state["facts"]]
    topic_counts = Counter(fact_topics)
    multi_source = sum(c for c in topic_counts.values() if c >= 2)
    return multi_source / max(sum(topic_counts.values()), 1)

def _activity_density(self, state, days) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    return sum(
        1 for f in state["facts"] 
        if _safe_parse_extracted_at(f) >= cutoff
    )

def _trend_direction(self, state) -> float:
    d7 = self._activity_density(state, 7)
    d30 = self._activity_density(state, 30)
    return tanh((d7 - d30/4) / max(d30/4, 1))

def _boost_confidence(self, state) -> float:
    """quality_score (1-10 整数) 归一化到 [0,1] 后乘 source_diversity。
    
    注意：mode="features" 单跑时 quality_score 仍由 SignalCritic（§4.3 B1+B2）
    在 review 阶段填入（取 1-10 整数等价分），不会出现 quality_score=0 的退化。
    若 critic 未运行（Writer mode 异常），fallback 到 0.5。
    """
    raw_qs = state.get("quality_score", 0.0) or 5.0  # fallback 中位数
    normalized_qs = min(max(raw_qs / 10.0, 0.0), 1.0)
    return normalized_qs * self._source_diversity(state)
```

#### Fact 字段 Contract（Scout 输出契约）

`state["facts"]` 中每个 dict 必须包含：

| 字段 | 类型 | 必需 | 默认（缺失时） |
|---|---|---|---|
| `id` | str | ✅ | - |
| `content` | str | ✅ | "" |
| `source_url` | str | ✅ | "" |
| `source_name` | str | ✅ | "unknown" |
| `source_type` | Literal["official","academic","news","report","self_media"] | ✅ | "self_media" |
| `credibility_score` | float [0,1] | ✅ | 0.5 |
| `extracted_at` | str (ISO 8601) | ✅ | datetime.utcnow().isoformat() |

`_safe_parse_extracted_at(f)` 兜底：缺失或解析失败 → 返回 `datetime.utcnow()`（不算入历史窗口）。Scout 实现负责保证此契约；FeatureExtractor 防御性兜底。

### 4.5 Feature Schema (pydantic)

```python
# backend/app/service/feature_pipeline/schemas.py

from pydantic import BaseModel, Field, conlist
from typing import Literal
from datetime import datetime

class SignalFeatureVector(BaseModel):
    """广告主信号特征向量（v2 主产出）"""
    
    # 元信息
    advertiser_id: str
    snapshot_time: datetime
    research_session_id: str
    
    # LLM-derived (5)
    business_health: float = Field(ge=-1.0, le=1.0)
    regulatory_pressure: float = Field(ge=-1.0, le=1.0)
    competitive_position: float = Field(ge=-1.0, le=1.0)
    innovation_signal: float = Field(ge=0.0, le=1.0)
    boost_recommendation: float = Field(ge=-1.0, le=1.0)
    
    # NLP (1)
    media_sentiment: float = Field(ge=-1.0, le=1.0)
    
    # 确定性 (7)
    source_diversity: float = Field(ge=0.0, le=1.0)
    source_authority: float = Field(ge=0.0, le=1.0)
    consensus_score: float = Field(ge=0.0, le=1.0)
    activity_density_7d: int = Field(ge=0)
    activity_density_30d: int = Field(ge=0)
    trend_direction: float = Field(ge=-1.0, le=1.0)
    boost_confidence: float = Field(ge=0.0, le=1.0)
    
    # 标签 (2)
    event_types: conlist(str, max_length=10) = []
    risk_flags: conlist(str, max_length=10) = []
```

### 4.6 Feature Store

```python
# backend/app/service/feature_pipeline/feature_store.py

class FeatureStore:
    """Feature 读写抽象。当前实现：Redis（最新）+ PostgreSQL（历史快照）"""
    
    def write(self, vector: SignalFeatureVector) -> None: ...
    def read_latest(self, advertiser_id: str) -> Optional[SignalFeatureVector]: ...
    def read_history(self, advertiser_id: str, since: datetime) -> List[SignalFeatureVector]: ...
    def list_advertisers(self) -> List[str]: ...
```

PG 表 schema：

```sql
CREATE TABLE advertiser_signal_features (
    id BIGSERIAL PRIMARY KEY,
    advertiser_id VARCHAR(64) NOT NULL,
    snapshot_time TIMESTAMP NOT NULL,
    research_session_id UUID NOT NULL,
    feature_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    INDEX idx_advertiser_time (advertiser_id, snapshot_time DESC)
);
```

### 4.7 Batch Scheduler

```python
# backend/app/service/feature_pipeline/batch_scheduler.py

class BatchScheduler:
    """周更广告主特征 + 失败重试 + 优先级"""
    
    async def run_batch(self, advertisers: List[str], priority_hint: Dict[str, int] = None):
        """
        优先级规则：
        - 高曝光广告主（CTR/曝光量历史高）优先
        - 上次更新 > 7 天的广告主优先  
        - 失败次数 < 3 才重试
        """
    
    async def schedule_advertiser(self, advertiser_id: str) -> str:
        """单广告主入队，返回 task_id"""
```

执行流程：
1. 拉广告主列表（mock）
2. 按优先级排队
3. 每个广告主调 `DeepResearchV2Service.research(query=f"广告主基本面: {name}", output_mode="features")`
4. 跑完 → FeatureExtractor → FeatureStore.write
5. 失败重试（指数退避，max 3 次）
6. 完成统计：成功 / 失败 / 平均耗时 / token 消耗

### 4.8 离线评估 Demo

**路径决定**（遵循 `.claude/rules/python-structure.md`：业务代码在 `backend/app/`）：

- 业务逻辑：`backend/app/service/feature_pipeline/eval.py`（核心 sklearn 训练 / 评估代码）
- 入口脚本：`backend/test/feature_pipeline/test_eval.py`（pytest 风格 + 可独立运行）
- 输出图：`backend/test/feature_pipeline/eval_output/`（gitignored）

```python
# backend/app/service/feature_pipeline/eval.py

"""
对比 baseline 扰动模型 vs +v2 features 的 AUC。
合成数据集（不含真实业务数据），方法论清晰即可。
"""

def run_eval():
    # 1. sklearn make_classification 造意愿中等用户样本
    # 2. 注入 15 个 v2 特征（含真实信号 + 噪声）
    # 3. baseline: 只用 embedding-mock 特征训扰动模型
    # 4. enhanced: baseline + v2 特征
    # 5. 对比 AUC / feature importance
    # 6. 输出图：eval_output/auc_comparison.png + feature_importance.png
```

`backend/test/feature_pipeline/test_eval.py` 调 `run_eval()` 并验证输出文件存在。

### 4.9 Frontend U2 改造范围

**改造**：
- `frontend/src/pages/chat/index.tsx` + `frontend/src/pages/chat/component/` → LangSmith 风格 trace 视图（参考 `ui-mockups.html` U2）
  - 步骤条改为可折叠 span 树
  - 每个 span 显示：状态点 / agent / 工具 / 计时 / token
  - 选中 span 显示详情（保持现有 ResearchDetail 组件，外壳重排）
  - 暗色 inset card 嵌在浅色 antd shell 中
- `frontend/src/pages/chat/newchat.tsx` → query header 略调
- `frontend/src/store/industry.ts` → 4 行业改证券广告主类目（智慧交通 → 证券 / 金融科技 → 银行 / 医疗 → 保险 / 能源 → 基金）
- 右侧 Output 面板：现有 ResearchDetail 组件新增「特征向量」tab（与 Sources / KG / Report 并列），antd Table 展示 15 字段特征

**保留不动**：
- `frontend/src/pages/{auth,bidding,database,index,knowledge,memory,news}/` 全部不动
- antd 主题不动
- 全局 CSS / 字体不动
- `frontend/src/pages/feature/`（独立特征详情页）**不在本期 scope**，特征展示只在 chat 页右侧 tab 内

---

## 5. 数据流

### 5.1 单广告主单次研究（Mode B）

#### API 契约

`POST /research/features/{advertiser_id}`

Request body:
```json
{
  "advertiser_name": "中信证券",      // human-readable，给 LLM 用
  "advertiser_type": "securities",   // ["securities","banking","insurance","fund"]
  "force_refresh": false,            // 默认走 Feature Store 缓存（≤7 天直返）
  "mode": "features"                 // ["report","features","both"]，默认 features
}
```

Response 200:
```json
{
  "advertiser_id": "cit",
  "research_session_id": "a4f8...",
  "feature_vector": { /* SignalFeatureVector */ },
  "elapsed_ms": 412300,
  "cached": false
}
```

Response 4xx：
- 400：invalid mode 或 advertiser_type
- 404：advertiser_id 不存在
- 429：BatchScheduler 限流

#### 流程

```
POST /research/features/{advertiser_id}
  → DeepResearchV2Service.extract_features(advertiser_id, mode)
  → DeepResearchV2Service.research(output_mode=mode)
  → LangGraph: plan → research → analyze → write(mode-aware) → review(SignalCritic) → END/revise
  → FeatureExtractor.extract(state, advertiser_id) 
  → SignalFeatureVector pydantic 校验（pydantic 失败 → 400）
  → FeatureStore.write(vector, research_session_id)
  → return JSON
```

### 5.2 批量调度（周更）

```
crontab / scheduler trigger 
  → BatchScheduler.run_batch(advertisers, priority)
  → for each advertiser:
       schedule_advertiser() 
         → 5.1 single-flow
         → on success: FeatureStore.write
         → on failure: retry queue (max 3, exponential backoff)
  → emit batch_complete metrics (count, avg_duration, failures)
```

### 5.3 评估流（离线）

```
load synthetic dataset
  → train baseline 扰动 model on embedding-mock features only
  → train enhanced 扰动 model on embedding-mock + v2 features
  → predict on holdout
  → compute AUC / NDCG / feature importance
  → plot comparison
  → save to backend/test/feature_pipeline/eval_output/
```

---

## 6. 风险与缓解

| Risk | 现状证据 | 缓解 |
|---|---|---|
| **R1: LLM 长链路连接异常** | 实测 24 min Connection error（DashScope 端） | Mode B 单次跑控制在 5-8 min（裁掉 SYNTHESIS）；BatchScheduler 加重试 + 限流 |
| **R2: LLM JSON 输出格式破格** | LLM 偶尔不严格遵循 JSON schema | pydantic 校验 + Writer 失败时 retry + 兜底 default 值 |
| **R3: 特征值漂移 / 不稳定** | 同广告主多次研究，特征值方差大 | 引入 confidence 维度 + 历史均值平滑（feature_extractor 内取 last 3 weeks 均值） |
| **R4: 评估缺真实数据** | 真实业务数据不上仓库 | 完全合成数据集 + 注入式信号；面试讲方法论而非"真实业务效果" |
| **R5: SignalCritic 误拒** | 校验过严导致很多次 revise | iteration ≥ 3 后允许 critic warn-only 而非 reject |

---

## 7. 验收标准

| Goal | 验收 |
|---|---|
| G1 dual-mode | 同一 query，分别用 `output_mode="report"` / `"features"` / `"both"` 跑通 3 次，产物各异且符合 schema |
| G2 schema | `SignalFeatureVector(**dict).model_dump()` round-trip 通过；非法值（如 value > 1.0）被 pydantic 拒绝 |
| G3 SignalCritic | 构造测试用例：仅 1 源的强信号 → 被拒；矛盾信号 → 触发 conflict issue |
| G4 Feature Store | 写入 → 读取 → list_advertisers / read_history 全部 round-trip 通过 |
| G5 BatchScheduler | mock 5 个广告主，run_batch 跑通；故意让 1 个失败，验证 retry 机制 |
| G6 离线评估 | `pytest backend/test/feature_pipeline/test_eval.py` 跑通，eval_output/ 下出 2 张图（auc_comparison.png + feature_importance.png），方法论可读 |
| G7 Frontend U2 | chat-trace 页面视觉与 `ui-mockups.html` U2 tab 一致；其他页对比改造前无视觉差异 |
| G8 Audit trail | 任意 SignalFeatureVector，根据 `research_session_id` 关联到 `ResearchCheckpoint` 表（`backend/app/service/checkpoint_service.py` 既有），可拉回完整研究 state 和事件日志 |

---

## 8. Out of Scope（再次明确）

- ❌ 实时信号流（Tier 1）
- ❌ 在线扰动模型集成
- ❌ 真实业务数据接入
- ❌ 监管文件解读 / 合规审计
- ❌ KG 前端可视化作为核心
- ❌ antd 替换 / 全局 UI 重写
- ❌ U1 / U3 风格切换
- ❌ Airflow / Feast / W&B 等重型依赖

---

## 9. 面试 Talk Track 集成

按 design doc 完成后，更新 `docs/exec-plans/active/interview-prep.md`：

- §A 60-sec pitch → 替换为「v2 是为 embedding-主导扰动模型配套的特征生成层」版本
- §B Mermaid 架构图 → 加一张「v2 在扰动模型 pipeline 中的位置」
- §C 高频追问 → 替换为本 spec 涉及的 7 项 Agent 工程能力（C1-C7 + C8/C9/C10）
- §F Demo 指标 → 跑完 G6 评估 demo 后用真实指标替换
- §G 现场 Demo 流程 → 调整为：跑一个广告主 → trace 视图演示 → 特征面板演示 → 评估对比图

---

## 10. 实施依赖与排序

不按时间，按依赖顺序：

```
A. 业务定位重塑 (frontend/store/industry.ts)         [独立]
B. ResearchState +字段                                 [独立]
C. SignalFeatureVector schema (pydantic)              [独立]
D. FeatureExtractor                                    [依赖 B + C]
E. Writer dual-mode + FEATURE_EXTRACTION_PROMPT       [依赖 B]
F. SignalCritic 扩展                                   [依赖 C + E]
G. Feature Store + DB schema                           [依赖 C]
H. extract_features API + research_router 扩展        [依赖 D + G]
I. BatchScheduler                                      [依赖 H]
J. 离线评估 demo                                       [依赖 G]
K. Frontend U2 chat-trace 重建                         [独立; 与后端并行]
L. interview-prep 更新                                 [依赖全部 done]
```

复杂度层级：
- 🟢 低：A / B / C / G(schema) / L
- 🟡 中：D / E / F / H / J / K
- 🔴 高：I（异步队列 + 失败处理 + 优先级最易踩坑）

---

## 11. 待确认 / Open Questions

| # | 问题 | 当前默认 | 待确认 |
|---|------|---------|--------|
| Q1 | 4 个证券广告主类目具体名称 | 证券 / 银行 / 保险 / 基金 | 用户可调整 |
| Q2 | demo 用的具体广告主例子 | 中信证券 | 是否换成其他 |
| Q3 | media_sentiment 是用独立 NLP 还是 LLM fallback | LLM fallback（简化） | 后续可加 sentiment classifier |
| Q4 | event_types / risk_flags 标签词表 | **预定义封闭词表**（避免 SignalCritic Rule 5 互斥校验失效） | 见下方默认词表，可调整 |
| Q5 | BatchScheduler 是用 asyncio.Queue 还是引入 RQ/Celery | asyncio.Queue（轻量） | 复杂度可接受范围 |

#### Q4 默认词表

```python
EVENT_TYPES = {
    "license_approval",      # 牌照获批
    "partnership",           # 合作签约
    "product_launch",        # 新产品发布
    "expansion",             # 业务扩张
    "innovation_award",      # 创新奖项
    "leadership_change",     # 高管变动（中性）
    "earnings_beat",         # 业绩超预期
}

RISK_FLAGS = {
    "regulatory_warning",    # 监管警告
    "regulatory_fine",       # 监管罚单
    "litigation",            # 诉讼
    "data_breach",           # 数据泄露
    "earnings_miss",         # 业绩不及预期
    "leadership_scandal",    # 高管负面
    "license_revocation",    # 牌照撤销
}
```

封闭词表保证：
- SignalCritic Rule 5（互斥校验）有效：两集合不相交
- LLM 提取时只能选已知标签，避免幻觉
- 下游模型不需处理无限 vocabulary

