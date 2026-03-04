import os
import sys
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
TARGET_CHANNEL_ID = os.environ.get("TARGET_CHANNEL_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

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