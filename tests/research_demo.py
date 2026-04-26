"""
Deep Research V2 端到端真实测试 — 用于面试 demo 收集指标。

跑法：
    backend/.venv/Scripts/python.exe tests/research_demo.py

输出：
    tests/research_demo_output.json   # 完整指标 + 报告
    控制台打印阶段计时和事件计数
"""
import json
import time
import sys
from collections import Counter
from pathlib import Path

import httpx

QUERY = "2026 年中国金融科技监管走向和重点机会"
ENDPOINT = "http://localhost:8000/research/stream"
PAYLOAD = {
    "query": QUERY,
    "version": "v2",
    "search_modes": ["web"],
    "max_iterations": 3,
}
TIMEOUT = httpx.Timeout(600.0, connect=10.0)
OUT_FILE = Path(__file__).parent / "research_demo_output.json"


def main() -> int:
    print(f"[demo] query: {QUERY}")
    print(f"[demo] POST {ENDPOINT}")
    t_start = time.time()

    event_counts: Counter[str] = Counter()
    phase_timings: dict[str, float] = {}
    last_phase: str | None = None
    last_phase_t: float = t_start
    final_report = ""
    references: list[dict] = []
    outline: list = []
    charts_count = 0
    kg_nodes = 0
    kg_edges = 0
    sample_events: list[dict] = []
    error_msg: str | None = None

    try:
        with httpx.stream("POST", ENDPOINT, json=PAYLOAD, timeout=TIMEOUT) as resp:
            resp.raise_for_status()
            for raw in resp.iter_lines():
                if not raw or not raw.startswith("data:"):
                    continue
                payload = raw[5:].strip()
                if not payload or payload == "[DONE]":
                    continue
                try:
                    evt = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                etype = evt.get("type", "unknown")
                event_counts[etype] += 1

                if len(sample_events) < 3 and etype not in {"thought", "delta", "section_content"}:
                    sample_events.append({"type": etype, "preview": str(evt)[:300]})

                if etype == "phase":
                    phase = evt.get("phase")
                    now = time.time()
                    if last_phase is not None:
                        phase_timings[last_phase] = phase_timings.get(last_phase, 0.0) + (now - last_phase_t)
                    last_phase = phase
                    last_phase_t = now
                    print(f"[demo] phase: {phase} (+{now - t_start:.1f}s)")

                if etype == "outline":
                    content = evt.get("content", evt)
                    outline = content.get("outline", []) if isinstance(content, dict) else []

                if etype == "search_results":
                    results = evt.get("results") or evt.get("content", {}).get("results", [])
                    if results:
                        print(f"[demo] search_results: +{len(results)} sources")

                if etype == "charts":
                    charts = evt.get("charts") or evt.get("content", {}).get("charts", [])
                    charts_count += len(charts)

                if etype == "knowledge_graph":
                    content = evt.get("content", evt)
                    graph = content.get("graph") if isinstance(content, dict) else None
                    if graph:
                        kg_nodes = len(graph.get("nodes", []))
                        kg_edges = len(graph.get("edges", []))

                if etype == "research_complete":
                    final_report = evt.get("final_report", "")
                    references = evt.get("references", []) or []
                    if last_phase is not None:
                        phase_timings[last_phase] = phase_timings.get(last_phase, 0.0) + (time.time() - last_phase_t)
                        last_phase = None

    except httpx.HTTPError as e:
        error_msg = f"{type(e).__name__}: {e}"
        print(f"[demo] ERROR: {error_msg}", file=sys.stderr)

    elapsed = time.time() - t_start

    summary = {
        "query": QUERY,
        "elapsed_seconds": round(elapsed, 2),
        "total_events": sum(event_counts.values()),
        "event_type_counts": dict(event_counts.most_common()),
        "phase_timings_seconds": {k: round(v, 2) for k, v in phase_timings.items()},
        "outline_section_count": len(outline),
        "outline_titles": [s.get("title") for s in outline][:8],
        "charts_count": charts_count,
        "knowledge_graph": {"nodes": kg_nodes, "edges": kg_edges},
        "references_count": len(references),
        "report_length_chars": len(final_report),
        "report_preview": final_report[:800],
        "sample_events": sample_events,
        "error": error_msg,
    }

    OUT_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"[demo] done in {elapsed:.1f}s · events={summary['total_events']} · refs={summary['references_count']} · report_chars={summary['report_length_chars']}")
    print(f"[demo] output saved to {OUT_FILE}")

    return 0 if error_msg is None else 1


if __name__ == "__main__":
    sys.exit(main())
