from video_ifbench.metrics import summarize_cases


def test_tcsr_is_task_gated_constraint_accuracy():
    cases = {
        "a": {
            "status": "ok",
            "instruction_type": "single",
            "constraint_summary": {"passed": 1, "total": 2, "accuracy": 0.5},
            "task_summary": {"passed": 1, "total": 1},
            "instruction_result": {"constraint_all_passed": False, "task_all_passed": True},
            "constraint_results": [{"constraint_id": "x", "passed": True}, {"constraint_id": "y", "passed": False}],
            "task_results": [{"passed": True}],
        },
        "b": {
            "status": "ok",
            "instruction_type": "single",
            "constraint_summary": {"passed": 2, "total": 2, "accuracy": 1.0},
            "task_summary": {"passed": 0, "total": 1},
            "instruction_result": {"constraint_all_passed": True, "task_all_passed": False},
            "constraint_results": [{"constraint_id": "x", "passed": True}, {"constraint_id": "y", "passed": True}],
            "task_results": [{"passed": False}],
        },
    }
    summary = summarize_cases(cases)
    assert summary["tcsr"]["accuracy"] == 0.25
    assert summary["tisr"]["accuracy"] == 0.0
