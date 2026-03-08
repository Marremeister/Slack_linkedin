def build_image_prompt(draft: str, style: str) -> str:
    return f"""Create a LinkedIn post image in the following style: {style}

The image should visually complement this LinkedIn post:
{draft}

Visual guidelines (strict):
- Black background with simple white text where text is needed
- Font style: clean sans-serif (Roboto-like), all lowercase body text, no capital letters
- Minimal and clean layout with strong visual hierarchy
- Use matt glass effects on cards, panels, and UI elements
- Elegant, modern, minimal aesthetic — european editorial feel
- For photographic content: realistic photos in european settings, european offices with european people
- Photography preference: black & white, or clean parisian-style color photography of people
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

Visual guidelines (strict — always apply unless user feedback explicitly overrides):
- Black background with simple white text where text is needed
- Font style: clean sans-serif (Roboto-like), all lowercase body text, no capital letters
- Minimal and clean layout with strong visual hierarchy
- Use matt glass effects on cards, panels, and UI elements
- Elegant, modern, minimal aesthetic — european editorial feel
- For photographic content: realistic photos in european settings, european offices with european people
- Photography preference: black & white, or clean parisian-style color photography of people
- No text overlays or watermarks
- High quality, polished look

Additional:
- Incorporate the user's feedback above"""
