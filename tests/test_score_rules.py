from video_ifbench.function_judges import FUNCTION_REGISTRY
from video_ifbench.score import build_rule_constraint_spec_map, function_spec_name, sanitize_rule_parameters


def test_rule_function_specs_resolve_registry_names():
    spec_map = build_rule_constraint_spec_map()

    for constraint_id in [
        "paragraph_count_constraint",
        "required_keyword_inclusion",
        "structured_json_output",
        "forbidden_keyword_exclusion",
        "ordered_list_output",
    ]:
        names = [function_spec_name(spec) for spec in spec_map[constraint_id]]
        assert names
        assert all(name in FUNCTION_REGISTRY for name in names)


def test_rule_parameter_sanitizer_keeps_list_values_as_lists():
    spec = build_rule_constraint_spec_map()["required_keyword_inclusion"][0]

    params = sanitize_rule_parameters(spec, {"keywords": ["overtakes"], "match_all": "true"})

    assert params["keywords"] == ["overtakes"]
    assert params["match_all"] is True
