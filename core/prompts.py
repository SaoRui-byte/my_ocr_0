"""任务 prompt 模板，与官方 skills/xiaomi-ocr/mcp_ocr_server.py 保持一致。"""
import json

DOC_PROMPT = (
    "Extract all information from the main body of the document image and represent it in markdown format, "
    "ignoring headers and footers. Tables should be expressed in OTSL format, formulas in the document should "
    "be represented using LATEX format, and the parsing should be organized according to the reading order."
)

KIE_PROMPT_NO_FIELDS = (
    "Extract the key information from the document image as a JSON object. "
    "Use concise field names. Return JSON only; use an empty string for missing values."
)

VQA_SUFFIX = "\nAnswer the question using a single word or phrase."


def parse_prompt() -> str:
    return DOC_PROMPT


def kie_prompt(fields: list[str] | None) -> str:
    if not fields:
        return KIE_PROMPT_NO_FIELDS
    schema = {str(field): "" for field in fields}
    return (
        "Extract key information in the image\n\n"
        "Please output the key information in JSON format according to the following schema:\n"
        + json.dumps(schema, ensure_ascii=False, indent=4)
    )


def vqa_prompt(question: str) -> str:
    return question.strip() + VQA_SUFFIX
