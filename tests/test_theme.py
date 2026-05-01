"""Unit tests for theme.py — runtime CSS injection for light/dark/system."""

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import theme
from theme import (
    THEME_CHOICES,
    DEFAULT_THEME,
    THEME_CSS,
    apply_theme,
    resolve_choice,
    get_css_for,
)


class TestThemeConstants(unittest.TestCase):
    def test_theme_choices(self):
        self.assertEqual(THEME_CHOICES, ["🌞 Light", "🌙 Dark", "⚙️ System"])

    def test_default_theme_is_system(self):
        self.assertEqual(DEFAULT_THEME, "⚙️ System")
        self.assertIn(DEFAULT_THEME, THEME_CHOICES)

    def test_theme_css_keys(self):
        self.assertIn("🌙 Dark", THEME_CSS)
        self.assertIn("🌞 Light", THEME_CSS)
        self.assertNotIn("⚙️ System", THEME_CSS)

    def test_theme_css_files_exist(self):
        for choice, path in THEME_CSS.items():
            self.assertTrue(path.exists(), f"CSS for {choice} missing at {path}")

    def test_theme_css_files_have_content(self):
        for choice, path in THEME_CSS.items():
            content = path.read_text()
            self.assertGreater(len(content), 50, f"CSS for {choice} is too small")
            self.assertIn("!important", content, f"{choice} should override Streamlit")

    def test_dark_css_targets_app(self):
        css = THEME_CSS["🌙 Dark"].read_text()
        self.assertIn(".stApp", css)
        self.assertIn("background-color", css)


class TestResolveChoice(unittest.TestCase):
    def test_valid_dark(self):
        self.assertEqual(resolve_choice("🌙 Dark"), "🌙 Dark")

    def test_valid_light(self):
        self.assertEqual(resolve_choice("🌞 Light"), "🌞 Light")

    def test_valid_system(self):
        self.assertEqual(resolve_choice("⚙️ System"), "⚙️ System")

    def test_none_returns_default(self):
        self.assertEqual(resolve_choice(None), DEFAULT_THEME)

    def test_empty_string_returns_default(self):
        self.assertEqual(resolve_choice(""), DEFAULT_THEME)

    def test_unknown_returns_default(self):
        self.assertEqual(resolve_choice("🌈 Rainbow"), DEFAULT_THEME)


class TestGetCssFor(unittest.TestCase):
    def test_dark_returns_string(self):
        css = get_css_for("🌙 Dark")
        self.assertIsInstance(css, str)
        self.assertIn("!important", css)

    def test_light_returns_string(self):
        css = get_css_for("🌞 Light")
        self.assertIsInstance(css, str)
        self.assertIn("!important", css)

    def test_system_returns_none(self):
        self.assertIsNone(get_css_for("⚙️ System"))

    def test_unknown_returns_none(self):
        self.assertIsNone(get_css_for("🌈 Rainbow"))

    def test_missing_file_returns_none(self):
        with patch.dict(theme.THEME_CSS,
                        {"🌙 Dark": Path("/nonexistent/path.css")},
                        clear=False):
            self.assertIsNone(get_css_for("🌙 Dark"))


class TestApplyTheme(unittest.TestCase):
    def test_dark_injects_css(self):
        with patch.object(theme, "st") as mock_st:
            mock_st.session_state = {"theme_choice": "🌙 Dark"}
            mock_st.markdown = MagicMock()
            apply_theme()
            mock_st.markdown.assert_called_once()
            call_args = mock_st.markdown.call_args
            self.assertIn("<style>", call_args[0][0])
            self.assertIn("</style>", call_args[0][0])
            self.assertTrue(call_args[1].get("unsafe_allow_html"))

    def test_light_injects_css(self):
        with patch.object(theme, "st") as mock_st:
            mock_st.session_state = {"theme_choice": "🌞 Light"}
            mock_st.markdown = MagicMock()
            apply_theme()
            mock_st.markdown.assert_called_once()

    def test_system_no_inject(self):
        with patch.object(theme, "st") as mock_st:
            mock_st.session_state = {"theme_choice": "⚙️ System"}
            mock_st.markdown = MagicMock()
            apply_theme()
            mock_st.markdown.assert_not_called()

    def test_default_no_inject_when_missing_key(self):
        with patch.object(theme, "st") as mock_st:
            mock_st.session_state = {}
            mock_st.markdown = MagicMock()
            apply_theme()
            # Default = system → no inject
            mock_st.markdown.assert_not_called()

    def test_unknown_choice_no_inject(self):
        with patch.object(theme, "st") as mock_st:
            mock_st.session_state = {"theme_choice": "🌈 Rainbow"}
            mock_st.markdown = MagicMock()
            apply_theme()
            mock_st.markdown.assert_not_called()

    def test_missing_file_no_crash(self):
        with patch.object(theme, "st") as mock_st, \
             patch.dict(theme.THEME_CSS,
                        {"🌙 Dark": Path("/nonexistent/dark.css")},
                        clear=False):
            mock_st.session_state = {"theme_choice": "🌙 Dark"}
            mock_st.markdown = MagicMock()
            apply_theme()  # must not raise
            mock_st.markdown.assert_not_called()


if __name__ == "__main__":
    unittest.main()
