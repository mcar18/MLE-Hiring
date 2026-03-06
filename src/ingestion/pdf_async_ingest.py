"""
PDF ingestion: extract text from sample_merchant_summary.pdf asynchronously.
In production this would be a proper job queue (e.g. Celery, SQS); we use asyncio with a comment.
"""
import asyncio
import logging
from pathlib import Path
from typing import Any

import pdfplumber

from src.config import SAMPLE_PDF

logger = logging.getLogger(__name__)


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
        return {"source": str(pdf_path), "text": full_text, "page_count": len(text_parts)}

    result = await loop.run_in_executor(None, _extract)
    logger.info("PDF extracted: %s (%d chars)", pdf_path, len(result.get("text", "")))
    return result
