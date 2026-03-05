"""Slack Block Kit message builders."""

from __future__ import annotations


WORD_COUNT_OPTIONS = [
    ("Short (50-100 words)", "50-100"),
    ("Medium (100-200 words)", "100-200"),
    ("Long (200-400 words)", "200-400"),
    ("Extra Long (400-600 words)", "400-600"),
]


def build_word_count_picker() -> list[dict]:
    options = [
        {
            "text": {"type": "plain_text", "text": label},
            "value": value,
        }
        for label, value in WORD_COUNT_OPTIONS
    ]
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*How long should your LinkedIn post be?*",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "radio_buttons",
                    "action_id": "length_select",
                    "options": options,
                }
            ],
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Confirm Length"},
                    "action_id": "confirm_length",
                    "style": "primary",
                }
            ],
        },
    ]


def build_category_checkboxes(
    categories: list[str], action_id: str = "category_select"
) -> list[dict]:
    options = [
        {
            "text": {"type": "mrkdwn", "text": cat},
            "value": cat,
        }
        for cat in categories
    ]
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Pick categories for your LinkedIn post* (or add your own below):",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "checkboxes",
                    "action_id": action_id,
                    "options": options,
                }
            ],
        },
        {
            "type": "input",
            "block_id": "custom_category_block",
            "optional": True,
            "element": {
                "type": "plain_text_input",
                "action_id": "custom_category_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Describe a custom category...",
                },
            },
            "label": {"type": "plain_text", "text": "Custom category (optional)"},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Generate Drafts"},
                    "action_id": "confirm_categories",
                    "style": "primary",
                }
            ],
        },
    ]


def build_draft_messages(drafts: list[str]) -> list[dict]:
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Here are your {len(drafts)} draft(s):*",
            },
        }
    ]
    for i, draft in enumerate(drafts):
        # Truncate for display if very long (Slack block limit is 3000 chars)
        display = draft[:2900] + "..." if len(draft) > 2900 else draft
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Draft {i + 1}:*\n\n{display}"},
            }
        )
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Accept"},
                        "action_id": f"accept_draft_{i}",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Edit with AI"},
                        "action_id": f"edit_draft_{i}",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Edit Manually"},
                        "action_id": f"edit_draft_manual_{i}",
                    },
                ],
            }
        )
    return blocks


def build_manual_edit_modal(draft: str, draft_index: int, thread_ts: str, channel_id: str) -> dict:
    """Build a Slack modal for manually editing a draft."""
    return {
        "type": "modal",
        "callback_id": "manual_edit_draft_submit",
        "private_metadata": f"{channel_id}|{thread_ts}|{draft_index}",
        "title": {"type": "plain_text", "text": "Edit Draft"},
        "submit": {"type": "plain_text", "text": "Save"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "draft_text_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "draft_text_input",
                    "multiline": True,
                    "initial_value": draft,
                },
                "label": {"type": "plain_text", "text": "Edit your post"},
            }
        ],
    }


def build_image_style_checkboxes(
    styles: list[str], action_id: str = "style_select"
) -> list[dict]:
    options = [
        {
            "text": {"type": "mrkdwn", "text": style},
            "value": style,
        }
        for style in styles
    ]
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Pick up to 3 image styles* (or describe your own below):",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "checkboxes",
                    "action_id": action_id,
                    "options": options,
                }
            ],
        },
        {
            "type": "input",
            "block_id": "custom_style_block",
            "optional": True,
            "element": {
                "type": "plain_text_input",
                "action_id": "custom_style_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Describe a custom image style...",
                },
            },
            "label": {"type": "plain_text", "text": "Custom style (optional)"},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Generate Images"},
                    "action_id": "confirm_styles",
                    "style": "primary",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Upload My Own Image"},
                    "action_id": "upload_own_image",
                },
            ],
        },
    ]


def build_image_messages(num_images: int) -> list[dict]:
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Here are your {num_images} image(s).* Choose one:",
            },
        }
    ]
    for i in range(num_images):
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Image {i + 1}* (see above)"},
            }
        )
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Accept"},
                        "action_id": f"accept_image_{i}",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Edit"},
                        "action_id": f"edit_image_{i}",
                    },
                ],
            }
        )
    return blocks


def build_publish_edit_modal(draft: str, thread_ts: str, channel_id: str) -> dict:
    """Build a Slack modal for editing the draft before publishing."""
    return {
        "type": "modal",
        "callback_id": "publish_edit_submit",
        "private_metadata": f"{channel_id}|{thread_ts}",
        "title": {"type": "plain_text", "text": "Edit Draft"},
        "submit": {"type": "plain_text", "text": "Save"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "draft_text_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "draft_text_input",
                    "multiline": True,
                    "initial_value": draft,
                },
                "label": {"type": "plain_text", "text": "Edit your post"},
            }
        ],
    }


def build_publish_options(draft: str, has_image: bool = True) -> list[dict]:
    summary = draft[:2900] + "..." if len(draft) > 2900 else draft
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Final post ready!*\n\n" + summary,
            },
        },
    ]
    if has_image:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "_(Image attached above)_"},
            }
        )
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Publish Now"},
                    "action_id": "publish_now",
                    "style": "primary",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Schedule"},
                    "action_id": "schedule_post",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Edit Before Publishing"},
                    "action_id": "edit_before_publish",
                },
            ],
        }
    )
    return blocks


def build_schedule_picker() -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*When should this post go live?*",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "datepicker",
                    "action_id": "schedule_date",
                    "placeholder": {"type": "plain_text", "text": "Pick a date"},
                },
                {
                    "type": "timepicker",
                    "action_id": "schedule_time",
                    "placeholder": {"type": "plain_text", "text": "Pick a time"},
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Confirm Schedule"},
                    "action_id": "confirm_schedule",
                    "style": "primary",
                },
            ],
        },
    ]
