import logging
import os
import sys
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
TARGET_CHANNEL_ID = os.environ.get("TARGET_CHANNEL_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Optional LinkedIn credentials — app falls back to mock mode when absent.
LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_PERSON_URN = os.environ.get("LINKEDIN_PERSON_URN", "")
LINKEDIN_CONFIGURED = bool(LINKEDIN_ACCESS_TOKEN)

_REQUIRED = {
    "SLACK_BOT_TOKEN": SLACK_BOT_TOKEN,
    "SLACK_APP_TOKEN": SLACK_APP_TOKEN,
    "TARGET_CHANNEL_ID": TARGET_CHANNEL_ID,
    "GEMINI_API_KEY": GEMINI_API_KEY,
}

_missing = [name for name, val in _REQUIRED.items() if not val]
if _missing:
    print(f"ERROR: Missing required env vars: {', '.join(_missing)}", file=sys.stderr)
    print("Copy .env.example to .env and fill in the values.", file=sys.stderr)
    sys.exit(1)

if not LINKEDIN_CONFIGURED:
    logger.warning(
        "LINKEDIN_ACCESS_TOKEN not set — LinkedIn publishing will run in mock mode."
    )