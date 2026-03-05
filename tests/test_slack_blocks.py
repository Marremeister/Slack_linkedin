"""Tests for services/slack_blocks.py."""

from services.slack_blocks import (
    build_category_checkboxes,
    build_draft_messages,
    build_image_messages,
    build_image_style_checkboxes,
    build_manual_edit_modal,
    build_publish_edit_modal,
    build_publish_options,
    build_schedule_picker,
    build_word_count_picker,
)


class TestBuildWordCountPicker:
    def test_returns_correct_structure(self):
        blocks = build_word_count_picker()
        # section + radio actions + button actions = 3 blocks
        assert len(blocks) == 3
        assert blocks[0]["type"] == "section"

    def test_radio_has_four_options(self):
        blocks = build_word_count_picker()
        radio = blocks[1]["elements"][0]
        assert radio["type"] == "radio_buttons"
        assert radio["action_id"] == "length_select"
        assert len(radio["options"]) == 4

    def test_confirm_button(self):
        blocks = build_word_count_picker()
        btn = blocks[2]["elements"][0]
        assert btn["action_id"] == "confirm_length"
        assert btn["style"] == "primary"


class TestBuildCategoryCheckboxes:
    def test_correct_checkbox_options(self):
        cats = ["Thought Leadership", "Personal Story"]
        blocks = build_category_checkboxes(cats)
        checkboxes = blocks[1]["elements"][0]
        assert checkboxes["type"] == "checkboxes"
        assert checkboxes["action_id"] == "category_select"
        values = [o["value"] for o in checkboxes["options"]]
        assert values == cats

    def test_has_custom_input_block(self):
        blocks = build_category_checkboxes(["A"])
        input_block = blocks[2]
        assert input_block["type"] == "input"
        assert input_block["block_id"] == "custom_category_block"
        assert input_block["optional"] is True

    def test_confirm_button(self):
        blocks = build_category_checkboxes(["A"])
        btn = blocks[3]["elements"][0]
        assert btn["action_id"] == "confirm_categories"


class TestBuildDraftMessages:
    def test_one_section_plus_actions_per_draft(self):
        drafts = ["Draft A", "Draft B"]
        blocks = build_draft_messages(drafts)
        # header + (divider + section + actions) * 2 = 1 + 6 = 7
        assert len(blocks) == 7

    def test_correct_action_ids(self):
        blocks = build_draft_messages(["D1", "D2"])
        # actions blocks are at index 3 and 6
        btns_0 = blocks[3]["elements"]
        assert btns_0[0]["action_id"] == "accept_draft_0"
        assert btns_0[1]["action_id"] == "edit_draft_0"
        assert btns_0[2]["action_id"] == "edit_draft_manual_0"

        btns_1 = blocks[6]["elements"]
        assert btns_1[0]["action_id"] == "accept_draft_1"

    def test_truncates_long_draft(self):
        long_draft = "x" * 3000
        blocks = build_draft_messages([long_draft])
        section_text = blocks[2]["text"]["text"]
        assert section_text.endswith("...")
        assert len(section_text) < 3100


class TestBuildManualEditModal:
    def test_callback_id(self):
        modal = build_manual_edit_modal("draft", 0, "ts1", "C1")
        assert modal["callback_id"] == "manual_edit_draft_submit"

    def test_private_metadata_format(self):
        modal = build_manual_edit_modal("draft", 2, "ts1", "C1")
        assert modal["private_metadata"] == "C1|ts1|2"

    def test_initial_value(self):
        modal = build_manual_edit_modal("my draft text", 0, "ts1", "C1")
        element = modal["blocks"][0]["element"]
        assert element["initial_value"] == "my draft text"


class TestBuildImageStyleCheckboxes:
    def test_checkbox_options_match_input(self):
        styles = ["Minimalist", "Bold Typography", "Photo"]
        blocks = build_image_style_checkboxes(styles)
        checkboxes = blocks[1]["elements"][0]
        assert checkboxes["type"] == "checkboxes"
        values = [o["value"] for o in checkboxes["options"]]
        assert values == styles

    def test_has_upload_button(self):
        blocks = build_image_style_checkboxes(["A"])
        btns = blocks[3]["elements"]
        action_ids = [b["action_id"] for b in btns]
        assert "upload_own_image" in action_ids


class TestBuildImageMessages:
    def test_correct_accept_edit_buttons(self):
        blocks = build_image_messages(2)
        # header + (divider + section + actions) * 2 = 1 + 6 = 7
        assert len(blocks) == 7
        btns_0 = blocks[3]["elements"]
        assert btns_0[0]["action_id"] == "accept_image_0"
        assert btns_0[1]["action_id"] == "edit_image_0"
        btns_1 = blocks[6]["elements"]
        assert btns_1[0]["action_id"] == "accept_image_1"


class TestBuildPublishEditModal:
    def test_callback_id(self):
        modal = build_publish_edit_modal("draft", "ts1", "C1")
        assert modal["callback_id"] == "publish_edit_submit"

    def test_metadata_format(self):
        modal = build_publish_edit_modal("draft", "ts1", "C1")
        assert modal["private_metadata"] == "C1|ts1"

    def test_initial_value(self):
        modal = build_publish_edit_modal("my text", "ts1", "C1")
        element = modal["blocks"][0]["element"]
        assert element["initial_value"] == "my text"


class TestBuildPublishOptions:
    def test_with_image(self):
        blocks = build_publish_options("draft text", has_image=True)
        texts = [b.get("text", {}).get("text", "") for b in blocks]
        assert any("Image attached" in t for t in texts)

    def test_without_image(self):
        blocks = build_publish_options("draft text", has_image=False)
        texts = [b.get("text", {}).get("text", "") for b in blocks]
        assert not any("Image attached" in t for t in texts)

    def test_three_buttons(self):
        blocks = build_publish_options("draft", has_image=True)
        actions_block = [b for b in blocks if b["type"] == "actions"][0]
        ids = [e["action_id"] for e in actions_block["elements"]]
        assert ids == ["publish_now", "schedule_post", "edit_before_publish"]


class TestBuildSchedulePicker:
    def test_has_datepicker_timepicker_and_confirm(self):
        blocks = build_schedule_picker()
        elements = blocks[1]["elements"]
        types = [e["type"] for e in elements]
        assert "datepicker" in types
        assert "timepicker" in types
        assert "button" in types
        btn = [e for e in elements if e["type"] == "button"][0]
        assert btn["action_id"] == "confirm_schedule"
