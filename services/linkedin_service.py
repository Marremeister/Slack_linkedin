"""LinkedIn posting service — real API client with mock fallback."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.linkedin.com"
_cached_person_urn: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_configured() -> bool:
    return bool(config.LINKEDIN_ACCESS_TOKEN)


def _get_headers() -> dict:
    return {
        "Authorization": f"Bearer {config.LINKEDIN_ACCESS_TOKEN}",
        "LinkedIn-Version": "202401",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _resolve_person_urn() -> str:
    """Return the person URN, fetching it from /v2/userinfo if needed."""
    global _cached_person_urn

    if config.LINKEDIN_PERSON_URN:
        return config.LINKEDIN_PERSON_URN

    if _cached_person_urn:
        return _cached_person_urn

    resp = requests.get(
        f"{_BASE_URL}/v2/userinfo",
        headers=_get_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    sub = resp.json()["sub"]
    _cached_person_urn = f"urn:li:person:{sub}"
    return _cached_person_urn


def _upload_image(image_bytes: bytes) -> str:
    """Upload an image via the two-step LinkedIn flow. Returns the image URN."""
    person_urn = _resolve_person_urn()
    headers = _get_headers()

    # Step 1: Initialize upload
    init_resp = requests.post(
        f"{_BASE_URL}/rest/images?action=initializeUpload",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "initializeUploadRequest": {
                "owner": person_urn,
            }
        },
        timeout=10,
    )
    init_resp.raise_for_status()
    init_data = init_resp.json()["value"]
    upload_url = init_data["uploadUrl"]
    image_urn = init_data["image"]

    # Step 2: PUT binary bytes
    put_resp = requests.put(
        upload_url,
        headers={
            "Authorization": headers["Authorization"],
            "Content-Type": "application/octet-stream",
        },
        data=image_bytes,
        timeout=60,
    )
    put_resp.raise_for_status()

    return image_urn


def _create_post(commentary: str, image_urn: Optional[str] = None) -> dict:
    """Create a LinkedIn post. Returns the API result dict."""
    person_urn = _resolve_person_urn()
    headers = {**_get_headers(), "Content-Type": "application/json"}

    body: dict = {
        "author": person_urn,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
    }

    if image_urn:
        body["content"] = {
            "media": {
                "id": image_urn,
            }
        }

    resp = requests.post(
        f"{_BASE_URL}/rest/posts",
        headers=headers,
        json=body,
        timeout=10,
    )
    resp.raise_for_status()

    post_urn = resp.headers.get("x-restli-id", "")
    return {
        "status": "published",
        "post_id": post_urn,
        "url": f"https://www.linkedin.com/feed/update/{post_urn}",
        "timestamp": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Mock fallbacks
# ---------------------------------------------------------------------------

def _mock_publish(draft: str, image_bytes: Optional[bytes] = None) -> dict:
    image_info = f" with image ({len(image_bytes)} bytes)" if image_bytes else ""
    logger.info("MOCK PUBLISH: Publishing post%s", image_info)
    logger.info("Post content:\n%s", draft[:200])
    return {
        "status": "published",
        "post_id": "mock-post-12345",
        "url": "https://www.linkedin.com/feed/update/mock-post-12345",
        "timestamp": datetime.now().isoformat(),
        "mock": True,
    }


def _mock_schedule(
    draft: str,
    scheduled_time: datetime,
    image_bytes: Optional[bytes] = None,
) -> dict:
    image_info = f" with image ({len(image_bytes)} bytes)" if image_bytes else ""
    logger.info(
        "MOCK SCHEDULE: Scheduling post%s for %s",
        image_info,
        scheduled_time.isoformat(),
    )
    logger.info("Post content:\n%s", draft[:200])
    return {
        "status": "scheduled",
        "post_id": "mock-scheduled-67890",
        "scheduled_for": scheduled_time.isoformat(),
        "url": "https://www.linkedin.com/feed/update/mock-scheduled-67890",
        "mock": True,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def publish_post(draft: str, image_bytes: Optional[bytes] = None) -> dict:
    """Publish a post to LinkedIn, or mock if not configured."""
    if not _is_configured():
        return _mock_publish(draft, image_bytes)

    try:
        image_urn = None
        if image_bytes:
            image_urn = _upload_image(image_bytes)
        return _create_post(draft, image_urn)
    except requests.RequestException as exc:
        logger.error("LinkedIn API error during publish: %s", exc)
        return {"status": "error", "error": str(exc)}


def schedule_post(
    draft: str,
    scheduled_time: datetime,
    image_bytes: Optional[bytes] = None,
) -> dict:
    """Schedule a post. LinkedIn personal profiles have no native scheduling,
    so this publishes immediately and includes a note."""
    if not _is_configured():
        return _mock_schedule(draft, scheduled_time, image_bytes)

    try:
        image_urn = None
        if image_bytes:
            image_urn = _upload_image(image_bytes)
        result = _create_post(draft, image_urn)
        result["note"] = (
            "LinkedIn does not support native scheduling for personal profiles. "
            "The post was published immediately."
        )
        return result
    except requests.RequestException as exc:
        logger.error("LinkedIn API error during schedule: %s", exc)
        return {"status": "error", "error": str(exc)}
