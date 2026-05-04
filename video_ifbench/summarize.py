from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional


def pct(value: Optional[float]) -> str:
    return "--" if value is None else f"{100 * value:.1f}"


def row_for(summary: Dict[str, Any], name: str) -> Dict[str, Any]:
    if name == "overall":
        return {"tcsr": summary.get("tcsr", {}).get("accuracy"), "tisr": summary.get("tisr", {}).get("accuracy")}
    if name == "multi":
        return summary.get("multi") or {}
    return (summary.get("by_instruction_type") or {}).get(name) or {}


def latex_row(model_name: str, summary: Dict[str, Any]) -> str:
    cells = []
    for key in ("single", "multi", "selection", "nested", "overall"):
        row = row_for(summary, key)
        cells.extend([pct(row.get("tcsr")), pct(row.get("tisr"))])
    return model_name + " & " + " & ".join(cells) + r" \\"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize a Video-IFBench score report.")
    parser.add_argument("--report", required=True)
    parser.add_argument("--model-name", default="Model")
    parser.add_argument("--format", choices=["json", "latex", "csv"], default="latex")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    summary = report.get("summary") or {}
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.format == "csv":
        header = ["Model", "Single TCSR", "Single TISR", "Multi TCSR", "Multi TISR", "Selection TCSR", "Selection TISR", "Nested TCSR", "Nested TISR", "Overall TCSR", "Overall TISR"]
        values = [args.model_name]
        for key in ("single", "multi", "selection", "nested", "overall"):
            row = row_for(summary, key)
            values.extend([pct(row.get("tcsr")), pct(row.get("tisr"))])
        print(",".join(header))
        print(",".join(values))
    else:
        print(latex_row(args.model_name, summary))


if __name__ == "__main__":
    main()
