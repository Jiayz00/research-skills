#!/usr/bin/env python3
"""Summarize tidy experiment runs with no third-party dependencies.

Input is CSV or JSONL with one row per run (or one row per run/step).
The script reports group statistics and baseline differences; it does not
decide whether a result is scientifically meaningful.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


T95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
}


def t_critical(df: int, confidence: float) -> Tuple[float, bool]:
    """Return (critical value, used_normal_approximation)."""
    if abs(confidence - 0.95) > 1e-9:
        # 0.90/0.99 are common; otherwise fall back to the normal approximation.
        z = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}.get(round(confidence, 2))
        return (z if z is not None else 1.960), True
    if df <= 0:
        return T95[1], False
    if df in T95:
        return T95[df], False
    if df < 30:
        covered = [key for key in T95 if key <= df]
        return T95[max(covered)], False
    return 1.960, False


def as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def load_rows(path: Path) -> List[Dict[str, Any]]:
    if path.suffix.lower() in (".jsonl", ".ndjson"):
        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    item = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid JSON on line {line_number}: {exc}") from exc
                if not isinstance(item, dict):
                    raise ValueError(f"line {line_number} is not a JSON object")
                rows.append(item)
        return rows
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        return [dict(row) for row in reader]


def group_key(row: Dict[str, Any], group_column: str, step_column: Optional[str]) -> Tuple[str, Optional[str]]:
    group = str(row.get(group_column, "")).strip()
    step = None
    if step_column is not None:
        raw_step = row.get(step_column)
        step = str(raw_step).strip() if raw_step not in (None, "") else None
    return group, step


def bootstrap_interval(values: Sequence[float], confidence: float, draws: int, rng: random.Random) -> Tuple[float, float]:
    if not values:
        raise ValueError("cannot bootstrap an empty sequence")
    if draws <= 0:
        value = sum(values) / len(values)
        return value, value
    samples: List[float] = []
    n = len(values)
    for _ in range(draws):
        total = 0.0
        for _ in range(n):
            total += values[rng.randrange(n)]
        samples.append(total / n)
    samples.sort()
    alpha = (1.0 - confidence) / 2.0
    lower_index = max(0, min(len(samples) - 1, int(math.floor(alpha * len(samples)))))
    upper_index = max(0, min(len(samples) - 1, int(math.ceil((1.0 - alpha) * len(samples))) - 1))
    return samples[lower_index], samples[upper_index]


def bootstrap_delta_interval(
    treatment: Sequence[float],
    baseline: Sequence[float],
    confidence: float,
    draws: int,
    rng: random.Random,
) -> Tuple[float, float, float]:
    delta = sum(treatment) / len(treatment) - sum(baseline) / len(baseline)
    if draws <= 0:
        return delta, delta, delta
    samples: List[float] = []
    n_t = len(treatment)
    n_b = len(baseline)
    for _ in range(draws):
        t_sum = 0.0
        b_sum = 0.0
        for _ in range(n_t):
            t_sum += treatment[rng.randrange(n_t)]
        for _ in range(n_b):
            b_sum += baseline[rng.randrange(n_b)]
        samples.append(t_sum / n_t - b_sum / n_b)
    samples.sort()
    alpha = (1.0 - confidence) / 2.0
    lower_index = max(0, min(len(samples) - 1, int(math.floor(alpha * len(samples)))))
    upper_index = max(0, min(len(samples) - 1, int(math.ceil((1.0 - alpha) * len(samples))) - 1))
    return delta, samples[lower_index], samples[upper_index]


def bootstrap_paired_interval(
    deltas: Sequence[float],
    confidence: float,
    draws: int,
    rng: random.Random,
) -> Tuple[float, float, float]:
    delta = sum(deltas) / len(deltas)
    if draws <= 0:
        return delta, delta, delta
    samples: List[float] = []
    n = len(deltas)
    for _ in range(draws):
        total = 0.0
        for _ in range(n):
            total += deltas[rng.randrange(n)]
        samples.append(total / n)
    samples.sort()
    alpha = (1.0 - confidence) / 2.0
    lower_index = max(0, min(len(samples) - 1, int(math.floor(alpha * len(samples)))))
    upper_index = max(0, min(len(samples) - 1, int(math.ceil((1.0 - alpha) * len(samples))) - 1))
    return delta, samples[lower_index], samples[upper_index]


def values_by_seed(records: Sequence[Dict[str, Any]], group: str, step: Optional[str]) -> Dict[str, float]:
    mapping: Dict[str, float] = {}
    for record in records:
        if record.get("group") == group and record.get("step") == step and record.get("seed"):
            mapping[str(record["seed"])] = float(record["value"])
    return mapping


def summarize_group(group: str, step: Optional[str], values: List[float], confidence: float) -> Dict[str, Any]:
    n = len(values)
    mean = statistics.mean(values)
    warnings: List[str] = []
    if n == 1:
        sd = None
        sem = None
        interval = [mean, mean]
        warnings.append("single seed: report it as 'single seed' and do not claim a stable interval")
    else:
        sd = statistics.stdev(values)
        sem = sd / math.sqrt(n)
        critical, used_normal = t_critical(n - 1, confidence)
        interval = [mean - critical * sem, mean + critical * sem]
        if used_normal:
            warnings.append("non-95% confidence uses a normal approximation, not a t interval")
        if sd == 0:
            warnings.append("zero variance: interval collapses to a point")
    if n < 3:
        warnings.append(f"n={n}: fewer than 3 seeds; treat differences as exploratory")
    if n == 1:
        ci_note = "single seed; no interval"
    elif n < 3:
        ci_note = "n<3; exploratory interval"
    else:
        ci_note = ""
    return {
        "group": group,
        "step": step,
        "n": n,
        "mean": mean,
        "sd": sd,
        "sem": sem,
        "ci": interval,
        "ci_note": ci_note,
        "min": min(values),
        "max": max(values),
        "values": values,
        "warnings": warnings,
    }


def compare_groups(
    baseline: Dict[str, Any],
    treatment: Dict[str, Any],
    baseline_records: Sequence[Dict[str, Any]],
    treatment_records: Sequence[Dict[str, Any]],
    confidence: float,
    bootstrap: int,
    rng: random.Random,
) -> Dict[str, Any]:
    baseline_values = list(baseline["values"])
    treatment_values = list(treatment["values"])
    warnings: List[str] = []
    if len(treatment_values) < 2 or len(baseline_values) < 2:
        warnings.append("one or both arms have fewer than 2 seeds: no stable difference interval")

    baseline_seeds = values_by_seed(baseline_records, baseline["group"], baseline["step"])
    treatment_seeds = values_by_seed(treatment_records, treatment["group"], treatment["step"])
    common_seeds = sorted(set(baseline_seeds) & set(treatment_seeds))

    if len(common_seeds) >= 2:
        paired_deltas = [treatment_seeds[seed] - baseline_seeds[seed] for seed in common_seeds]
        delta, lower, upper = bootstrap_paired_interval(paired_deltas, confidence, bootstrap, rng)
        method = "paired-bootstrap"
        warnings.append(f"paired on {len(common_seeds)} common seeds")
        if len(common_seeds) < 3:
            warnings.append(f"paired n={len(common_seeds)}: fewer than 3 seed pairs; treat as exploratory")
    else:
        delta, lower, upper = bootstrap_delta_interval(
            treatment_values,
            baseline_values,
            confidence,
            bootstrap,
            rng,
        )
        method = "unpaired-bootstrap"
        if common_seeds:
            warnings.append("only one common seed; using unpaired interval")
        if len(treatment_values) != len(baseline_values):
            warnings.append("unequal arm sizes: comparison is unpaired at group level")

    if bootstrap <= 0:
        warnings.append("bootstrap disabled: interval is a point estimate")
    elif bootstrap < 200:
        warnings.append(f"bootstrap={bootstrap}: small resample count; increase it for a stable interval")

    return {
        "baseline": baseline["group"],
        "variant": treatment["group"],
        "step": treatment["step"],
        "n_baseline": len(baseline_values),
        "n_variant": len(treatment_values),
        "n_pairs": len(common_seeds) if len(common_seeds) >= 2 else 0,
        "delta": delta,
        "ci": [lower, upper],
        "method": method,
        "warnings": warnings,
    }


def format_number(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def format_markdown(summary: Dict[str, Any]) -> str:
    lines = [
        f"# Experiment analysis: {summary['input']}",
        "",
        f"- Rows loaded: {summary['n_rows_loaded']}",
        f"- Rows used: {summary['n_rows_used']}",
        f"- Confidence: {summary['confidence']}",
        f"- Bootstrap draws: {summary['bootstrap']}",
        "",
        "## Groups",
        "",
        "| Group | Step | n | Mean | SD | 95% CI | Min | Max |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for group in summary["groups"]:
        interval = f"[{format_number(group['ci'][0])}, {format_number(group['ci'][1])}]"
        if group.get("ci_note"):
            interval = f"{interval} ({group['ci_note']})"
        lines.append(
            "| {group} | {step} | {n} | {mean} | {sd} | {ci} | {min} | {max} |".format(
                group=group["group"],
                step=group["step"] or "",
                n=group["n"],
                mean=format_number(group["mean"]),
                sd=format_number(group["sd"]),
                ci=interval,
                min=format_number(group["min"]),
                max=format_number(group["max"]),
            )
        )
    lines.extend(["", "## Comparisons", ""])
    if summary["comparisons"]:
        lines.extend([
            "| Variant | Baseline | Step | Delta | 95% CI | n (variant/baseline) | n_pairs |",
            "| --- | --- | --- | ---: | --- | --- | --- |",
        ])
        for comparison in summary["comparisons"]:
            lines.append(
                "| {variant} | {baseline} | {step} | {delta} | [{lo}, {hi}] | {nv}/{nb} | {npairs} |".format(
                    variant=comparison["variant"],
                    baseline=comparison["baseline"],
                    step=comparison["step"] or "",
                    delta=format_number(comparison["delta"]),
                    lo=format_number(comparison["ci"][0]),
                    hi=format_number(comparison["ci"][1]),
                    nv=comparison["n_variant"],
                    nb=comparison["n_baseline"],
                    npairs=comparison.get("n_pairs", 0),
                )
            )
    else:
        lines.append("No baseline comparison requested or baseline group not found.")
    lines.extend(["", "## Provenance", ""])
    for group in summary["groups"]:
        lines.append(
            "- {group} @ {step}: runs={runs}; seeds={seeds}".format(
                group=group["group"],
                step=group["step"] or "final",
                runs=", ".join(group.get("run_ids") or []) or "not provided",
                seeds=", ".join(group.get("seeds") or []) or "not provided",
            )
        )
    lines.extend(["", "## Warnings", ""])
    if summary["warnings"]:
        lines.extend(f"- {warning}" for warning in summary["warnings"])
    else:
        lines.append("- None")
    if summary["dropped"]:
        lines.extend(["", "## Dropped rows", "", "| Row | Reason |", "| ---: | --- |"])
        for item in summary["dropped"]:
            lines.append(f"| {item['row']} | {item['reason']} |")
    return "\n".join(lines) + "\n"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize tidy experiment runs (CSV or JSONL).")
    parser.add_argument("--input", required=True, help="CSV or JSONL input path.")
    parser.add_argument("--group", default="variant", help="Group/variant column name.")
    parser.add_argument("--value", default="value", help="Numeric metric column name.")
    parser.add_argument("--run-id", default="run_id", help="Run id column name.")
    parser.add_argument("--seed", default="seed", help="Seed column name.")
    parser.add_argument("--step", default=None, help="Optional step/epoch/token column; aggregates per step.")
    parser.add_argument("--status-column", default=None, help="Optional status column used for filtering.")
    parser.add_argument("--ok-status", default="completed,success,succeeded,done,ok,passed")
    parser.add_argument(
        "--duplicate-policy",
        choices=("first", "keep", "error"),
        default="first",
        help="How to handle duplicate (group, run_id, seed) rows.",
    )
    parser.add_argument("--baseline", default=None, help="Baseline group used for differences.")
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--random-seed", type=int, default=0)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", default=None)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if not (0.0 < args.confidence < 1.0):
        print("--confidence must be between 0 and 1", file=sys.stderr)
        return 2
    if args.bootstrap < 0:
        print("--bootstrap must be >= 0", file=sys.stderr)
        return 2
    path = Path(args.input)
    if not path.exists():
        print(f"input not found: {path}", file=sys.stderr)
        return 2
    try:
        rows = load_rows(path)
    except Exception as exc:
        print(f"cannot read input: {exc}", file=sys.stderr)
        return 2
    if not rows:
        print("input contains no rows", file=sys.stderr)
        return 3
    columns = set(rows[0].keys())
    if args.group not in columns or args.value not in columns:
        print(
            f"missing required column(s): {args.group!r}, {args.value!r}; available: {sorted(columns)}",
            file=sys.stderr,
        )
        return 2
    if args.step and args.step not in columns:
        print(f"step column not found: {args.step!r}", file=sys.stderr)
        return 2
    if args.status_column and args.status_column not in columns:
        print(f"status column not found: {args.status_column!r}", file=sys.stderr)
        return 2

    ok_status = {status.strip().lower() for status in args.ok_status.split(",") if status.strip()}
    dropped: List[Dict[str, Any]] = []
    records: List[Dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        group, step = group_key(row, args.group, args.step)
        if not group:
            dropped.append({"row": index, "reason": f"empty {args.group!r}"})
            continue
        if args.status_column:
            status = str(row.get(args.status_column, "")).strip().lower()
            if status not in ok_status:
                dropped.append({"row": index, "reason": f"status {status!r} not in ok statuses"})
                continue
        value = as_float(row.get(args.value))
        if value is None:
            dropped.append({"row": index, "reason": f"missing or non-finite {args.value!r}"})
            continue
        run_id = str(row.get(args.run_id, "")).strip() if args.run_id in columns else ""
        seed = str(row.get(args.seed, "")).strip() if args.seed in columns else ""
        records.append({"row": index, "group": group, "step": step, "value": value, "run_id": run_id, "seed": seed})

    if not records:
        print("no valid numeric rows", file=sys.stderr)
        return 3

    warnings: List[str] = []
    duplicate_keys = Counter(
        (record["group"], record["step"], record["run_id"], record["seed"])
        for record in records
        if record["run_id"] or record["seed"]
    )
    duplicates = [key for key, count in duplicate_keys.items() if count > 1]
    if duplicates:
        if args.duplicate_policy == "error":
            print(
                f"{len(duplicates)} duplicate run/seed key(s) detected; refusing to aggregate",
                file=sys.stderr,
            )
            return 2
        if args.duplicate_policy == "first":
            seen_keys: set = set()
            kept_records: List[Dict[str, Any]] = []
            for record in records:
                key = (record["group"], record["step"], record["run_id"], record["seed"])
                if (record["run_id"] or record["seed"]) and key in seen_keys:
                    dropped.append(
                        {"row": record["row"], "reason": "duplicate run/seed key; kept first occurrence"}
                    )
                    continue
                seen_keys.add(key)
                kept_records.append(record)
            records = kept_records
            warnings.append(
                f"{len(duplicates)} duplicate run/seed key(s) detected; kept first occurrence"
            )
        else:
            warnings.append(
                f"{len(duplicates)} duplicate run/seed key(s) detected; kept all occurrences; n includes duplicate rows and is not independent"
            )

    if args.step is None:
        implicit_step_columns = [name for name in ("step", "epoch", "token") if name in columns]
        if implicit_step_columns:
            warnings.append(
                "step-like column(s) present but --step not provided; rows may represent multiple steps"
            )

    groups: Dict[Tuple[str, Optional[str]], List[float]] = defaultdict(list)
    records_by_group: Dict[Tuple[str, Optional[str]], List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[(record["group"], record["step"])].append(record["value"])
        records_by_group[(record["group"], record["step"])].append(record)

    group_summaries: List[Dict[str, Any]] = []
    for (group, step), values in sorted(groups.items(), key=lambda item: (item[0][0], item[0][1] or "")):
        summary = summarize_group(group, step, values, args.confidence)
        group_records = records_by_group[(group, step)]
        summary["run_ids"] = sorted({record["run_id"] for record in group_records if record["run_id"]})
        summary["seeds"] = sorted({record["seed"] for record in group_records if record["seed"]})
        group_summaries.append(summary)
        warnings.extend(f"{group}@{step or 'final'}: {warning}" for warning in summary["warnings"])

    comparisons: List[Dict[str, Any]] = []
    if args.baseline:
        rng = random.Random(args.random_seed)
        for treatment in group_summaries:
            if treatment["group"] == args.baseline:
                continue
            baseline_rows = [
                item for item in group_summaries
                if item["group"] == args.baseline and item["step"] == treatment["step"]
            ]
            if not baseline_rows:
                warnings.append(
                    f"baseline {args.baseline!r} missing for step {treatment['step']!r}; comparison skipped"
                )
                continue
            comparisons.append(
                compare_groups(
                    baseline_rows[0],
                    treatment,
                    records_by_group[(baseline_rows[0]["group"], baseline_rows[0]["step"])],
                    records_by_group[(treatment["group"], treatment["step"])],
                    args.confidence,
                    args.bootstrap,
                    rng,
                )
            )
    else:
        warnings.append("no --baseline provided; only group summaries were produced")

    for comparison in comparisons:
        warnings.extend(
            f"{comparison['variant']} vs {comparison['baseline']}: {warning}"
            for warning in comparison["warnings"]
        )

    summary = {
        "input": str(path),
        "group_column": args.group,
        "value_column": args.value,
        "step_column": args.step,
        "confidence": args.confidence,
        "bootstrap": args.bootstrap,
        "random_seed": args.random_seed,
        "duplicate_policy": args.duplicate_policy,
        "n_rows_loaded": len(rows),
        "n_rows_used": len(records),
        "dropped": dropped,
        "groups": group_summaries,
        "comparisons": comparisons,
        "warnings": warnings,
    }

    output = json.dumps(summary, ensure_ascii=False, indent=2) if args.format == "json" else format_markdown(summary)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)