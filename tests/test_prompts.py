from core.prompts import parse_prompt, kie_prompt, vqa_prompt


def test_parse_prompt_matches_official_contract():
    p = parse_prompt()
    assert "markdown" in p
    assert "OTSL" in p
    assert "LATEX" in p


def test_kie_prompt_lists_fields_as_json_schema():
    p = kie_prompt(["金额", "日期"])
    assert "金额" in p and "日期" in p
    assert "JSON" in p


def test_kie_prompt_without_fields():
    p = kie_prompt(None)
    assert "JSON" in p
    assert "empty string for missing values" in p


def test_vqa_prompt_contains_question_and_concise_constraint():
    p = vqa_prompt("哪个季度营收最高？")
    assert "哪个季度营收最高？" in p
    assert "single word or phrase" in p
