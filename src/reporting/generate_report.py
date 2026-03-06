"""
Generate the underwriting report using the LLM from pipeline outputs.
Save report_context.json, underwriting_report.md, llm_prompt.txt, llm_response.txt.
"""
import logging
from pathlib import Path

from src.config import (
    LLM_PROMPT_TXT,
    LLM_RESPONSE_TXT,
    REPORT_CONTEXT_JSON,
    UNDERWRITING_REPORT_MD,
)
from src.reporting.build_report_context import build_report_context
from src.reporting.llm_client import call_llm
from src.reporting.prompts import REPORT_SECTIONS, SYSTEM_PROMPT, get_report_prompt
from src.utils.io_utils import save_json, ensure_dir

logger = logging.getLogger(__name__)


def generate_report(
    report_context: dict | None = None,
    model_metrics: dict | None = None,
    output_md_path: Path = UNDERWRITING_REPORT_MD,
    context_path: Path = REPORT_CONTEXT_JSON,
    prompt_path: Path = LLM_PROMPT_TXT,
    response_path: Path = LLM_RESPONSE_TXT,
) -> str:
    """
    Build context, call LLM, save all artifacts. Return the report text.
    """
    if report_context is None:
        report_context = build_report_context(model_metrics=model_metrics)
    if model_metrics:
        report_context["model_metrics"] = model_metrics

    import json
    context_str = json.dumps(report_context, indent=2)
    user_prompt = get_report_prompt(context_str)

    ensure_dir(context_path)
    save_json(report_context, context_path)
    ensure_dir(prompt_path)
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(user_prompt)

    response = call_llm(user_prompt, SYSTEM_PROMPT)

    with open(response_path, "w", encoding="utf-8") as f:
        f.write(response)
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(response)
    logger.info("Report saved: %s", output_md_path)
    return response
