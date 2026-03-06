"""
PDF ingestion: extract text from sample_merchant_summary.pdf asynchronously.
Clean whitespace, remove short fragments, build a short pdf_summary for the report.
Production would use a job queue; we use asyncio with a comment.
"""
import asyncio
import logging
import re
from pathlib import Path
from typing import Any

import pdfplumber

from src.config import PDF_SUMMARY_JSON, PDF_TEXT_JSON, SAMPLE_PDF

logger = logging.getLogger(__name__)


def _clean_extracted_text(text: str) -> str:
    """Normalize whitespace, remove very short lines (fragments/noise)."""
    if not text or not text.strip():
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # Drop extremely short fragments (likely artifacts; keep meaningful sentences)
    min_len = 20
    lines = [l for l in lines if len(l) >= min_len]
    return "\n".join(lines)


def _extract_summary_from_cleaned(cleaned_text: str, max_chars: int = 500) -> str:
    """Build a short summary from the most informative paragraphs (longer = more content)."""
    if not cleaned_text:
        return "(No content extracted)"
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", cleaned_text) if p.strip()]
    # Prefer longer paragraphs as more substantive
    paragraphs.sort(key=len, reverse=True)
    summary_parts = []
    total = 0
    for p in paragraphs:
        if total + len(p) <= max_chars:
            summary_parts.append(p)
            total += len(p)
        else:
            break
    return " ".join(summary_parts) if summary_parts else cleaned_text[:max_chars]


async def extract_pdf_text_async(pdf_path: Path = SAMPLE_PDF) -> dict[str, Any]:
    """
    Extract text from PDF in an async-friendly way.
    Production systems would enqueue the PDF to a job queue and process in a worker;
    we run the CPU-bound extraction in a thread pool to avoid blocking the event loop.
    """
    loop = asyncio.get_event_loop()

    def _extract() -> dict[str, Any]:
        text_parts: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        full_text = "\n".join(text_parts) if text_parts else ""
        cleaned = _clean_extracted_text(full_text)
        summary = _extract_summary_from_cleaned(cleaned)
        return {
            "source": str(pdf_path),
            "text": full_text,
            "cleaned_text": cleaned,
            "pdf_summary": summary,
            "page_count": len(text_parts),
        }

    result = await loop.run_in_executor(None, _extract)
    logger.info("PDF extracted: %s (%d chars, summary %d chars)", pdf_path, len(result.get("text", "")), len(result.get("pdf_summary", "")))
    return result


def save_pdf_summary(extract_result: dict[str, Any], summary_path: Path = PDF_SUMMARY_JSON) -> Path:
    """Write pdf_summary and key metadata to pdf_summary.json for the report."""
    from src.utils.io_utils import ensure_dir, save_json
    out = {
        "source": extract_result.get("source"),
        "pdf_summary": extract_result.get("pdf_summary", ""),
        "page_count": extract_result.get("page_count", 0),
    }
    ensure_dir(summary_path)
    save_json(out, summary_path)
    return summary_path
