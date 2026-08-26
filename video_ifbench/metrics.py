from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, Mapping


def _is_yes(value: Any) -> bool:
    return str(value or "").strip().lower() == "yes" or bool(value is True)


def case_status(case: Mapping[str, Any]) -> str:
    return str(case.get("status") or "ok")


def _empty_stats() -> Dict[str, Any]:
    return {
        "case_passed": 0,
        "task_all_passed_case_passed": 0,
        "case_total": 0,
        "tcsr_sum": 0.0,
        "tisr_passed": 0,
        "constraint_passed": 0,
        "constraint_total": 0,
        "task_passed": 0,
        "task_total": 0,
    }


def _format_row(stats: Dict[str, Any]) -> Dict[str, Any]:
    total = stats["case_total"]
    return {
        "tcsr": round(stats["tcsr_sum"] / total, 4) if total else None,
        "tisr": round(stats["tisr_passed"] / total, 4) if total else None,
        "instruction_accuracy": round(stats["case_passed"] / total, 4) if total else None,
        "instruction_task_accuracy": round(stats["task_all_passed_case_passed"] / total, 4) if total else None,
        "constraint_accuracy": round(stats["constraint_passed"] / stats["constraint_total"], 4) if stats["constraint_total"] else None,
        "task_item_accuracy": round(stats["task_passed"] / stats["task_total"], 4) if stats["task_total"] else None,
        "instruction_passed": stats["case_passed"],
        "instruction_task_passed": stats["task_all_passed_case_passed"],
        "instruction_total": total,
        "tisr_passed": stats["tisr_passed"],
        "tcsr_sum": round(stats["tcsr_sum"], 4),
        "constraint_passed": stats["constraint_passed"],
        "constraint_total": stats["constraint_total"],
        "task_passed": stats["task_passed"],
        "task_total": stats["task_total"],
    }


def summarize_cases(cases: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    by_type: Dict[str, Dict[str, Any]] = defaultdict(_empty_stats)
    by_constraint: Dict[str, Dict[str, int]] = defaultdict(lambda: {"passed": 0, "total": 0})
    total = _empty_stats()
    error_cases = []

    for case_id, case in cases.items():
        if case_status(case) != "ok":
            error_cases.append({"case_id": case_id, "error": case.get("error")})
            continue
        inst_type = str(case.get("instruction_type") or "").lower()
        c_summary = case.get("constraint_summary") or {}
        t_summary = case.get("task_summary") or {}
        instr = case.get("instruction_result") or {}
        constraint_accuracy = float(c_summary.get("accuracy") or 0.0)
        task_all = instr.get("task_all_passed")
        task_gate = 1 if task_all is None else int(bool(task_all))
        constraint_all = bool(instr.get("constraint_all_passed"))
        instruction_passed = int(bool(task_gate and constraint_all))
        tcsr_value = task_gate * constraint_accuracy
        tisr_value = instruction_passed
        buckets = [total, by_type[inst_type]]
        for stats in buckets:
            stats["case_total"] += 1
            stats["case_passed"] += instruction_passed
            stats["task_all_passed_case_passed"] += int(bool(task_all)) if task_all is not None else 1
            stats["tcsr_sum"] += tcsr_value
            stats["tisr_passed"] += tisr_value
            stats["constraint_passed"] += int(c_summary.get("passed") or 0)
            stats["constraint_total"] += int(c_summary.get("total") or 0)
            stats["task_passed"] += int(t_summary.get("passed") or 0)
            stats["task_total"] += int(t_summary.get("total") or 0)
        for item in case.get("constraint_results") or []:
            cid = str(item.get("constraint_id") or "")
            if not cid:
                continue
            by_constraint[cid]["passed"] += int(bool(item.get("passed")))
            by_constraint[cid]["total"] += 1

    multi_raw = _empty_stats()
    for name in ("multi", "compose", "chain"):
        if name not in by_type:
            continue
        for key in multi_raw:
            multi_raw[key] += by_type[name][key]

    return {
        "case_status": {"recorded_total": len(cases), "ok": total["case_total"], "error": len(error_cases)},
        "instruction_accuracy": {"passed": total["case_passed"], "total": total["case_total"], "accuracy": _format_row(total)["instruction_accuracy"]},
        "tcsr": {"score_sum": round(total["tcsr_sum"], 4), "total": total["case_total"], "accuracy": _format_row(total)["tcsr"]},
        "tisr": {"passed": total["tisr_passed"], "total": total["case_total"], "accuracy": _format_row(total)["tisr"]},
        "instruction_task_accuracy": {"passed": total["task_all_passed_case_passed"], "total": total["case_total"], "accuracy": _format_row(total)["instruction_task_accuracy"]},
        "constraint_accuracy": {"passed": total["constraint_passed"], "total": total["constraint_total"], "accuracy": _format_row(total)["constraint_accuracy"]},
        "task_item_accuracy": {"passed": total["task_passed"], "total": total["task_total"], "accuracy": _format_row(total)["task_item_accuracy"]},
        "by_instruction_type": {k: _format_row(v) for k, v in sorted(by_type.items())},
        "multi": _format_row(multi_raw),
        "by_constraint_id": {k: {"passed": v["passed"], "total": v["total"], "accuracy": round(v["passed"] / v["total"], 4) if v["total"] else None} for k, v in sorted(by_constraint.items())},
        "error_cases": error_cases,
    }
