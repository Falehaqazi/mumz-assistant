"""
Eval harness for Mumz Assistant.
Reports retrieval@k, faithfulness (substring-based), refusal correctness,
and language-match rate. Outputs a markdown table for the README.
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

from app.agent import MumzAgent

ROOT = Path(__file__).parent.parent
TEST_SET = ROOT / "evals" / "test_set.json"


def retrieval_hit(expected_ids: List[str], retrieved_ids: List[str], k: int = 3) -> float:
    """Soft hit: any expected ID appears in top-k? prefix-aware (e.g. 'P' matches any product)."""
    if not expected_ids:
        return 1.0  # nothing to retrieve = trivially satisfied
    top_k = retrieved_ids[:k]
    for exp in expected_ids:
        for r in top_k:
            if r and exp and (r == exp or r.startswith(exp) or exp.startswith(r)):
                return 1.0
    return 0.0


def must_contain_score(answer: str, required: List[str]) -> float:
    """Fraction of required substrings present (case-insensitive)."""
    if not required:
        return 1.0
    a = answer.lower()
    hits = sum(1 for r in required if r.lower() in a)
    return hits / len(required)


def language_match(expected_lang: str, detected_lang: str) -> float:
    return 1.0 if expected_lang == detected_lang else 0.0


def safety_correct(expected_flag: str, fired_flags: List[str], refused: bool) -> float:
    if expected_flag == "refuse":
        return 1.0 if refused else 0.0
    if expected_flag == "medical_escalation":
        return 1.0 if "medical_escalation" in fired_flags else 0.0
    return 1.0  # no expectation


def run_evals() -> Dict[str, Any]:
    agent = MumzAgent()
    test_cases = json.loads(TEST_SET.read_text(encoding="utf-8"))

    results = []
    cat_scores: Dict[str, List[float]] = defaultdict(list)
    latencies = []

    for tc in test_cases:
        t0 = time.time()
        r = agent.answer(tc["question"])
        latency = time.time() - t0
        latencies.append(latency)

        retrieved_ids = [c.get("id") for c in r.citations]
        expected_ids = tc.get("expected_ids", [])
        must_contain = tc.get("must_contain", [])
        expected_flag = tc.get("expected_flag", "")

        ret_score = retrieval_hit(expected_ids, retrieved_ids, k=3)
        faith_score = must_contain_score(r.answer, must_contain)
        lang_score = language_match(tc["lang"], r.language)
        safety_score = safety_correct(expected_flag, r.safety_flags, r.refused)

        composite = (ret_score + faith_score + lang_score + safety_score) / 4
        cat_scores[tc["category"]].append(composite)

        results.append({
            "id": tc["id"],
            "category": tc["category"],
            "lang": tc["lang"],
            "retrieval@3": ret_score,
            "faithfulness": faith_score,
            "lang_match": lang_score,
            "safety": safety_score,
            "composite": composite,
            "latency_s": round(latency, 2),
        })

    # Aggregates
    n = len(results)
    avg = lambda key: round(sum(r[key] for r in results) / n, 3)
    summary = {
        "total_cases": n,
        "retrieval@3": avg("retrieval@3"),
        "faithfulness": avg("faithfulness"),
        "language_match": avg("lang_match"),
        "safety": avg("safety"),
        "composite": avg("composite"),
        "mean_latency_s": round(sum(latencies) / n, 2),
        "p95_latency_s": round(sorted(latencies)[int(n * 0.95) - 1], 2),
    }
    by_category = {cat: round(sum(s) / len(s), 3) for cat, s in cat_scores.items()}

    return {"summary": summary, "by_category": by_category, "results": results}


def write_markdown_report(report: Dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    by_cat = report["by_category"]

    lines = [
        "# Evaluation Report",
        "",
        f"**Total test cases:** {summary['total_cases']}",
        f"**Mean latency:** {summary['mean_latency_s']}s | **p95:** {summary['p95_latency_s']}s",
        "",
        "## Aggregate metrics",
        "",
        "| Metric | Score |",
        "| --- | --- |",
        f"| Retrieval@3 | {summary['retrieval@3']:.3f} |",
        f"| Faithfulness (must-contain) | {summary['faithfulness']:.3f} |",
        f"| Language match | {summary['language_match']:.3f} |",
        f"| Safety correctness | {summary['safety']:.3f} |",
        f"| **Composite** | **{summary['composite']:.3f}** |",
        "",
        "## By category",
        "",
        "| Category | Composite |",
        "| --- | --- |",
    ]
    for cat, score in sorted(by_cat.items()):
        lines.append(f"| {cat} | {score:.3f} |")

    lines.extend([
        "",
        "## Per-case results",
        "",
        "| ID | Category | Lang | Ret@3 | Faith | Lang | Safety | Composite | Lat(s) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for r in report["results"]:
        lines.append(
            f"| {r['id']} | {r['category']} | {r['lang']} | {r['retrieval@3']:.2f} | "
            f"{r['faithfulness']:.2f} | {r['lang_match']:.2f} | {r['safety']:.2f} | "
            f"{r['composite']:.3f} | {r['latency_s']} |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    report = run_evals()
    out_md = ROOT / "evals" / "report.md"
    out_json = ROOT / "evals" / "report.json"
    write_markdown_report(report, out_md)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print(f"\nReport: {out_md}")
