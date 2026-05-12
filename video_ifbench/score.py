from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from tqdm import tqdm

from .function_judges import CONSTRAINT_FUNCTION_SPECS, FUNCTION_REGISTRY
from .metrics import summarize_cases
from .openai_client import OpenAICompatibleClient, extract_json_object


def ensure_text(value: Any) -> str:
    return str(value or "").strip()


def yes(answer: Any) -> bool:
    return ensure_text(answer).lower() == "yes" or answer is True


def build_llm_judge_prompt(*, instruction: str, response_text: str, constraint_inputs: Sequence[Dict[str, Any]]) -> str:
    return (
        "You are a deterministic instruction-following judge.\n"
        "Judge each constraint item using the final active instruction, the assistant response, "
        "the item's checklist_query, and the item's judge_context when available.\n"
        "For each item, decide whether the response satisfies the checklist query under the provided instruction.\n"
        "Return exactly one Yes/No answer and one concise rationale for each item, preserving the order.\n"
        "Return JSON only in this format: {\"items\": [{\"constraint_id\": \"...\", \"answer\": \"Yes\", \"rationale\": \"...\"}, ...]}\n"
        "For each item, copy back the same constraint_id you were given.\n\n"
        f"Final active instruction:\n{instruction}\n\n"
        f"Assistant response:\n{response_text}\n\n"
        "Constraint items:\n"
        f"{json.dumps(list(constraint_inputs), ensure_ascii=False, indent=2)}\n"
    )


def build_task_judge_prompt(*, instruction: str, response_text: str, task_inputs: Sequence[Dict[str, Any]]) -> str:
    return (
        "You are a deterministic task-execution judge for video-understanding instructions.\n"
        "Judge whether the response attempts and executes each requested task under the final active instruction.\n"
        "Judge task execution, not factual correctness. Answer Yes if the response clearly addresses the requested task, "
        "even if some factual details may be imperfect. Answer No if it skips the task, answers a different task, refuses, "
        "or is too vague to count.\n"
        "Return JSON only in this format: {\"items\": [{\"task_name\": \"...\", \"answer\": \"Yes\", \"rationale\": \"...\"}, ...]}\n"
        "For each item, copy back the same task_name you were given.\n\n"
        f"Final active instruction:\n{instruction}\n\n"
        f"Assistant response:\n{response_text}\n\n"
        "Task items:\n"
        f"{json.dumps(list(task_inputs), ensure_ascii=False, indent=2)}\n"
    )


def build_rule_extraction_prompt(*, instruction: str, response_text: str, constraint_inputs: Sequence[Dict[str, Any]]) -> str:
    schema = {"answer_list": [{"constraint_id": "string", "extracted_response": "string", "function_calls": [{"function_name": "string", "parameters": {"param_name": "value"}}]}]}
    return (
        "You are preparing deterministic rule-based checks for instruction-following evaluation.\n"
        "For each constraint item, use the checklist_query, function_context, instruction, and assistant response.\n"
        "First extract the minimal response substring needed for validating the listed functions. Return it in extracted_response.\n"
        "The function call plan is fixed by function_context: do not add, remove, or reorder functions.\n"
        "For each listed function, output one object with the same function_name and inferred parameters. "
        "Use only the listed parameter names. If a parameter is not needed or cannot be inferred, return an empty object for that function.\n"
        "Preserve item order and return JSON only.\n\n"
        f"Return schema:\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
        f"Final active instruction:\n{instruction}\n\n"
        f"Assistant response:\n{response_text}\n\n"
        "Constraint items:\n"
        f"{json.dumps(list(constraint_inputs), ensure_ascii=False, indent=2)}\n"
    )


def response_format_schema(name: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": name, "schema": schema}}


def build_rule_constraint_spec_map() -> Dict[str, List[Dict[str, Any]]]:
    return {str(k): list(v or []) for k, v in CONSTRAINT_FUNCTION_SPECS.items()}


def function_spec_name(spec: Mapping[str, Any]) -> str:
    return ensure_text(spec.get("function_name") or spec.get("name"))


def _unwrap_optional_type(param_type: str) -> str:
    text = ensure_text(param_type)
    if text.startswith("Optional[") and text.endswith("]"):
        return text[len("Optional[") : -1]
    return text


def _coerce_parameter_value(param_type: str, value: Any) -> Any:
    kind = _unwrap_optional_type(param_type)
    kind_lower = kind.lower()
    if value is None:
        return None
    if kind.startswith("List[") and kind.endswith("]"):
        inner = kind[len("List[") : -1]
        if isinstance(value, list):
            values = value
        elif isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                try:
                    loaded = json.loads(stripped)
                    values = loaded if isinstance(loaded, list) else [value]
                except json.JSONDecodeError:
                    values = [value]
            else:
                values = [value]
        else:
            values = [value]
        return [
            item
            for item in (_coerce_parameter_value(inner, entry) for entry in values)
            if item is not None and ensure_text(item) != ""
        ]
    if kind_lower in {"int", "integer"}:
        try:
            return int(float(value))
        except Exception:
            return None
    if kind_lower in {"float", "number"}:
        try:
            return float(value)
        except Exception:
            return None
    if kind_lower in {"bool", "boolean"}:
        if isinstance(value, bool):
            return value
        text = ensure_text(value).lower()
        if text in {"true", "yes", "1"}:
            return True
        if text in {"false", "no", "0"}:
            return False
        return None
    if kind_lower in {"list", "array"}:
        return value if isinstance(value, list) else [value]
    if kind_lower in {"str", "string"}:
        return ensure_text(value)
    return value


def sanitize_rule_parameters(function_spec: Dict[str, Any], parameters: Any) -> Dict[str, Any]:
    raw = parameters if isinstance(parameters, dict) else {}
    allowed = {ensure_text(x.get("name")): x for x in function_spec.get("parameters", []) if isinstance(x, dict) and ensure_text(x.get("name"))}
    result: Dict[str, Any] = {}
    for name, value in raw.items():
        key = ensure_text(name)
        if key not in allowed:
            continue
        coerced = _coerce_parameter_value(ensure_text(allowed[key].get("type")), value)
        if coerced is not None and coerced != "":
            result[key] = coerced
    for name, spec in allowed.items():
        if name not in result and "default" in spec:
            result[name] = _coerce_parameter_value(ensure_text(spec.get("type")), spec.get("default"))
    return result


def evaluate_llm_constraints(client: OpenAICompatibleClient, instruction: str, response_text: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not items:
        return []
    prompt_items = [{"constraint_id": x.get("constraint_id"), "checklist_query": x.get("checklist_query", ""), "judge_context": x.get("judge_context", "")} for x in items]
    prompt = build_llm_judge_prompt(instruction=instruction, response_text=response_text, constraint_inputs=prompt_items)
    schema = {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object"}}}, "required": ["items"]}
    parsed = extract_json_object(client.chat([{"role": "user", "content": prompt}], response_format=response_format_schema("constraint_judge", schema)))
    by_id = {ensure_text(x.get("constraint_id")): x for x in parsed.get("items", []) if isinstance(x, dict)}
    results = []
    for original in items:
        cid = ensure_text(original.get("constraint_id"))
        judged = by_id.get(cid, {})
        results.append({**original, "mode": "llm_judge", "answer": judged.get("answer"), "passed": yes(judged.get("answer")), "rationale": ensure_text(judged.get("rationale"))})
    return results


def evaluate_task_items(client: OpenAICompatibleClient, instruction: str, response_text: str, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not tasks:
        return []
    prompt_items = [{"task_name": x.get("task_name") or x.get("name") or x.get("task"), "task_description": x.get("task_description") or x.get("description") or x} for x in tasks]
    prompt = build_task_judge_prompt(instruction=instruction, response_text=response_text, task_inputs=prompt_items)
    schema = {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object"}}}, "required": ["items"]}
    parsed = extract_json_object(client.chat([{"role": "user", "content": prompt}], response_format=response_format_schema("task_judge", schema)))
    by_name = {ensure_text(x.get("task_name")): x for x in parsed.get("items", []) if isinstance(x, dict)}
    results = []
    for original, prompt_item in zip(tasks, prompt_items):
        name = ensure_text(prompt_item.get("task_name"))
        judged = by_name.get(name, {})
        results.append({**original, "task_name": name, "answer": judged.get("answer"), "passed": yes(judged.get("answer")), "rationale": ensure_text(judged.get("rationale"))})
    return results


def evaluate_rule_constraints(client: OpenAICompatibleClient, instruction: str, response_text: str, items: List[Dict[str, Any]], spec_map: Mapping[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if not items:
        return []
    prompt_items = []
    for item in items:
        cid = ensure_text(item.get("constraint_id"))
        prompt_items.append({"constraint_id": cid, "checklist_query": item.get("checklist_query", ""), "function_context": spec_map.get(cid, [])})
    schema = {"type": "object", "properties": {"answer_list": {"type": "array", "items": {"type": "object"}}}, "required": ["answer_list"]}
    parsed = extract_json_object(client.chat([{"role": "user", "content": build_rule_extraction_prompt(instruction=instruction, response_text=response_text, constraint_inputs=prompt_items)}], response_format=response_format_schema("rule_extraction", schema)))
    by_id = {ensure_text(x.get("constraint_id")): x for x in parsed.get("answer_list", []) if isinstance(x, dict)}
    results: List[Dict[str, Any]] = []
    for original in items:
        cid = ensure_text(original.get("constraint_id"))
        extracted = by_id.get(cid, {})
        target_text = ensure_text(extracted.get("extracted_response")) or response_text
        function_results = []
        planned = extracted.get("function_calls") if isinstance(extracted.get("function_calls"), list) else []
        planned_by_name = {ensure_text(x.get("function_name")): x for x in planned if isinstance(x, dict)}
        for spec in spec_map.get(cid, []):
            fname = function_spec_name(spec)
            if fname not in FUNCTION_REGISTRY:
                function_results.append({"function_name": fname, "passed": False, "reason": "Function not found in registry.", "details": {}})
                continue
            call = planned_by_name.get(fname, {})
            params = sanitize_rule_parameters(spec, call.get("parameters"))
            try:
                result = FUNCTION_REGISTRY[fname](response=target_text, **params)
                function_results.append(result if isinstance(result, dict) else {"function_name": fname, "passed": bool(result), "reason": "", "details": {}})
            except Exception as exc:
                function_results.append({"function_name": fname, "passed": False, "reason": str(exc), "details": {"error_type": type(exc).__name__}})
        passed = bool(function_results) and all(bool(x.get("passed")) for x in function_results)
        rationale = "; ".join(ensure_text(x.get("reason")) for x in function_results if ensure_text(x.get("reason")))
        results.append({**original, "mode": "function_call", "passed": passed, "answer": "Yes" if passed else "No", "rationale": rationale, "extracted_response": target_text, "function_results": function_results})
    return results


def load_response(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_response_jsons(response_dir: Path) -> List[Path]:
    return sorted(response_dir.rglob("*.response.json"))


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def thinking_chat_template_kwargs(mode: str) -> Optional[Dict[str, bool]]:
    if mode == "auto":
        return None
    if mode == "enabled":
        return {"enable_thinking": True}
    return {"enable_thinking": False}


def evaluate_response(path: Path, judge_client: OpenAICompatibleClient, extract_client: OpenAICompatibleClient, task_client: OpenAICompatibleClient, spec_map: Mapping[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    payload = load_response(path)
    meta = payload.get("_meta") or {}
    case_id = ensure_text(payload.get("case_id") or meta.get("case_id") or path.stem)
    response_text = ensure_text(payload.get("response_text"))
    if payload.get("error"):
        return {"case_id": case_id, "status": "error", "error": payload.get("error"), "response_json": str(path), "response_meta": meta}
    instruction = ensure_text(meta.get("active_instruction") or meta.get("instruction"))
    constraints = list(meta.get("constraints") or [])
    tasks = list(meta.get("tasks") or [])
    rule_items = [x for x in constraints if ensure_text(x.get("constraint_id")) in spec_map]
    llm_items = [x for x in constraints if ensure_text(x.get("constraint_id")) not in spec_map]
    rule_results = evaluate_rule_constraints(extract_client, instruction, response_text, rule_items, spec_map)
    llm_results = evaluate_llm_constraints(judge_client, instruction, response_text, llm_items)
    task_results = evaluate_task_items(task_client, instruction, response_text, tasks)
    result_buckets = {"rule": list(rule_results), "llm": list(llm_results)}
    constraint_results = []
    for original in constraints:
        cid = ensure_text(original.get("constraint_id"))
        bucket_name = "rule" if cid in spec_map else "llm"
        bucket = result_buckets[bucket_name]
        match_index = next((i for i, item in enumerate(bucket) if item.get("constraint_id") == original.get("constraint_id") and item.get("checklist_query") == original.get("checklist_query")), None)
        if match_index is not None:
            constraint_results.append(bucket.pop(match_index))
    constraint_results.extend(result_buckets["rule"])
    constraint_results.extend(result_buckets["llm"])
    c_passed = sum(int(bool(x.get("passed"))) for x in constraint_results)
    c_total = len(constraint_results)
    t_passed = sum(int(bool(x.get("passed"))) for x in task_results)
    t_total = len(task_results)
    constraint_all = (c_passed == c_total) if c_total else True
    task_all = (t_passed == t_total) if t_total else None
    return {
        "case_id": case_id,
        "status": "ok",
        "response_json": str(path),
        "video_path": meta.get("video_path"),
        "instruction_key": meta.get("instruction_key"),
        "instruction_type": meta.get("instruction_type"),
        "instruction": meta.get("instruction"),
        "active_instruction": instruction,
        "response_text": response_text,
        "constraint_results": constraint_results,
        "constraint_summary": {"passed": c_passed, "total": c_total, "accuracy": round(c_passed / c_total, 4) if c_total else None},
        "task_results": task_results,
        "task_summary": {"passed": t_passed, "total": t_total, "accuracy": round(t_passed / t_total, 4) if t_total else None},
        "instruction_result": {"passed": bool(constraint_all and (task_all is not False)), "constraint_all_passed": constraint_all, "task_all_passed": task_all},
        "response_meta": meta,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score Video-IFBench model responses with OpenAI-compatible judges.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--response-dir")
    src.add_argument("--response-json")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--judge-api-base", required=True)
    parser.add_argument("--judge-model", required=True)
    parser.add_argument("--judge-api-key", default=None)
    parser.add_argument("--judge-api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--extract-api-base", default=None)
    parser.add_argument("--extract-model", default=None)
    parser.add_argument("--task-judge-api-base", default=None)
    parser.add_argument("--task-judge-model", default=None)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--timeout-sec", type=float, default=300.0)
    parser.add_argument("--concurrency", type=positive_int, default=1, help="Number of response files to score concurrently.")
    parser.add_argument("--thinking-mode", choices=["disabled", "enabled", "auto"], default="disabled", help="Pass Qwen/vLLM enable_thinking chat-template kwargs for judge calls. Default: disabled.")
    parser.add_argument("--enable-thinking", action="store_const", dest="thinking_mode", const="enabled", help="Shortcut for --thinking-mode enabled.")
    parser.add_argument("--disable-thinking", action="store_const", dest="thinking_mode", const="disabled", help="Shortcut for --thinking-mode disabled.")
    return parser.parse_args()


def score_one_response(path: Path, judge: OpenAICompatibleClient, extract: OpenAICompatibleClient, task: OpenAICompatibleClient, spec_map: Mapping[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    try:
        return evaluate_response(path, judge, extract, task, spec_map)
    except Exception as exc:
        return {"case_id": path.stem, "status": "error", "response_json": str(path), "error": {"type": type(exc).__name__, "message": str(exc)}}


def main() -> None:
    args = parse_args()
    started = time.time()
    response_paths = [Path(args.response_json)] if args.response_json else discover_response_jsons(Path(args.response_dir))
    chat_template_kwargs = thinking_chat_template_kwargs(args.thinking_mode)
    judge = OpenAICompatibleClient(api_base=args.judge_api_base, model=args.judge_model, api_key=args.judge_api_key, api_key_env=args.judge_api_key_env, temperature=args.temperature, max_tokens=args.max_tokens, timeout=args.timeout_sec, chat_template_kwargs=chat_template_kwargs)
    extract = OpenAICompatibleClient(api_base=args.extract_api_base or args.judge_api_base, model=args.extract_model or args.judge_model, api_key=args.judge_api_key, api_key_env=args.judge_api_key_env, temperature=args.temperature, max_tokens=args.max_tokens, timeout=args.timeout_sec, chat_template_kwargs=chat_template_kwargs)
    task = OpenAICompatibleClient(api_base=args.task_judge_api_base or args.judge_api_base, model=args.task_judge_model or args.judge_model, api_key=args.judge_api_key, api_key_env=args.judge_api_key_env, temperature=args.temperature, max_tokens=args.max_tokens, timeout=args.timeout_sec, chat_template_kwargs=chat_template_kwargs)
    spec_map = build_rule_constraint_spec_map()
    cases: Dict[str, Dict[str, Any]] = {}
    if args.concurrency == 1:
        for path in tqdm(response_paths, desc="Video-IFBench score"):
            result = score_one_response(path, judge, extract, task, spec_map)
            cases[ensure_text(result.get("case_id")) or path.stem] = result
    else:
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            future_to_path = {executor.submit(score_one_response, path, judge, extract, task, spec_map): path for path in response_paths}
            for future in tqdm(as_completed(future_to_path), total=len(future_to_path), desc="Video-IFBench score"):
                path = future_to_path[future]
                result = future.result()
                cases[ensure_text(result.get("case_id")) or path.stem] = result
    report = {
        "_meta": {
            "generated_by": "video-ifbench-score",
            "response_dir": args.response_dir,
            "response_json": args.response_json,
            "output_json": args.output_json,
            "source_case_count": len(response_paths),
            "concurrency": args.concurrency,
            "thinking_mode": args.thinking_mode,
            "elapsed_sec": round(time.time() - started, 3),
            "judge_runtime": judge.runtime_meta(),
            "extract_runtime": extract.runtime_meta(),
            "task_judge_runtime": task.runtime_meta(),
        },
        "summary": summarize_cases(cases),
        "cases": dict(sorted(cases.items())),
    }
    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
