"""Slack → LinkedIn Post Bot entry point."""

import logging

import config  # noqa: F401  — validates env vars on import

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from handlers import (
    message_handler,
    category_actions,
    draft_actions,
    image_actions,
    publish_actions,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = App(token=config.SLACK_BOT_TOKEN)

# Register all handlers
message_handler.register(app)
category_actions.register(app)
draft_actions.register(app)
image_actions.register(app)
publish_actions.register(app)

if __name__ == "__main__":
    logger.info("Starting LinkedIn Post Bot (Socket Mode)...")
    handler = SocketModeHandler(app, config.SLACK_APP_TOKEN)
    handler.start()
