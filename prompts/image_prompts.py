def build_image_prompt(draft: str, style: str) -> str:
    return f"""Create a LinkedIn post image in the following style: {style}

The image should visually complement this LinkedIn post:
{draft}

Requirements:
- Professional and suitable for LinkedIn
- Clean composition with good visual hierarchy
- No text overlays or watermarks
- High quality, polished look
- Aspect ratio suitable for LinkedIn feed (landscape or square)"""


def build_edit_image_prompt(
    draft: str, current_description: str, feedback: str
) -> str:
    return f"""Create a revised LinkedIn post image based on user feedback.

Original image style/description: {current_description}

LinkedIn post it accompanies:
{draft}

User feedback on what to change:
{feedback}

Requirements:
- Incorporate the user's feedback
- Professional and suitable for LinkedIn
- Clean composition with good visual hierarchy
- No text overlays or watermarks
- High quality, polished look"""
