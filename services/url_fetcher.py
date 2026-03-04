"""Fetches and extracts readable text content from URLs."""

from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Slack wraps URLs like <https://example.com> or <https://example.com|display text>
SLACK_URL_PATTERN = re.compile(r"<(https?://[^|>]+)(?:\|[^>]*)?>")
PLAIN_URL_PATTERN = re.compile(r"(https?://\S+)")


def extract_urls(text: str) -> list[str]:
    """Extract URLs from a Slack message (handles Slack's URL formatting)."""
    urls = SLACK_URL_PATTERN.findall(text)
    if not urls:
        urls = PLAIN_URL_PATTERN.findall(text)
    return urls


def strip_urls(text: str) -> str:
    """Remove URLs from text, leaving any surrounding commentary."""
    cleaned = SLACK_URL_PATTERN.sub("", text)
    cleaned = PLAIN_URL_PATTERN.sub("", cleaned)
    return cleaned.strip()


def fetch_page_content(url: str, max_chars: int = 5000) -> str | None:
    """Fetch a URL and return its main text content."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; LinkedInPostBot/1.0)"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script, style, nav, footer elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Try to get article or main content first
        main = soup.find("article") or soup.find("main") or soup.find("body")
        if not main:
            return None

        text = main.get_text(separator="\n", strip=True)

        # Collapse excessive whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)

        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        return text
    except Exception:
        logger.exception("Failed to fetch URL: %s", url)
        return None


def fetch_all_urls(urls: list[str]) -> str:
    """Fetch content from multiple URLs and combine them."""
    contents = []
    for url in urls:
        content = fetch_page_content(url)
        if content:
            contents.append(f"[Content from {url}]\n{content}")
    return "\n\n---\n\n".join(contents)
