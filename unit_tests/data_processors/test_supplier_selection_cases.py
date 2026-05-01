from __future__ import annotations

from finrl.meta.data_processors.supplier_selection_cases import (
    DEFAULT_CASE_OUTPUT_PATH,
    OBJECTIVE_PROFILES,
    REQUIRED_CASE_FIELDS,
    REQUIRED_SUPPLIER_FIELDS,
    assign_case_split,
    generate_and_write_supplier_selection_cases,
    generate_supplier_selection_cases,
    write_supplier_selection_cases_jsonl,
)


def test_supplier_selection_cases_are_deterministic_for_fixed_seed():
    first = generate_supplier_selection_cases(case_count=5, seed=17)
    second = generate_supplier_selection_cases(case_count=5, seed=17)

    assert first == second


def test_supplier_selection_case_schema_and_supplier_fields():
    case = generate_supplier_selection_cases(case_count=1, seed=23)[0]

    assert REQUIRED_CASE_FIELDS.issubset(case)
    assert case["case_id"] == "supplier_case_000001"
    assert case["case_type"] == "supplier_selection"
    assert case["seed"] == 23
    assert case["buyer_objective"]
    assert case["metadata"]["objective_profile"] in {
        profile["profile_id"] for profile in OBJECTIVE_PROFILES
    }
    assert "service_level_target" in case["demand_context"]
    assert case["metadata"]["generator_version"] == "v1"
    assert case["metadata"]["split"] == assign_case_split(case["case_id"])
    assert case["rubric"]["aggregation"] == "equal_weight_mean"

    assert len(case["supplier_options"]) >= 3
    for supplier in case["supplier_options"]:
        assert REQUIRED_SUPPLIER_FIELDS.issubset(supplier)
        assert supplier["supplier_id"].startswith("SUP_")
        assert supplier["base_price"] > 0.0
        assert 0.0 <= supplier["reliability"] <= 1.0
        assert supplier["lead_time_days"] >= 1
        assert supplier["capacity"] > 0.0
        assert 0.0 <= supplier["disruption_probability"] <= 1.0


def test_generate_one_hundred_valid_supplier_selection_cases():
    cases = generate_supplier_selection_cases(case_count=100, seed=31)

    assert len(cases) == 100
    assert len({case["case_id"] for case in cases}) == 100
    assert all(case["case_type"] == "supplier_selection" for case in cases)
    assert all(REQUIRED_CASE_FIELDS.issubset(case) for case in cases)


def test_one_hundred_cases_cover_multiple_objective_profiles():
    cases = generate_supplier_selection_cases(case_count=100, seed=31)

    objective_profiles = {case["metadata"]["objective_profile"] for case in cases}
    buyer_objectives = {case["buyer_objective"] for case in cases}

    assert objective_profiles == {profile["profile_id"] for profile in OBJECTIVE_PROFILES}
    assert len(buyer_objectives) == len(OBJECTIVE_PROFILES)


def test_split_assignment_is_deterministic_by_case_id_only():
    case_id = "supplier_case_000042"

    assert assign_case_split(case_id) == assign_case_split(case_id)
    assert generate_supplier_selection_cases(case_count=42, seed=1)[-1]["metadata"][
        "split"
    ] == generate_supplier_selection_cases(case_count=42, seed=999)[-1]["metadata"][
        "split"
    ]


def test_objective_profile_assignment_is_deterministic_by_case_number_only():
    seed_one_cases = generate_supplier_selection_cases(case_count=12, seed=1)
    seed_two_cases = generate_supplier_selection_cases(case_count=12, seed=999)

    assert [
        case["metadata"]["objective_profile"] for case in seed_one_cases
    ] == [
        case["metadata"]["objective_profile"] for case in seed_two_cases
    ]


def test_supplier_selection_cases_can_be_written_as_jsonl(tmp_path):
    cases = generate_supplier_selection_cases(case_count=3, seed=43)
    output_path = tmp_path / "cases" / "supplier_selection_cases.jsonl"

    written_path = write_supplier_selection_cases_jsonl(cases, output_path)

    assert written_path == output_path
    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert '"case_id": "supplier_case_000001"' in lines[0]


def test_generate_and_write_supplier_selection_cases_uses_output_layout(tmp_path):
    output_path = tmp_path / DEFAULT_CASE_OUTPUT_PATH.name

    written_path = generate_and_write_supplier_selection_cases(
        case_count=4,
        seed=47,
        output_path=output_path,
    )

    assert written_path == output_path
    assert len(output_path.read_text(encoding="utf-8").splitlines()) == 4
    assert str(DEFAULT_CASE_OUTPUT_PATH).replace("\\", "/").endswith(
        "examples/supply_chain/supplier_selection_llm/outputs/cases/supplier_selection_cases.jsonl"
    )
