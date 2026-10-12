#!/usr/bin/env python3
"""Produce descriptive and record statistics from a frozen campaign."""

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def describe(values: list[float]) -> dict:
    return {
        "count": len(values),
        "minimum": min(values),
        "p10": percentile(values, 0.10),
        "p50": percentile(values, 0.50),
        "mean": statistics.fmean(values),
        "p90": percentile(values, 0.90),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "maximum": max(values),
        "standard_deviation": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.runs.read_text(encoding="utf-8").splitlines() if line]
    grouped: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[int(row["bits"])].append(row)

    analysis = {"schema_version": 1, "source": str(args.runs), "by_bits": {}}
    for bits, group in sorted(grouped.items()):
        completed = [row for row in group if row["status"] == "completed" and row["luck_factor"] is not None]
        censored = [row for row in group if row["status"] == "censored"]
        luck = [row["luck_factor"] for row in completed]
        operations = [row["observed_operations"] for row in completed]
        constants = [row["c"] for row in completed]
        records = []
        best = -math.inf
        worst = math.inf
        for row in completed:
            current = row["luck_factor"]
            changed = False
            record = {"run_index": row["run_index"], "run_id": row["run_id"]}
            if current > best:
                best = current
                record["best_luck_so_far"] = best
                changed = True
            if current < worst:
                worst = current
                record["worst_luck_so_far"] = worst
                changed = True
            if changed:
                records.append(record)

        tails = []
        total = len(completed)
        for row in completed:
            at_least = sum(other["luck_factor"] >= row["luck_factor"] for other in completed)
            tails.append({
                "run_id": row["run_id"],
                "luck_factor": row["luck_factor"],
                "runs_completed": total,
                "runs_at_least_this_lucky": at_least,
                "in_sample_tail_probability": at_least / total,
                "empirical_percentile": 100.0 * (1.0 - at_least / total),
            })

        analysis["by_bits"][str(bits)] = {
            "total_runs": len(group),
            "completed_runs": len(completed),
            "censored_runs": len(censored),
            "failed_runs": sum(row["status"] == "failed" for row in group),
            "observed_operations": describe(operations) if operations else None,
            "c": describe(constants) if constants else None,
            "luck_factor": describe(luck) if luck else None,
            "record_history": records,
            "in_sample_tails": tails,
            "holdout_tail": None,
            "holdout_note": "Requires a separately frozen independent campaign.",
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
