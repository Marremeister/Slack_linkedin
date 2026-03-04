from __future__ import annotations

import json
import logging
import time
from typing import Optional

from google import genai
from google.genai import types

import config
from prompts.category_prompts import (
    build_suggest_angles_prompt,
    build_suggest_image_styles_prompt,
)
from prompts.draft_prompts import build_draft_prompt, build_edit_draft_prompt
from prompts.image_prompts import build_image_prompt, build_edit_image_prompt

logger = logging.getLogger(__name__)

client = genai.Client(api_key=config.GEMINI_API_KEY)

TEXT_MODEL = "gemini-2.5-flash"
IMAGE_MODEL = "gemini-2.5-flash-image"


def _parse_json(text: str) -> list | dict:
    """Strip markdown fences if present, then parse JSON."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]  # drop opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)


def suggest_categories(message: str) -> list[str]:
    prompt = build_suggest_angles_prompt(message)
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
    )
    return _parse_json(response.text)


def generate_drafts(message: str, categories: list[str], word_count_range: str = "150-300") -> list[str]:
    prompt = build_draft_prompt(message, categories, word_count_range)
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
    )
    parsed = _parse_json(response.text)
    return [item["draft"] for item in parsed]


def revise_draft(
    original_message: str, draft: str, feedback: str, word_count_range: str = "150-300"
) -> list[str]:
    prompt = build_edit_draft_prompt(original_message, draft, feedback, word_count_range)
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
    )
    return _parse_json(response.text)


def suggest_image_styles(draft: str) -> list[str]:
    prompt = build_suggest_image_styles_prompt(draft)
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
    )
    return _parse_json(response.text)


IMAGE_RETRY_ATTEMPTS = 3
IMAGE_RETRY_BASE_DELAY = 60  # seconds


def _generate_image_with_retry(prompt: str, label: str) -> Optional[bytes]:
    for attempt in range(IMAGE_RETRY_ATTEMPTS):
        try:
            response = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    return part.inline_data.data
            return None
        except Exception as e:
            is_rate_limit = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
            if is_rate_limit and attempt < IMAGE_RETRY_ATTEMPTS - 1:
                delay = IMAGE_RETRY_BASE_DELAY * (attempt + 1)
                logger.warning(
                    "Rate limited for %s, retrying in %ds (attempt %d/%d)",
                    label, delay, attempt + 1, IMAGE_RETRY_ATTEMPTS,
                )
                time.sleep(delay)
            else:
                logger.exception("Image generation failed for %s", label)
                return None
    return None


def generate_image(draft: str, style: str) -> Optional[bytes]:
    prompt = build_image_prompt(draft, style)
    return _generate_image_with_retry(prompt, f"style: {style}")


def generate_images(
    draft: str, styles: list[str]
) -> list[tuple[str, Optional[bytes]]]:
    results = []
    for style in styles:
        img = generate_image(draft, style)
        results.append((style, img))
    return results


def revise_images(
    draft: str, current_description: str, feedback: str
) -> list[Optional[bytes]]:
    results = []
    for i in range(3):
        prompt = build_edit_image_prompt(draft, current_description, feedback)
        full_prompt = f"(Variation {i + 1} of 3) {prompt}"
        img_bytes = _generate_image_with_retry(full_prompt, f"revision {i + 1}")
        results.append(img_bytes)
    return results
