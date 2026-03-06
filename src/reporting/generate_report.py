"""
Generate the underwriting report using the LLM from pipeline outputs.
Save report_context.json, underwriting_report.md, llm_prompt.txt, llm_response.txt.
Accepts model_comparison, feature_importance, and builds context with underwriting recommendation.
Embeds plot images (ROC, PR, confusion matrix, calibration, feature importance, risk distribution) into the report.
"""
import logging
from pathlib import Path

from src.config import (
    LLM_PROMPT_TXT,
    LLM_RESPONSE_TXT,
    PLOTS_DIR,
    REPORT_CONTEXT_JSON,
    UNDERWRITING_REPORT_MD,
)
from src.reporting.build_report_context import build_report_context
from src.reporting.llm_client import call_llm
from src.reporting.prompts import REPORT_SECTIONS, SYSTEM_PROMPT, get_report_prompt
from src.utils.io_utils import ensure_dir, save_json

logger = logging.getLogger(__name__)

# Relative path from report (artifacts/underwriting_report.md) to plots (artifacts/plots/)
PLOTS_RELATIVE = "plots"
PLOT_FILES = [
    ("roc_curve.png", "ROC Curve"),
    ("pr_curve.png", "Precision-Recall Curve"),
    ("confusion_matrix.png", "Confusion Matrix"),
    ("calibration_curve.png", "Calibration Curve"),
    ("feature_importance.png", "Feature Importance"),
    ("risk_distribution.png", "Risk Score Distribution"),
]


def _append_visuals_section(report_text: str, plots_dir: Path) -> str:
    """Append an Appendix with embedded plot images; only include plots that exist."""
    lines = [
        "",
        "---",
        "",
        "## Appendix: Model Visuals",
        "",
        "The following plots are generated from out-of-fold predictions and the chosen model.",
        "",
    ]
    for filename, title in PLOT_FILES:
        path = plots_dir / filename
        if path.exists():
            rel = f"{PLOTS_RELATIVE}/{filename}"
            lines.append(f"### {title}")
            lines.append("")
            lines.append(f"![{title}]({rel})")
            lines.append("")
    return report_text.rstrip() + "\n" + "\n".join(lines)


def generate_report(
    report_context: dict | None = None,
    model_metrics: dict | None = None,
    model_comparison: dict | None = None,
    feature_importance: list | None = None,
    output_md_path: Path = UNDERWRITING_REPORT_MD,
    context_path: Path = REPORT_CONTEXT_JSON,
    prompt_path: Path = LLM_PROMPT_TXT,
    response_path: Path = LLM_RESPONSE_TXT,
) -> str:
    """
    Build context (with model_comparison, feature_importance, underwriting recommendation), call LLM, save artifacts.
    """
    if report_context is None:
        report_context = build_report_context(
            model_metrics=model_metrics,
            feature_importance=feature_importance,
        )
    if model_metrics:
        report_context["model_metrics"] = model_metrics
    if model_comparison:
        report_context["model_comparison"] = model_comparison
    if feature_importance is not None:
        report_context["feature_importance_ranking"] = feature_importance

    import json
    context_str = json.dumps(report_context, indent=2)
    user_prompt = get_report_prompt(context_str)

    ensure_dir(context_path)
    save_json(report_context, context_path)
    ensure_dir(prompt_path)
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(user_prompt)

    response = call_llm(user_prompt, SYSTEM_PROMPT)

    ensure_dir(response_path)
    with open(response_path, "w", encoding="utf-8") as f:
        f.write(response)
    ensure_dir(output_md_path)
    report_with_visuals = _append_visuals_section(response, PLOTS_DIR)
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(report_with_visuals)
    logger.info("Report saved: %s", output_md_path)
    return report_with_visuals
