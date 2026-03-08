def build_suggest_angles_prompt(message: str) -> str:
    return f"""You are a LinkedIn content strategist. A user wants to turn the following message into a LinkedIn post.

Suggest 6-8 distinct angle categories they could take for this post. Each category should be a short label (2-5 words) representing a different perspective, tone, or theme.

Return ONLY a JSON array of strings. No explanation, no markdown fences.

Example output: ["Thought Leadership", "Personal Story", "Industry Trend", "Hot Take", "How-To Guide", "Data-Driven Insight"]

Message:
{message}"""


def build_suggest_image_styles_prompt(draft: str) -> str:
    return f"""You are a visual content strategist for LinkedIn. Given the following LinkedIn post draft, suggest 6-8 distinct image style categories that would complement this post well.

All suggestions must fit within these brand guidelines:
- Black background, white text, minimal clean layout
- Matt glass effects on cards and UI elements
- Elegant, modern, minimal european editorial aesthetic
- Photographic styles: realistic european settings, black & white photography, or clean parisian-style color photography of people
- No bright colors, no cartoons, no hand-drawn or playful styles

Each style should be a short label (2-5 words) representing a different visual approach within these constraints.

Return ONLY a JSON array of strings. No explanation, no markdown fences.

Example output: ["B&W European Office", "Parisian Street Portrait", "Glass Card Infographic", "Minimal Data Layout", "Editorial Photography", "Dark Keynote Slide"]

Post draft:
{draft}"""
