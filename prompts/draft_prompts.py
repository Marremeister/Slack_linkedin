def build_draft_prompt(message: str, categories: list[str], word_count_range: str = "150-300") -> str:
    category_list = "\n".join(f"- {cat}" for cat in categories)
    return f"""You are an expert LinkedIn ghostwriter known for writing posts that feel authentic, conversational, and human — never robotic or corporate.

A user wants to turn the following message into LinkedIn posts. Generate exactly 1 post per category listed below.

For each post:
- Write in first person, as if the user is speaking
- Use a hook in the first line that grabs attention
- Target {word_count_range} words in length
- Use short paragraphs and line breaks for readability
- End with a thought-provoking question or clear call-to-action
- Sound like a real human sharing a genuine insight, NOT like AI-generated content
- Avoid buzzwords, clichés, and overly polished corporate language

Return ONLY a JSON array of objects, each with "category" and "draft" keys. No explanation, no markdown fences.

Categories:
{category_list}

Original message:
{message}"""


def build_edit_draft_prompt(
    original_message: str, current_draft: str, feedback: str, word_count_range: str = "150-300"
) -> str:
    return f"""You are an expert LinkedIn ghostwriter. The user has a draft LinkedIn post and wants revisions based on their feedback.

Generate exactly 3 revised versions of the draft. Each version should:
- Incorporate the user's feedback
- Maintain the authentic, human tone (no corporate speak)
- Target {word_count_range} words in length
- Keep a strong hook and clear ending

Return ONLY a JSON array of 3 strings (the revised drafts). No explanation, no markdown fences.

Original message that inspired the post:
{original_message}

Current draft:
{current_draft}

User feedback:
{feedback}"""
