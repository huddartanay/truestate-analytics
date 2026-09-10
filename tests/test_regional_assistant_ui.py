"""Presentation-only regression checks for the regional/assistant refinement."""

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text()


class OverviewPresentationTests(unittest.TestCase):
    def test_overview_has_all_existing_region_routes(self):
        text = source("platform_pages/overview.py")
        for route in ("ROUTE_ABU_DHABI", "ROUTE_DUBAI", "ROUTE_SHARJAH", "ROUTE_RAK"):
            self.assertIn(f"C.{route}", text)
        for key in ("ov-go-ad", "ov-go-dxb", "ov-go-sharjah", "ov-go-rak"):
            self.assertIn(f'key="{key}"', text)

    def test_general_capabilities_are_three_non_forecast_tiles(self):
        tree = ast.parse(source("platform_pages/overview.py"))
        tiles = next(
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "tiles" for target in node.targets)
        )
        values = ast.literal_eval(tiles)
        titles = [item[1] for item in values]
        self.assertEqual(titles, ["Market measurement", "Statistical analysis", "Property & location"])
        self.assertNotIn("Forecasting", titles)

    def test_overview_uses_four_region_stat_and_no_stale_two_dashboard_copy(self):
        text = source("platform_pages/overview.py")
        self.assertIn('(\"4\", \"Regional experiences\")', text)
        self.assertNotIn('(\"2\", \"Regional dashboards\")', text)
        self.assertNotIn("Abu Dhabi and Dubai each have", text)


class AssistantPresentationTests(unittest.TestCase):
    def test_summary_is_not_wrapped_in_an_expander(self):
        text = source("platform_core/ai_ui.py")
        summary_body = text.split("def _render_summary(", 1)[1].split("def _dismiss_assistant", 1)[0]
        self.assertIn("truestate-ai-summary", summary_body)
        self.assertNotIn("st.expander", summary_body)
        self.assertIn("Generate summary", text)
        self.assertIn("Refresh summary", text)

    def test_one_shared_dialog_and_top_right_trigger_are_wired(self):
        text = source("platform_core/ai_ui.py")
        self.assertEqual(text.count("def _assistant_content("), 1)
        self.assertIn("@st.dialog", text)
        self.assertIn("ASSISTANT_OPEN", text)
        for page in (
            "platform_pages/region_abu_dhabi.py",
            "platform_pages/region_dubai.py",
            "platform_pages/region_sharjah.py",
            "platform_pages/region_rak.py",
            "platform_pages/area.py",
            "platform_pages/forecast.py",
        ):
            self.assertIn("ai_ui.render_trigger()", source(page), page)

    def test_ui_does_not_directly_call_provider(self):
        text = source("platform_core/ai_ui.py")
        self.assertNotIn("OpenRouterClient", text)
        self.assertNotIn("OPENROUTER_API_KEY", text)
        self.assertIn("service.call('help'", text)

    def test_theme_has_semantic_assistant_selectors(self):
        text = source("platform_core/design_system.py")
        for selector in (
            "truestate-ai-summary",
            "truestate-ai-trigger",
            "truestate-ai-suggestion-",
            'data-testid=\"stDialog\"',
        ):
            self.assertIn(selector, text)
        self.assertIn("--cta: #9333EA", text)
        self.assertIn("--cta: #059669", text)


if __name__ == "__main__":
    unittest.main()
