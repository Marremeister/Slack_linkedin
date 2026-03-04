"""Mocked LinkedIn posting service."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def publish_post(draft: str, image_bytes: Optional[bytes] = None) -> dict:
    """Mock immediate publish to LinkedIn."""
    image_info = f" with image ({len(image_bytes)} bytes)" if image_bytes else ""
    logger.info("MOCK PUBLISH: Publishing post%s", image_info)
    logger.info("Post content:\n%s", draft[:200])
    return {
        "status": "published",
        "post_id": "mock-post-12345",
        "url": "https://www.linkedin.com/feed/update/mock-post-12345",
        "timestamp": datetime.now().isoformat(),
    }


def schedule_post(
    draft: str,
    scheduled_time: datetime,
    image_bytes: Optional[bytes] = None,
) -> dict:
    """Mock scheduled publish to LinkedIn."""
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
    }
