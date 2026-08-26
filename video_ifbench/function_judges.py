from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Sequence

EvaluationResult = Dict[str, Any]

CJK_CHAR_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")
NON_CJK_WORD_PATTERN = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", flags=re.UNICODE)
WORD_COUNT_TRANSLATION = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "‛": "'",
        "`": "'",
        "´": "'",
        "–": "-",
        "—": "-",
        "－": "-",
        "‐": "-",
        "‑": "-",
        "‒": "-",
    }
)
QUOTE_TRANSLATION = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "„": '"',
        "‟": '"',
        "«": '"',
        "»": '"',
        "‘": "'",
        "’": "'",
        "‚": "'",
        "‛": "'",
        "`": "'",
        "´": "'",
    }
)
WORD_UNIT_ALIASES = {"word", "words"}
ZH_LENGTH_UNIT_ALIASES = {
    "zh_length",
    "zh_len",
    "zh-char",
    "zh_char",
    "zh_chars",
    "cjk_length",
    "cjk_char",
    "cjk_chars",
    "char",
    "chars",
    "character",
    "characters",
}
DEFAULT_SPAN_PATTERNS = [
    r"\b\d{1,2}[:：]\d{2}(?::\d{2})?\s*(?:-|–|—|~|to|\u5230|\u81f3)\s*\d{1,2}[:：]\d{2}(?::\d{2})?\b",
    r"\[(?:\d{1,2}[:：])?\d{1,2}:\d{2}\s*(?:-|–|—|~|to|\u5230|\u81f3)\s*(?:\d{1,2}[:：])?\d{1,2}:\d{2}\]",
    r"(?:start|begin|from|\u8d77\u59cb|\u5f00\u59cb)\s*[:：=]?\s*\d{1,2}[:：]\d{2}(?::\d{2})?\s*(?:,|，|;|；|\s)+(?:end|to|until|\u7ed3\u675f|\u622a\u6b62|\u5230)\s*[:：=]?\s*\d{1,2}[:：]\d{2}(?::\d{2})?",
    r"(?:from|\u4ece)\s*\d{1,2}[:：]\d{2}(?::\d{2})?\s*(?:to|\u5230|\u81f3)\s*\d{1,2}[:：]\d{2}(?::\d{2})?",
]
def _build_result(function_name: str, passed: bool, reason: str, **details: Any) -> EvaluationResult:
    return {
        "function_name": function_name,
        "passed": bool(passed),
        "reason": str(reason),
        "details": details,
    }


def _ensure_text(value: Any) -> str:
    return str(value or "").strip()


def _strip_markdown_code_fences(text: str) -> str:
    raw = _ensure_text(text)
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:[A-Za-z0-9_+-]+)?\s*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)
    return raw.strip()


def _target_text(response: str) -> str:
    return _strip_markdown_code_fences(_ensure_text(response))


def _normalize_text(text: str, *, normalize_whitespace: bool = True) -> str:
    value = str(text or "")
    if normalize_whitespace:
        value = re.sub(r"\s+", " ", value)
    return value.strip()


def _non_empty_lines(text: str) -> List[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _count_words(text: str) -> int:
    normalized = _normalize_text(text).translate(WORD_COUNT_TRANSLATION)
    if not normalized:
        return 0
    non_cjk_text = CJK_CHAR_PATTERN.sub(" ", normalized)
    return len(NON_CJK_WORD_PATTERN.findall(non_cjk_text))


def _count_zh_length(text: str) -> int:
    return len(re.sub(r"\s+", "", str(text or "")))


def _safe_json_loads(text: str) -> Any:
    candidates = [_ensure_text(text), _strip_markdown_code_fences(text)]
    extracted_block = _extract_first_json_block(text)
    if extracted_block:
        candidates.append(extracted_block)
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _extract_first_json_block(text: str) -> str:
    raw = _ensure_text(text)
    if not raw:
        return ""
    start_positions = [index for index in (raw.find("{"), raw.find("[")) if index != -1]
    if not start_positions:
        return ""
    start = min(start_positions)
    opening = raw[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(raw)):
        char = raw[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return raw[start : index + 1]
    return ""


def _load_schema_skeleton(schema: Any) -> Optional[Any]:
    if schema is None:
        return None
    if isinstance(schema, (dict, list)):
        return schema
    if isinstance(schema, str):
        parsed = _safe_json_loads(schema)
        return parsed if isinstance(parsed, (dict, list)) else None
    return None


def _json_value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _validate_structure_skeleton(instance: Any, schema: Any, *, path: str = "$") -> List[str]:
    if isinstance(schema, dict):
        if not isinstance(instance, dict):
            return [f"{path}: expected object, got {_json_value_type(instance)}."]
        errors: List[str] = []
        expected_keys = list(schema.keys())
        for key in expected_keys:
            if key not in instance:
                errors.append(f"{path}: missing required property '{key}'.")
        for key in instance:
            if key not in schema:
                errors.append(f"{path}: unexpected property '{key}'.")
        for key in expected_keys:
            if key in instance:
                errors.extend(_validate_structure_skeleton(instance[key], schema[key], path=f"{path}.{key}"))
        return errors

    if isinstance(schema, list):
        if not isinstance(instance, list):
            return [f"{path}: expected array, got {_json_value_type(instance)}."]
        if not schema:
            return []
        errors: List[str] = []
        if len(schema) == 1:
            for index, item in enumerate(instance):
                errors.extend(_validate_structure_skeleton(item, schema[0], path=f"{path}[{index}]"))
            return errors
        if len(instance) != len(schema):
            errors.append(f"{path}: expected array length {len(schema)}, got {len(instance)}.")
        for index in range(min(len(instance), len(schema))):
            errors.extend(_validate_structure_skeleton(instance[index], schema[index], path=f"{path}[{index}]"))
        return errors

    if isinstance(instance, (dict, list)):
        return [f"{path}: expected scalar, got {_json_value_type(instance)}."]
    return []


def _split_markdown_table_row(line: str) -> List[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _is_markdown_separator_cells(cells: Sequence[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) is not None for cell in cells)


def _build_table_payload(
    *,
    format_name: str,
    header: Sequence[str],
    rows: Sequence[Sequence[str]],
    has_header: bool,
) -> Dict[str, Any]:
    normalized_header = [_ensure_text(cell) for cell in header]
    normalized_rows = [[_ensure_text(cell) for cell in row] for row in rows]
    header_is_unique = bool(normalized_header) and len(set(normalized_header)) == len(normalized_header)
    header_has_empty = any(not cell for cell in normalized_header)
    records: List[Dict[str, str]] = []
    if has_header and normalized_header and header_is_unique and not header_has_empty:
        for row in normalized_rows:
            records.append({normalized_header[index]: row[index] for index in range(len(normalized_header))})
    return {
        "format": format_name,
        "has_header": bool(has_header),
        "header": normalized_header,
        "rows": normalized_rows,
        "records": records,
        "row_count": len(normalized_rows),
        "column_count": len(normalized_header) if normalized_header else (len(normalized_rows[0]) if normalized_rows else 0),
        "header_is_unique": header_is_unique,
        "header_has_empty": header_has_empty,
    }


def _parse_markdown_table_payload(text: str) -> Optional[Dict[str, Any]]:
    lines = _non_empty_lines(text)
    if len(lines) < 3:
        return None
    for start_index in range(len(lines) - 2):
        header = _split_markdown_table_row(lines[start_index])
        separator = _split_markdown_table_row(lines[start_index + 1])
        if len(header) < 2 or len(header) != len(separator) or not _is_markdown_separator_cells(separator):
            continue
        body_rows: List[List[str]] = []
        for line in lines[start_index + 2 :]:
            row = _split_markdown_table_row(line)
            if len(row) != len(header):
                break
            body_rows.append(row)
        if body_rows:
            return _build_table_payload(format_name="markdown", header=header, rows=body_rows, has_header=True)
    return None


def _is_scalar_sequence_schema(schema_skeleton: Any) -> bool:
    return isinstance(schema_skeleton, list) and bool(schema_skeleton) and all(not isinstance(item, (dict, list)) for item in schema_skeleton)


def _parse_csv_table_payload(text: str, *, require_header: bool) -> Optional[Dict[str, Any]]:
    lines = _non_empty_lines(text)
    min_line_count = 2 if require_header else 1
    if len(lines) < min_line_count:
        return None
    reader = csv.reader(io.StringIO("\n".join(lines)))
    rows = [[cell.strip() for cell in row] for row in reader if any(cell.strip() for cell in row)]
    if not rows or len(rows[0]) < 2:
        return None
    column_count = len(rows[0])
    if any(len(row) != column_count for row in rows[1:]):
        return None
    if require_header:
        if len(rows) < 2:
            return None
        return _build_table_payload(format_name="csv", header=rows[0], rows=rows[1:], has_header=True)
    return _build_table_payload(format_name="csv", header=[], rows=rows, has_header=False)


def _contains_keyword(text: str, keyword: str, *, ignore_case: bool = True) -> int:
    haystack = _normalize_text(text)
    needle = _normalize_text(keyword)
    if ignore_case:
        haystack = haystack.lower()
        needle = needle.lower()
    if not needle:
        return 0
    if CJK_CHAR_PATTERN.search(needle):
        return haystack.count(needle)
    return len(re.findall(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack))


def _parse_list_like_items(text: str) -> List[str]:
    parsed = _safe_json_loads(text)
    if isinstance(parsed, list):
        return [_ensure_text(item) for item in parsed if _ensure_text(item)]

    lines = _non_empty_lines(text)
    list_marker = re.compile(r"^(?:\d+[\.)]|[-*•])\s+")
    list_items = [list_marker.sub("", line).strip() for line in lines if list_marker.search(line)]
    if list_items and (len(lines) > 1 or len(list_items) > 1):
        return [item for item in list_items if item]

    stripped = _ensure_text(text)
    if stripped and "\n" not in stripped:
        inline_marker = re.compile(r"(?:^|\s)(\d+[\.)])\s+")
        matches = list(inline_marker.finditer(stripped))
        if len(matches) >= 2 and matches[0].group(1).startswith("1"):
            inline_items: List[str] = []
            for index, match in enumerate(matches):
                start = match.start(1)
                end = matches[index + 1].start() if index + 1 < len(matches) else len(stripped)
                segment = stripped[start:end].strip()
                segment = re.sub(r"^\d+[\.)]\s+", "", segment).strip()
                if segment:
                    inline_items.append(segment)
            if len(inline_items) >= 2:
                return inline_items

    if lines and all("," in line or "，" in line for line in lines):
        split_items: List[str] = []
        for line in lines:
            split_items.extend(part.strip() for part in re.split(r"\s*[,，]\s*", line) if part.strip())
        if split_items:
            return split_items

    if re.fullmatch(r"\d+", stripped):
        return [str(index) for index in range(int(stripped))]

    return [line for line in lines if line]


def _flatten_scalar_values(value: Any) -> List[str]:
    scalars: List[str] = []
    if isinstance(value, dict):
        for item in value.values():
            scalars.extend(_flatten_scalar_values(item))
        return scalars
    if isinstance(value, list):
        for item in value:
            scalars.extend(_flatten_scalar_values(item))
        return scalars
    if value is None:
        return scalars
    text = _ensure_text(value)
    if text:
        scalars.append(text)
    return scalars


def _extract_validation_items(
    text: str,
    *,
    allow_multiple: bool,
    separator_pattern: str,
) -> List[str]:
    parsed = _safe_json_loads(text)
    if parsed is not None:
        scalar_items = _flatten_scalar_values(parsed)
        if scalar_items:
            return scalar_items
    if not allow_multiple:
        return [text] if text else []
    return [item.strip() for item in re.split(separator_pattern, text) if item.strip()]


def _contains_phrase(text: str, phrase: str, *, ignore_case: bool = True) -> bool:
    haystack = _normalize_text(text)
    needle = _normalize_text(phrase)
    if not haystack or not needle:
        return False
    if CJK_CHAR_PATTERN.search(needle):
        if ignore_case:
            return needle.lower() in haystack.lower()
        return needle in haystack
    flags = re.IGNORECASE if ignore_case else 0
    pattern = re.compile(rf"(?<!\w){re.escape(needle)}(?!\w)", flags=flags)
    return pattern.search(haystack) is not None


def _normalize_timestamp_token(value: Any) -> str:
    text = _ensure_text(value).replace("：", ":")
    if not text:
        return ""
    if re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", text) is None:
        return ""
    return text


def _extract_structured_span_matches(value: Any) -> List[str]:
    matches: List[str] = []
    if isinstance(value, list):
        for item in value:
            matches.extend(_extract_structured_span_matches(item))
        return matches
    if not isinstance(value, dict):
        return matches

    start_candidates = [
        value.get("start"),
        value.get("start_time"),
        value.get("start_timestamp"),
        value.get("begin"),
        value.get("from"),
    ]
    end_candidates = [
        value.get("end"),
        value.get("end_time"),
        value.get("end_timestamp"),
        value.get("until"),
        value.get("to"),
    ]
    for start_raw in start_candidates:
        start = _normalize_timestamp_token(start_raw)
        if not start:
            continue
        for end_raw in end_candidates:
            end = _normalize_timestamp_token(end_raw)
            if end:
                matches.append(f"{start} - {end}")
                break

    for item in value.values():
        matches.extend(_extract_structured_span_matches(item))
    return matches


def _normalize_quotes(text: str) -> str:
    return str(text or "").translate(QUOTE_TRANSLATION)


def _strip_unicode_punctuation(text: str) -> str:
    return "".join(char for char in str(text or "") if not unicodedata.category(char).startswith("P"))


def _strip_wrapping_quotes(text: str) -> str:
    value = str(text or "").strip()
    quote_pairs = [('"', '"'), ("'", "'")]
    for left, right in quote_pairs:
        if value.startswith(left) and value.endswith(right) and len(value) >= 2:
            return value[1:-1].strip()
    return value


def _extract_quoted_utterances(text: str) -> List[str]:
    normalized = _normalize_quotes(str(text or ""))
    utterances: List[str] = []
    for candidate in re.findall(r'"([^"\n]+)"', normalized):
        candidate = _ensure_text(candidate)
        if candidate:
            utterances.append(candidate)
    for candidate in re.findall(r"(?<![\w])'([^'\n]+)'(?![\w])", normalized):
        candidate = _ensure_text(candidate)
        if candidate:
            utterances.append(candidate)
    return utterances


def _extract_verbatim_segments(text: str) -> List[str]:
    raw = _target_text(text)
    quoted = _extract_quoted_utterances(raw)
    if quoted:
        return quoted
    lines = _non_empty_lines(raw)
    if len(lines) > 1:
        return lines
    return [raw] if raw else []


def _normalize_verbatim_segment(
    text: str,
    *,
    normalize_whitespace: bool = True,
    normalize_quotes: bool = True,
    allow_wrapping_quotes: bool = True,
) -> str:
    value = str(text or "")
    if allow_wrapping_quotes:
        value = _strip_wrapping_quotes(value)
    if normalize_quotes:
        value = _normalize_quotes(value)
    value = _strip_unicode_punctuation(value)
    if normalize_whitespace:
        value = _normalize_text(value)
    return value.lower()


def judge_normalized_value_format(
    response: str,
    *,
    allowed_patterns: Optional[List[str]] = None,
    allowed_values: Optional[List[str]] = None,
    require_full_match: bool = True,
    ignore_case: bool = False,
    allow_multiple: bool = False,
    separator_pattern: str = r"(?:\n+|[;；])",
) -> EvaluationResult:
    function_name = "judge_normalized_value_format"
    text = _target_text(response)
    flags = re.IGNORECASE if ignore_case else 0
    items = _extract_validation_items(text, allow_multiple=allow_multiple, separator_pattern=separator_pattern)
    if not items:
        return _build_result(function_name, False, "The response is empty and cannot be validated for format.")

    normalized_values = None
    if allowed_values is not None:
        normalized_values = {value.lower() if ignore_case else value for value in allowed_values}
    compiled_patterns = [re.compile(pattern, flags=flags) for pattern in (allowed_patterns or [])]

    unmatched_items: List[str] = []
    matched_items: List[str] = []
    ignored_items: List[str] = []
    for item in items:
        normalized_item = item.lower() if ignore_case else item
        matched_value = normalized_values is not None and normalized_item in normalized_values
        matched_pattern = False
        for pattern in compiled_patterns:
            if require_full_match and pattern.fullmatch(item):
                matched_pattern = True
                break
            if not require_full_match and pattern.search(item):
                matched_pattern = True
                break
        if matched_value or matched_pattern:
            matched_items.append(item)
            continue
        if allow_multiple and not require_full_match:
            ignored_items.append(item)
            continue
        if not matched_value and not matched_pattern:
            unmatched_items.append(item)

    passed = not unmatched_items and bool(compiled_patterns or normalized_values) and bool(matched_items)
    return _build_result(
        function_name,
        passed,
        "All segments satisfy the normalized value format." if passed else "Some segments do not satisfy the normalized value format.",
        item_count=len(items),
        matched_items=matched_items,
        ignored_items=ignored_items,
        unmatched_items=unmatched_items,
        require_full_match=require_full_match,
    )


def judge_structured_json_output(
    response: str,
    *,
    top_level: str = "object",
    required_keys: Optional[List[str]] = None,
    forbidden_keys: Optional[List[str]] = None,
    schema: Optional[Any] = None,
) -> EvaluationResult:
    function_name = "judge_structured_json_output"
    parsed = _safe_json_loads(_target_text(response))
    if parsed is None:
        return _build_result(function_name, False, "The response is not valid JSON.")

    normalized_top_level = _ensure_text(top_level).lower()
    if normalized_top_level == "object" and not isinstance(parsed, dict):
        return _build_result(function_name, False, "The top-level JSON value is not an object.", actual_type=type(parsed).__name__)
    if normalized_top_level == "array" and not isinstance(parsed, list):
        return _build_result(function_name, False, "The top-level JSON value is not an array.", actual_type=type(parsed).__name__)

    missing_keys: List[str] = []
    if required_keys:
        if not isinstance(parsed, dict):
            return _build_result(function_name, False, "The top-level JSON value must be an object when required keys are specified.")
        missing_keys = [key for key in required_keys if key not in parsed]

    present_forbidden_keys: List[str] = []
    if forbidden_keys and isinstance(parsed, dict):
        present_forbidden_keys = [key for key in forbidden_keys if key in parsed]

    schema_skeleton = _load_schema_skeleton(schema)
    if schema is not None and schema_skeleton is None:
        return _build_result(function_name, False, "The provided schema skeleton is invalid; only JSON objects or arrays are supported.")

    schema_errors: List[str] = []
    if schema_skeleton is not None:
        schema_errors = _validate_structure_skeleton(parsed, schema_skeleton)

    passed = not missing_keys and not present_forbidden_keys and not schema_errors
    return _build_result(
        function_name,
        passed,
        "The JSON structure satisfies the requirements." if passed else "The JSON structure does not satisfy the key or structure requirements.",
        missing_keys=missing_keys,
        present_forbidden_keys=present_forbidden_keys,
        schema_errors=schema_errors,
        actual_type=type(parsed).__name__,
    )


def judge_table_output(
    response: str,
    *,
    allowed_formats: Optional[List[str]] = None,
    min_rows: int = 1,
    require_header: bool = True,
    schema: Optional[Any] = None,
) -> EvaluationResult:
    function_name = "judge_table_output"
    text = _target_text(response)
    formats = [item.lower() for item in (allowed_formats or ["markdown", "csv"]) if _ensure_text(item)]
    if not formats:
        formats = ["markdown", "csv"]

    candidates: List[Dict[str, Any]] = []
    if "markdown" in formats:
        markdown_payload = _parse_markdown_table_payload(text)
        if markdown_payload is not None:
            candidates.append(markdown_payload)
    if "csv" in formats:
        csv_payload = _parse_csv_table_payload(text, require_header=require_header)
        if csv_payload is not None:
            candidates.append(csv_payload)

    if not candidates:
        return _build_result(function_name, False, "No Markdown or CSV table satisfying the basic structural requirements was detected.")

    schema_skeleton = _load_schema_skeleton(schema)
    if schema is not None and schema_skeleton is None:
        return _build_result(function_name, False, "The provided table schema is invalid; only JSON objects or arrays are supported.")

    candidate_errors: List[Dict[str, Any]] = []
    for payload in candidates:
        row_count = int(payload.get("row_count") or 0)
        if row_count < min_rows:
            candidate_errors.append({
                "format": payload.get("format"),
                "errors": [f"$ : row_count {row_count} is smaller than min_rows={min_rows}."],
            })
            continue

        schema_errors: List[str] = []
        schema_target = "rows"
        if schema_skeleton is not None:
            if isinstance(schema_skeleton, dict):
                schema_target = "records"
                if not payload.get("records"):
                    schema_errors = ["$: named-field table schema requires a unique non-empty header row."]
                else:
                    schema_errors = _validate_structure_skeleton(payload.get("records"), [schema_skeleton])
            elif schema_skeleton and isinstance(schema_skeleton[0], dict):
                schema_target = "records"
                if not payload.get("records"):
                    schema_errors = ["$: record-structure table schema requires a unique non-empty header row."]
                else:
                    schema_errors = _validate_structure_skeleton(payload.get("records"), schema_skeleton)
            elif _is_scalar_sequence_schema(schema_skeleton):
                schema_target = "header"
                expected_header = [_ensure_text(item) for item in schema_skeleton]
                actual_header = [_ensure_text(item) for item in payload.get("header") or []]
                if not payload.get("has_header"):
                    schema_errors = ["$: header schema requires a detected header row."]
                elif len(actual_header) != len(expected_header):
                    schema_errors = [f"$: expected header length {len(expected_header)}, got {len(actual_header)}."]
                elif actual_header != expected_header:
                    schema_errors = [f"$: expected header {expected_header!r}, got {actual_header!r}."]
            else:
                schema_errors = _validate_structure_skeleton(payload.get("rows"), schema_skeleton)

        if not schema_errors:
            return _build_result(
                function_name,
                True,
                "The table structure satisfies the requirements.",
                detected_format=payload.get("format"),
                row_count=payload.get("row_count"),
                column_count=payload.get("column_count"),
                has_header=payload.get("has_header"),
                header=payload.get("header"),
                schema_target=schema_target,
            )

        candidate_errors.append({
            "format": payload.get("format"),
            "errors": schema_errors,
            "schema_target": schema_target,
        })

    return _build_result(
        function_name,
        False,
        "The detected table does not satisfy the requested row or field structure.",
        candidate_errors=candidate_errors,
    )


def judge_ordered_list_output(
    response: str,
    *,
    min_items: int = 1,
    allow_numbered: bool = True,
    allow_bullets: bool = True,
) -> EvaluationResult:
    function_name = "judge_ordered_list_output"
    lines = _non_empty_lines(_target_text(response))
    patterns: List[str] = []
    if allow_numbered:
        patterns.append(r"^\d+[\.)]\s+")
    if allow_bullets:
        patterns.append(r"^[-*•]\s+")
    if not patterns:
        return _build_result(function_name, False, "No list marker rule is enabled.")
    marker = re.compile("|".join(f"(?:{pattern})" for pattern in patterns))
    matched_count = sum(1 for line in lines if marker.search(line))
    passed = matched_count >= min_items
    return _build_result(
        function_name,
        passed,
        "The number of list items satisfies the requirement." if passed else "The number of list items is insufficient or does not match an allowed list format.",
        matched_item_count=matched_count,
        min_items=min_items,
    )


def judge_closed_set_option_output(
    response: str,
    *,
    allowed_options: List[str],
    allow_explanation: bool = False,
    ignore_case: bool = True,
) -> EvaluationResult:
    function_name = "judge_closed_set_option_output"
    text = _target_text(response)
    normalized_text = text.lower() if ignore_case else text
    normalized_options = [option.lower() if ignore_case else option for option in allowed_options]
    matched_option = None
    if allow_explanation:
        for option in normalized_options:
            if re.match(rf"^{re.escape(option)}(?:$|[\s\W])", normalized_text):
                matched_option = option
                break
    elif normalized_text in normalized_options:
        matched_option = normalized_text
    passed = matched_option is not None
    return _build_result(
        function_name,
        passed,
        "The response matches one of the allowed closed-set options." if passed else "The response does not match any allowed closed-set option.",
        matched_option=matched_option,
        allowed_options=allowed_options,
    )


def judge_response_length_constraint(
    response: str,
    *,
    min_count: int,
    max_count: int,
    unit: str = "word",
) -> EvaluationResult:
    function_name = "judge_response_length_constraint"
    text = _target_text(response)
    normalized_unit = _ensure_text(unit).lower()
    if normalized_unit in WORD_UNIT_ALIASES:
        actual = _count_words(text)
    elif normalized_unit in ZH_LENGTH_UNIT_ALIASES:
        actual = _count_zh_length(text)
    else:
        return _build_result(function_name, False, "Unsupported length unit.", unit=unit)
    passed = min_count <= actual <= max_count
    return _build_result(
        function_name,
        passed,
        "The response length falls within the required range." if passed else "The response length is outside the required range.",
        actual_count=actual,
        min_count=min_count,
        max_count=max_count,
        unit=unit,
    )


def judge_paragraph_count_constraint(
    response: str,
    *,
    min_count: int,
    max_count: int,
) -> EvaluationResult:
    function_name = "judge_paragraph_count_constraint"
    text = _target_text(response)
    paragraphs = [part for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]
    actual = len(paragraphs)
    passed = min_count <= actual <= max_count
    return _build_result(
        function_name,
        passed,
        "The paragraph count satisfies the requirement." if passed else "The paragraph count is outside the required range.",
        actual_count=actual,
        min_count=min_count,
        max_count=max_count,
    )


def judge_list_item_count_constraint(
    response: str,
    *,
    min_count: int,
    max_count: int,
) -> EvaluationResult:
    function_name = "judge_list_item_count_constraint"
    items = _parse_list_like_items(_target_text(response))
    actual = len(items)
    passed = min_count <= actual <= max_count
    return _build_result(
        function_name,
        passed,
        "The number of list items satisfies the requirement." if passed else "The number of list items is outside the required range.",
        actual_count=actual,
        min_count=min_count,
        max_count=max_count,
    )


def judge_required_keyword_inclusion(
    response: str,
    *,
    keywords: List[str],
    match_all: bool = True,
    min_occurrences: int = 1,
    max_occurrences: Optional[int] = None,
    ignore_case: bool = True,
) -> EvaluationResult:
    function_name = "judge_required_keyword_inclusion"
    text = _target_text(response)
    counts = {keyword: _contains_keyword(text, keyword, ignore_case=ignore_case) for keyword in keywords}
    hits = {
        keyword: count >= min_occurrences and (max_occurrences is None or count <= max_occurrences)
        for keyword, count in counts.items()
    }
    passed = all(hits.values()) if match_all else any(hits.values())
    return _build_result(
        function_name,
        passed,
        "The keyword hit requirement is satisfied." if passed else "Some required keywords do not meet the hit requirement.",
        keyword_counts=counts,
        min_occurrences=min_occurrences,
        max_occurrences=max_occurrences,
        match_all=match_all,
    )


def judge_forbidden_keyword_exclusion(
    response: str,
    *,
    keywords: List[str],
    ignore_case: bool = True,
) -> EvaluationResult:
    function_name = "judge_forbidden_keyword_exclusion"
    text = _target_text(response)
    counts = {keyword: _contains_keyword(text, keyword, ignore_case=ignore_case) for keyword in keywords}
    present_keywords = [keyword for keyword, count in counts.items() if count > 0]
    passed = not present_keywords
    return _build_result(
        function_name,
        passed,
        "No forbidden keywords were found." if passed else "Forbidden keywords were found in the response.",
        keyword_counts=counts,
        present_keywords=present_keywords,
    )


def judge_label_set_restriction(
    response: str,
    *,
    allowed_labels: List[str],
    ignore_case: bool = True,
    allow_duplicates: bool = True,
) -> EvaluationResult:
    function_name = "judge_label_set_restriction"
    items = _parse_list_like_items(_target_text(response))
    if not items:
        return _build_result(function_name, False, "No items could be parsed for label validation.")

    matched_labels_by_item: List[Dict[str, Any]] = []
    matched_labels_flat: List[str] = []
    out_of_set_items: List[str] = []
    for item in items:
        matched_labels = [label for label in allowed_labels if _contains_phrase(item, label, ignore_case=ignore_case)]
        matched_labels_by_item.append({"item": item, "matched_labels": matched_labels})
        if matched_labels:
            matched_labels_flat.extend(matched_labels)
        else:
            out_of_set_items.append(item)

    normalized_matched_labels = [label.lower() if ignore_case else label for label in matched_labels_flat]
    has_duplicate_conflict = not allow_duplicates and len(normalized_matched_labels) != len(set(normalized_matched_labels))
    passed = (not has_duplicate_conflict) and (not out_of_set_items)
    return _build_result(
        function_name,
        passed,
        "All detected label mentions stay within the allowed set." if passed else "There is a duplicate-label conflict or at least one parsed item lacks an allowed label mention.",
        parsed_items=items,
        matched_labels_by_item=matched_labels_by_item,
        out_of_set_items=out_of_set_items,
        allow_duplicates=allow_duplicates,
    )


def judge_verbatim_speech_constraint(
    response: str,
    *,
    expected_utterance: str,
    normalize_whitespace: bool = True,
    normalize_quotes: bool = True,
    ignore_case: bool = False,
    allow_wrapping_quotes: bool = True,
) -> EvaluationResult:
    function_name = "judge_verbatim_speech_constraint"
    candidate_segments = [
        _normalize_verbatim_segment(
            item,
            normalize_whitespace=normalize_whitespace,
            normalize_quotes=normalize_quotes,
            allow_wrapping_quotes=allow_wrapping_quotes,
        )
        for item in _extract_verbatim_segments(response)
    ]
    expected_segments = [
        _normalize_verbatim_segment(
            item,
            normalize_whitespace=normalize_whitespace,
            normalize_quotes=normalize_quotes,
            allow_wrapping_quotes=allow_wrapping_quotes,
        )
        for item in _extract_verbatim_segments(expected_utterance)
    ]
    candidate_segments = [item for item in candidate_segments if item]
    expected_segments = [item for item in expected_segments if item]
    passed = bool(expected_segments) and candidate_segments == expected_segments
    return _build_result(
        function_name,
        passed,
        "The response matches the normalized target utterance." if passed else "The response does not match the normalized target utterance.",
        normalized_candidate_segments=candidate_segments,
        normalized_expected_segments=expected_segments,
    )


def judge_span_localization(
    response: str,
    *,
    custom_patterns: Optional[List[str]] = None,
    min_spans: int = 1,
    max_spans: Optional[int] = None,
    expected_span_count: Optional[int] = None,
    ignore_case: bool = True,
) -> EvaluationResult:
    function_name = "judge_span_localization"
    text = _target_text(response)
    flags = re.IGNORECASE if ignore_case else 0
    patterns = custom_patterns or DEFAULT_SPAN_PATTERNS
    matches: List[str] = []
    parsed = _safe_json_loads(text)
    if parsed is not None:
        matches.extend(_extract_structured_span_matches(parsed))
    for pattern in patterns:
        matches.extend(match.group(0) for match in re.finditer(pattern, text, flags=flags))
    deduped_matches = list(dict.fromkeys(match.strip() for match in matches if match.strip()))
    actual = len(deduped_matches)

    passed = actual >= min_spans
    if max_spans is not None:
        passed = passed and actual <= max_spans
    if expected_span_count is not None:
        passed = passed and actual == expected_span_count

    return _build_result(
        function_name,
        passed,
        "Detected span-localization expressions that satisfy the requirement." if passed else "The number of span-localization expressions does not satisfy the requirement.",
        matched_spans=deduped_matches,
        actual_span_count=actual,
        min_spans=min_spans,
        max_spans=max_spans,
        expected_span_count=expected_span_count,
    )


FunctionParameterSpec = Dict[str, Any]
FunctionSpec = Dict[str, Any]


def _param_spec(
    name: str,
    type_name: str,
    meaning: str,
    *,
    required: bool = False,
    default: Any = None,
) -> FunctionParameterSpec:
    spec: FunctionParameterSpec = {
        "name": name,
        "type": type_name,
        "meaning": meaning,
    }
    if required:
        spec["required"] = True
    if default is not None:
        spec["default"] = default
    return spec


FUNCTION_SPEC_REGISTRY: Dict[str, FunctionSpec] = {
    "judge_normalized_value_format": {
        "function_name": "judge_normalized_value_format",
        "description": "Validate that the response matches a required normalized value format.",
        "primary_input_name": "response",
        "primary_input_meaning": "The extracted response span whose value format should be checked.",
        "parameters": [
            _param_spec("allowed_patterns", "Optional[List[str]]", "Regex patterns that define valid normalized formats."),
            _param_spec("allowed_values", "Optional[List[str]]", "A closed set of exact normalized values that are allowed."),
            _param_spec("require_full_match", "bool", "Whether each candidate item must fully match a valid pattern instead of only containing one.", default=True),
            _param_spec("ignore_case", "bool", "Whether exact-value and regex matching should ignore letter case.", default=False),
            _param_spec("allow_multiple", "bool", "Whether the response may contain multiple normalized items separated by delimiters.", default=False),
            _param_spec("separator_pattern", "str", "Regex used to split the response into multiple items when `allow_multiple` is enabled.", default=r"(?:\n+|[;；])"),
        ],
    },
    "judge_structured_json_output": {
        "function_name": "judge_structured_json_output",
        "description": "Validate that the response is valid JSON and optionally matches a field-and-structure skeleton.",
        "primary_input_name": "response",
        "primary_input_meaning": "The extracted response span expected to be JSON.",
        "parameters": [
            _param_spec("top_level", "str", "Required top-level JSON type, typically `object` or `array`.", default="object"),
            _param_spec("required_keys", "Optional[List[str]]", "Keys that must appear in the top-level JSON object."),
            _param_spec("forbidden_keys", "Optional[List[str]]", "Keys that must not appear in the top-level JSON object."),
            _param_spec("schema", "dict | list", "Optional structure skeleton. Objects define expected field names and nested structure; single-item arrays define the expected structure for every item in an array."),
        ],
    },
    "judge_table_output": {
        "function_name": "judge_table_output",
        "description": "Validate that the response is a valid Markdown or CSV-style table and optionally matches the expected row/field structure.",
        "primary_input_name": "response",
        "primary_input_meaning": "The extracted response span that should be formatted as a table.",
        "parameters": [
            _param_spec("allowed_formats", "Optional[List[str]]", "Allowed table formats, such as `markdown` and/or `csv`."),
            _param_spec("min_rows", "int", "Minimum number of data rows required in the detected table.", default=1),
            _param_spec("require_header", "bool", "Whether the detected table must contain an explicit header row.", default=True),
            _param_spec("schema", "dict | list", "Optional table structure skeleton. A dict means the expected field names for each row record; a list means the expected row or record-array structure."),
        ],
    },
    "judge_ordered_list_output": {
        "function_name": "judge_ordered_list_output",
        "description": "Validate that the response is organized as a numbered list or bullet list.",
        "primary_input_name": "response",
        "primary_input_meaning": "The extracted response span that should be formatted as a list.",
        "parameters": [
            _param_spec("min_items", "int", "Minimum number of list items that must be detected.", default=1),
            _param_spec("allow_numbered", "bool", "Whether numbered list items are allowed as a valid format.", default=True),
            _param_spec("allow_bullets", "bool", "Whether bulleted list items are allowed as a valid format.", default=True),
        ],
    },
    "judge_closed_set_option_output": {
        "function_name": "judge_closed_set_option_output",
        "description": "Validate that the response stays inside an allowed closed set of options.",
        "primary_input_name": "response",
        "primary_input_meaning": "The extracted response span whose option value should be checked.",
        "parameters": [
            _param_spec("allowed_options", "List[str]", "The closed-set options that are allowed as the answer.", required=True),
            _param_spec("allow_explanation", "bool", "Whether text following the chosen option is allowed.", default=False),
            _param_spec("ignore_case", "bool", "Whether option matching should ignore letter case.", default=True),
        ],
    },
    "judge_response_length_constraint": {
        "function_name": "judge_response_length_constraint",
        "description": "Validate that the response length falls within a required range.",
        "primary_input_name": "response",
        "primary_input_meaning": "The extracted response span whose length should be counted.",
        "parameters": [
            _param_spec("min_count", "int", "Inclusive lower bound for the required length.", required=True),
            _param_spec("max_count", "int", "Inclusive upper bound for the required length.", required=True),
            _param_spec("unit", "str", "The counting unit, such as `word` or `zh_length`.", default="word"),
        ],
    },
    "judge_paragraph_count_constraint": {
        "function_name": "judge_paragraph_count_constraint",
        "description": "Validate that the response contains a required number of paragraphs.",
        "primary_input_name": "response",
        "primary_input_meaning": "The extracted response span whose paragraphs should be counted.",
        "parameters": [
            _param_spec("min_count", "int", "Inclusive lower bound for the number of paragraphs.", required=True),
            _param_spec("max_count", "int", "Inclusive upper bound for the number of paragraphs.", required=True),
        ],
    },
    "judge_list_item_count_constraint": {
        "function_name": "judge_list_item_count_constraint",
        "description": "Validate that the response contains a required number of list items.",
        "primary_input_name": "response",
        "primary_input_meaning": "The extracted response span whose list items should be counted.",
        "parameters": [
            _param_spec("min_count", "int", "Inclusive lower bound for the number of list items.", required=True),
            _param_spec("max_count", "int", "Inclusive upper bound for the number of list items.", required=True),
        ],
    },
    "judge_required_keyword_inclusion": {
        "function_name": "judge_required_keyword_inclusion",
        "description": "Validate that required keywords appear in the response.",
        "primary_input_name": "response",
        "primary_input_meaning": "The extracted response span in which required keywords should be checked.",
        "parameters": [
            _param_spec("keywords", "List[str]", "Keywords or phrases that must be included.", required=True),
            _param_spec("match_all", "bool", "Whether all listed keywords must satisfy the requirement instead of any one of them.", default=True),
            _param_spec("min_occurrences", "int", "Minimum number of times each matched keyword must appear.", default=1),
            _param_spec("max_occurrences", "Optional[int]", "Maximum number of times each matched keyword may appear; combine with `min_occurrences` to express exact counts such as exactly once."),
            _param_spec("ignore_case", "bool", "Whether keyword matching should ignore letter case.", default=True),
        ],
    },
    "judge_forbidden_keyword_exclusion": {
        "function_name": "judge_forbidden_keyword_exclusion",
        "description": "Validate that forbidden keywords do not appear in the response.",
        "primary_input_name": "response",
        "primary_input_meaning": "The extracted response span in which forbidden keywords should be checked.",
        "parameters": [
            _param_spec("keywords", "List[str]", "Keywords or phrases that must be excluded.", required=True),
            _param_spec("ignore_case", "bool", "Whether forbidden-keyword matching should ignore letter case.", default=True),
        ],
    },
    "judge_label_set_restriction": {
        "function_name": "judge_label_set_restriction",
        "description": "Validate that parsed labels stay within an allowed label set.",
        "primary_input_name": "response",
        "primary_input_meaning": "The extracted response span from which label-like items should be parsed.",
        "parameters": [
            _param_spec("allowed_labels", "List[str]", "Labels that are allowed to appear after parsing the response.", required=True),
            _param_spec("ignore_case", "bool", "Whether label comparison should ignore letter case.", default=True),
            _param_spec("allow_duplicates", "bool", "Whether duplicate labels are allowed.", default=True),
        ],
    },
    "judge_verbatim_speech_constraint": {
        "function_name": "judge_verbatim_speech_constraint",
        "description": "Validate that the response matches a target utterance verbatim.",
        "primary_input_name": "response",
        "primary_input_meaning": "The extracted response span that should exactly match the expected utterance.",
        "parameters": [
            _param_spec("expected_utterance", "str", "The exact utterance the extracted response is expected to match.", required=True),
            _param_spec("normalize_whitespace", "bool", "Whether repeated whitespace should be normalized before comparison.", default=True),
            _param_spec("normalize_quotes", "bool", "Whether visually different quote characters should be normalized before comparison.", default=True),
            _param_spec("ignore_case", "bool", "Whether the comparison should ignore letter case.", default=False),
            _param_spec("allow_wrapping_quotes", "bool", "Whether matching should ignore a pair of wrapping quotation marks around the full utterance.", default=True),
        ],
    },
    "judge_span_localization": {
        "function_name": "judge_span_localization",
        "description": "Validate that the response contains the required number of explicit span-localization expressions.",
        "primary_input_name": "response",
        "primary_input_meaning": "The extracted response span in which localized time spans should be detected.",
        "parameters": [
            _param_spec("custom_patterns", "Optional[List[str]]", "Optional regex patterns used to detect valid span-localization expressions."),
            _param_spec("min_spans", "int", "Minimum number of valid span expressions that must be detected.", default=1),
            _param_spec("max_spans", "Optional[int]", "Optional maximum number of valid span expressions allowed."),
            _param_spec("expected_span_count", "Optional[int]", "Optional exact number of span expressions required."),
            _param_spec("ignore_case", "bool", "Whether span regex matching should ignore letter case.", default=True),
        ],
    },
}

CONSTRAINT_FUNCTION_SPECS: Dict[str, List[FunctionSpec]] = {
    "normalized_value_format": [FUNCTION_SPEC_REGISTRY["judge_normalized_value_format"]],
    "structured_json_output": [FUNCTION_SPEC_REGISTRY["judge_structured_json_output"]],
    "table_output": [FUNCTION_SPEC_REGISTRY["judge_table_output"]],
    "ordered_list_output": [FUNCTION_SPEC_REGISTRY["judge_ordered_list_output"]],
    "closed_set_option_output": [FUNCTION_SPEC_REGISTRY["judge_closed_set_option_output"]],
    "response_length_constraint": [FUNCTION_SPEC_REGISTRY["judge_response_length_constraint"]],
    "paragraph_count_constraint": [FUNCTION_SPEC_REGISTRY["judge_paragraph_count_constraint"]],
    "list_item_count_constraint": [FUNCTION_SPEC_REGISTRY["judge_list_item_count_constraint"]],
    "required_keyword_inclusion": [FUNCTION_SPEC_REGISTRY["judge_required_keyword_inclusion"]],
    "forbidden_keyword_exclusion": [FUNCTION_SPEC_REGISTRY["judge_forbidden_keyword_exclusion"]],
    "verbatim_speech_constraint": [FUNCTION_SPEC_REGISTRY["judge_verbatim_speech_constraint"]],
}


FUNCTION_REGISTRY: Dict[str, Callable[..., EvaluationResult]] = {
    "judge_normalized_value_format": judge_normalized_value_format,
    "judge_structured_json_output": judge_structured_json_output,
    "judge_table_output": judge_table_output,
    "judge_ordered_list_output": judge_ordered_list_output,
    "judge_closed_set_option_output": judge_closed_set_option_output,
    "judge_response_length_constraint": judge_response_length_constraint,
    "judge_paragraph_count_constraint": judge_paragraph_count_constraint,
    "judge_list_item_count_constraint": judge_list_item_count_constraint,
    "judge_required_keyword_inclusion": judge_required_keyword_inclusion,
    "judge_forbidden_keyword_exclusion": judge_forbidden_keyword_exclusion,
    "judge_label_set_restriction": judge_label_set_restriction,
    "judge_verbatim_speech_constraint": judge_verbatim_speech_constraint,
    "judge_span_localization": judge_span_localization,
}


__all__ = [
    "FUNCTION_REGISTRY",
    "FUNCTION_SPEC_REGISTRY",
    "CONSTRAINT_FUNCTION_SPECS",
    "judge_normalized_value_format",
    "judge_structured_json_output",
    "judge_table_output",
    "judge_ordered_list_output",
    "judge_closed_set_option_output",
    "judge_response_length_constraint",
    "judge_paragraph_count_constraint",
    "judge_list_item_count_constraint",
    "judge_required_keyword_inclusion",
    "judge_forbidden_keyword_exclusion",
    "judge_label_set_restriction",
    "judge_verbatim_speech_constraint",
    "judge_span_localization",
]
