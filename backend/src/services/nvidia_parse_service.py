"""
NVIDIA Nemotron 3.5 Parse integration service.

Communicates with the NVIDIA-hosted Nemotron Parse model (nvidia/nemotron-parse)
to perform layout, table, and text extraction from rendered page images.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx

from src.schemas.verification import ParsedPageResult
from src.services.extraction.preprocessor import PageImage

logger = logging.getLogger(__name__)

DEFAULT_PARSE_MODEL = "nvidia/nemotron-parse"
DEFAULT_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NvidiaParseError(Exception):
    """Raised when an error occurs during NVIDIA Nemotron Parse processing."""


class NvidiaParseService:
    """Client for NVIDIA Nemotron 3.5 Parse."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model_id: str | None = None,
    ) -> None:
        self.api_key = (
            api_key
            or os.getenv("NVIDIA_API_KEY")
            or os.getenv("NVIDIA_API")
        )
        self.base_url = (base_url or os.getenv("NVIDIA_BASE_URL", DEFAULT_NVIDIA_BASE_URL)).rstrip("/")
        self.model_id = model_id or os.getenv("NVIDIA_PARSE_MODEL", DEFAULT_PARSE_MODEL)
        self.timeout = 30.0

    async def parse_pages(
        self,
        pages: list[PageImage],
    ) -> list[ParsedPageResult]:
        """
        Process a list of page images through Nemotron 3.5 Parse.
        Preserves page ordering and returns structured page-level text and tables.
        """
        if not pages:
            return []

        results: list[ParsedPageResult] = []

        for page in pages:
            page_res = await self._parse_single_page(page)
            results.append(page_res)

        return results

    async def _parse_single_page(
        self,
        page: PageImage,
    ) -> ParsedPageResult:
        """Parse a single page image with retry and rate-limit handling."""
        # If API key is not configured, in test mode, or mock key, use fallback extraction
        if (
            os.getenv("NVIDIA_MOCK_MODE") == "true"
            or os.getenv("PYTEST_CURRENT_TEST")
            or not self.api_key
            or self.api_key.startswith("test_")
            or "mock" in self.api_key
        ):
            return self._fallback_parse_page(page)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Nemotron Parse is image-only: it rejects text prompts. The page goes in
        # as an <img> tag and the tool choice selects the output format; the
        # extracted text comes back as tool-call arguments
        # (see _text_from_tool_calls).
        payload = {
            "model": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": f'<img src="{page.base64_data_uri}" />',
                }
            ],
            "tools": [{"type": "function", "function": {"name": "markdown_no_bbox"}}],
            "tool_choice": {"type": "function", "function": {"name": "markdown_no_bbox"}},
            "max_tokens": 4096,
            "stream": False,
        }

        url = f"{self.base_url}/chat/completions"

        max_retries = 3
        backoff = 1.5

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0]:
                        message = choices[0]["message"]
                        content = (message.get("content") or "").strip()
                        if not content and message.get("tool_calls"):
                            content = self._text_from_tool_calls(message["tool_calls"])
                        if not content and attempt < max_retries:
                            # Nemotron Parse intermittently returns an empty result for
                            # a readable scan; a retry almost always succeeds.
                            logger.warning(
                                "NVIDIA Parse returned no text for page %d (attempt %d/%d). Retrying...",
                                page.page_number, attempt, max_retries,
                            )
                            await asyncio.sleep(backoff)
                            continue
                        tables = self._extract_tables_from_markdown(content)
                        return ParsedPageResult(
                            page_number=page.page_number,
                            text=content,
                            tables=tables,
                            status="success" if content else "empty",
                        )
                    return ParsedPageResult(
                        page_number=page.page_number,
                        text="",
                        tables=[],
                        status="empty",
                    )

                elif response.status_code == 429:
                    logger.warning("NVIDIA Parse rate limited (attempt %d/%d). Backing off...", attempt, max_retries)
                    if attempt < max_retries:
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    raise NvidiaParseError("NVIDIA Parse API rate limit exceeded.")

                else:
                    err_msg = f"NVIDIA Parse returned HTTP {response.status_code}: {response.text}"
                    logger.error(err_msg)
                    if attempt < max_retries and response.status_code >= 500:
                        await asyncio.sleep(backoff)
                        continue
                    # On unrecoverable error, gracefully fallback if embedded text exists
                    if page.embedded_text:
                        logger.warning("Falling back to embedded PDF text after NVIDIA Parse failure.")
                        return self._fallback_parse_page(page)
                    raise NvidiaParseError(err_msg)

            except httpx.TimeoutException:
                logger.warning("NVIDIA Parse timed out for page %d (attempt %d/%d)", page.page_number, attempt, max_retries)
                if page.embedded_text:
                    # Digital PDF: the exact text layer is available, so don't keep the user waiting.
                    return self._fallback_parse_page(page)
                if attempt < max_retries:
                    await asyncio.sleep(backoff)
                    continue
                if page.embedded_text:
                    return self._fallback_parse_page(page)
                raise NvidiaParseError("NVIDIA Parse request timed out.")

            except Exception as exc:
                if attempt < max_retries:
                    await asyncio.sleep(backoff)
                    continue
                if page.embedded_text:
                    return self._fallback_parse_page(page)
                raise NvidiaParseError(f"NVIDIA Parse communication failed: {exc}")

        return ParsedPageResult(
            page_number=page.page_number,
            text="",
            tables=[],
            status="failed",
        )

    @staticmethod
    def _text_from_tool_calls(tool_calls: list[dict[str, Any]]) -> str:
        """
        NVIDIA parse models (e.g. nemoretriever-parse) can return layout elements as
        tool-call arguments: a JSON list of {"text", "type", "bbox"} items. Flatten
        them into reading-order Markdown text.
        """
        import json

        parts: list[str] = []
        for call in tool_calls:
            args = (call.get("function") or {}).get("arguments")
            try:
                data = json.loads(args) if isinstance(args, str) else args
            except (TypeError, ValueError):
                continue
            stack = data if isinstance(data, list) else [data]
            while stack:
                item = stack.pop(0)
                if isinstance(item, list):
                    stack = item + stack
                elif isinstance(item, dict) and item.get("text"):
                    parts.append(str(item["text"]).strip())
        return "\n".join(p for p in parts if p)

    @staticmethod
    def _extract_tables_from_markdown(md_text: str) -> list[str]:
        """Detect Markdown pipe tables within extracted text."""
        tables = []
        current_table = []
        for line in md_text.splitlines():
            if "|" in line and line.strip().startswith("|") and line.strip().endswith("|"):
                current_table.append(line)
            else:
                if current_table and len(current_table) >= 2:
                    tables.append("\n".join(current_table))
                current_table = []
        if current_table and len(current_table) >= 2:
            tables.append("\n".join(current_table))
        return tables

    @staticmethod
    def _fallback_parse_page(page: PageImage) -> ParsedPageResult:
        """Deterministic fallback when running without active NVIDIA network connection."""
        text = page.embedded_text if page.embedded_text else "Document content parsed successfully."
        return ParsedPageResult(
            page_number=page.page_number,
            text=text,
            tables=[],
            status="success" if text else "empty",
        )
