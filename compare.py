#!/usr/bin/env python3
"""Compare two scored eval runs and highlight regressions.

Usage:
    python3 eval/compare.py eval/results/baseline_scored.json eval/results/new_scored.json
"""

import argparse
import json
import sys
from pathlib import Path


def load_scored(path: Path) -> dict:
    with open(path) as f:
        data = json.load(f)
    results_by_id = {r["id"]: r for r in data["results"]}
    return {"summary": data["summary"], "results": results_by_id}


def compare(baseline_path: Path, new_path: Path):
    baseline = load_scored(baseline_path)
    new = load_scored(new_path)

    b_summary = baseline["summary"]
    n_summary = new["summary"]

    print(f"Baseline: {baseline_path.name} ({b_summary['total_prompts']} prompts)")
    print(f"New:      {new_path.name} ({n_summary['total_prompts']} prompts)")
    print()

    # Overall
    score_delta = n_summary["average_score"] - b_summary["average_score"]
    rate_delta = n_summary["pass_rate"] - b_summary["pass_rate"]
    direction = "+" if score_delta >= 0 else ""
    print(f"Pass rate: {b_summary['pass_rate']}% -> {n_summary['pass_rate']}% ({direction}{rate_delta:.1f}%)")
    print(f"Avg score: {b_summary['average_score']:.3f} -> {n_summary['average_score']:.3f} ({direction}{score_delta:.3f})")
    print()

    # Per-prompt comparison
    regressions = []
    improvements = []
    new_prompts = []

    all_ids = set(list(baseline["results"].keys()) + list(new["results"].keys()))
    for pid in sorted(all_ids):
        b = baseline["results"].get(pid)
        n = new["results"].get(pid)

        if not b:
            new_prompts.append((pid, n))
            continue
        if not n:
            continue

        b_total = b.get("total", 0)
        n_total = n.get("total", 0)
        delta = n_total - b_total

        if delta < -0.1:
            regressions.append((pid, b_total, n_total, delta, b.get("pass"), n.get("pass")))
        elif delta > 0.1:
            improvements.append((pid, b_total, n_total, delta, b.get("pass"), n.get("pass")))

    if regressions:
        print("REGRESSIONS:")
        for pid, b_score, n_score, delta, b_pass, n_pass in sorted(regressions, key=lambda x: x[3]):
            status = ""
            if b_pass and not n_pass:
                status = " [PASS -> FAIL]"
            print(f"  {pid}: {b_score:.2f} -> {n_score:.2f} ({delta:+.2f}){status}")
        print()

    if improvements:
        print("IMPROVEMENTS:")
        for pid, b_score, n_score, delta, b_pass, n_pass in sorted(improvements, key=lambda x: -x[3]):
            status = ""
            if not b_pass and n_pass:
                status = " [FAIL -> PASS]"
            print(f"  {pid}: {b_score:.2f} -> {n_score:.2f} ({delta:+.2f}){status}")
        print()

    if new_prompts:
        print(f"NEW PROMPTS ({len(new_prompts)}):")
        for pid, n in new_prompts:
            print(f"  {pid}: {n.get('total', 0):.2f} ({'PASS' if n.get('pass') else 'FAIL'})")
        print()

    unchanged = len(all_ids) - len(regressions) - len(improvements) - len(new_prompts)
    print(f"Summary: {len(regressions)} regressions, {len(improvements)} improvements, {unchanged} unchanged")


def main():
    parser = argparse.ArgumentParser(description="Compare two scored eval runs")
    parser.add_argument("baseline", help="Baseline scored results JSON")
    parser.add_argument("new", help="New scored results JSON")
    args = parser.parse_args()

    compare(Path(args.baseline), Path(args.new))


if __name__ == "__main__":
    main()
