def build_suggest_angles_prompt(message: str) -> str:
    return f"""You are a LinkedIn content strategist. A user wants to turn the following message into a LinkedIn post.

Suggest 6-8 distinct angle categories they could take for this post. Each category should be a short label (2-5 words) representing a different perspective, tone, or theme.

Return ONLY a JSON array of strings. No explanation, no markdown fences.

Example output: ["Thought Leadership", "Personal Story", "Industry Trend", "Hot Take", "How-To Guide", "Data-Driven Insight"]

Message:
{message}"""


def build_suggest_image_styles_prompt(draft: str) -> str:
    return f"""You are a visual content strategist for LinkedIn. Given the following LinkedIn post draft, suggest 6-8 distinct image style categories that would complement this post well.

Each style should be a short label (2-5 words) representing a different visual approach.

Return ONLY a JSON array of strings. No explanation, no markdown fences.

Example output: ["Minimalist Infographic", "Professional Photo", "Abstract Gradient", "Hand-drawn Sketch", "Bold Typography", "Data Visualization"]

Post draft:
{draft}"""
