"""Tests for prompts/*.py — verify prompt builders include key information."""

from prompts.category_prompts import build_suggest_angles_prompt, build_suggest_image_styles_prompt
from prompts.draft_prompts import build_draft_prompt, build_edit_draft_prompt
from prompts.image_prompts import build_edit_image_prompt, build_image_prompt


class TestSuggestAnglesPrompt:
    def test_contains_message(self):
        prompt = build_suggest_angles_prompt("My big idea about AI")
        assert "My big idea about AI" in prompt

    def test_mentions_json(self):
        prompt = build_suggest_angles_prompt("anything")
        assert "JSON" in prompt


class TestSuggestImageStylesPrompt:
    def test_contains_draft(self):
        prompt = build_suggest_image_styles_prompt("This is my LinkedIn post draft.")
        assert "This is my LinkedIn post draft." in prompt

    def test_mentions_json(self):
        prompt = build_suggest_image_styles_prompt("draft")
        assert "JSON" in prompt


class TestDraftPrompt:
    def test_contains_categories_and_range(self):
        prompt = build_draft_prompt("my message", ["Hot Take", "Tutorial"], "100-200")
        assert "Hot Take" in prompt
        assert "Tutorial" in prompt
        assert "100-200" in prompt
        assert "my message" in prompt

    def test_default_word_count(self):
        prompt = build_draft_prompt("msg", ["A"])
        assert "150-300" in prompt


class TestEditDraftPrompt:
    def test_contains_feedback(self):
        prompt = build_edit_draft_prompt("orig", "current draft", "make it shorter", "50-100")
        assert "make it shorter" in prompt
        assert "current draft" in prompt
        assert "orig" in prompt
        assert "50-100" in prompt


class TestImagePrompt:
    def test_contains_style(self):
        prompt = build_image_prompt("my draft", "Minimalist Infographic")
        assert "Minimalist Infographic" in prompt
        assert "my draft" in prompt


class TestEditImagePrompt:
    def test_contains_feedback(self):
        prompt = build_edit_image_prompt("draft", "original style", "more colors")
        assert "more colors" in prompt
        assert "original style" in prompt
        assert "draft" in prompt
