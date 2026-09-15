"""Offline regression tests for the RAK yearly/quarterly analytics refactor."""

from pathlib import Path
import unittest

from regions.rak import analytics as data
from regions.rak import charts
from regions.rak.report_parser import parse_monthly_table_text, rows_are_complete


def monthly_row(year: int, month: str, offset: int = 0, *, missing: set[str] | None = None) -> dict:
    missing = missing or set()
    values = {
        "sales_v": 100 + offset,
        "mort_v": 200 + offset,
        "waiv_v": 300 + offset,
        "sales_n": 10 + offset,
        "mort_n": 20 + offset,
        "waiv_n": 30 + offset,
    }
    values.update({key: None for key in missing})
    return {"year": year, "month": month, **values, "source_note": f"{month} report"}


class RAKAnalyticsDataTests(unittest.TestCase):
    def test_requested_annual_years_are_fixed_and_only_report_backed_years_load(self):
        self.assertEqual(data.ANNUAL_YEAR_OPTIONS, (2022, 2023, 2024))
        self.assertEqual(data.annual_snapshot(2022).source["id"], "rak_annual_2022")
        self.assertEqual(data.annual_snapshot(2024).source["id"], "rak_annual_2025")
        self.assertIsNone(data.annual_snapshot(2023))

    def test_complete_quarter_sums_only_numeric_monthly_metrics(self):
        rows = [
            monthly_row(2024, "January", 0),
            monthly_row(2024, "February", 1),
            monthly_row(2024, "March", 2),
        ]
        snapshot = data.quarterly_snapshot(2024, "Q1", rows)
        self.assertEqual(data.available_quarters(2024, rows), ("Q1",))
        self.assertEqual(snapshot.months, ("January", "February", "March"))
        self.assertEqual(snapshot.metrics["sales_v"], 303)
        self.assertEqual(snapshot.metrics["mort_v"], 603)
        self.assertEqual(snapshot.metrics["waiv_v"], 903)
        self.assertEqual(snapshot.metrics["sales_n"], 33)
        self.assertEqual(snapshot.metrics["total_v"], 1809)
        self.assertEqual(snapshot.metrics["total_n"], 189)
        self.assertEqual(snapshot.monthly[0]["month"], "January")
        self.assertEqual(snapshot.monthly[-1]["month"], "March")

    def test_missing_required_month_does_not_create_incomplete_quarter(self):
        rows = [monthly_row(2024, "January"), monthly_row(2024, "March")]
        self.assertEqual(data.available_quarters(2024, rows), ())
        self.assertIsNone(data.quarterly_snapshot(2024, "Q1", rows))

    def test_missing_cell_is_not_converted_to_zero(self):
        rows = [
            monthly_row(2024, "January", missing={"waiv_v"}),
            monthly_row(2024, "February"),
            monthly_row(2024, "March"),
        ]
        normalised = data.normalise_monthly_record(rows[0])
        self.assertIsNone(normalised["waiv_v"])
        self.assertIsNone(normalised["total_v"])
        self.assertEqual(data.available_quarters(2024, rows), ())
        self.assertIsNone(data.quarterly_snapshot(2024, "Q1", rows))

    def test_conservative_pdf_ocr_cell_normalisation(self):
        self.assertEqual(data.parse_numeric("AED 1,234,567"), 1234567)
        self.assertEqual(data.parse_numeric("(1,250)"), -1250)
        self.assertIsNone(data.parse_numeric("1,000 2,000"))
        self.assertIsNone(data.parse_numeric("—"))

    def test_quarter_options_are_derived_from_the_supplied_monthly_registry(self):
        self.assertEqual(data.available_quarters(2022), ())
        self.assertEqual(data.available_quarters(2023), ("Q1", "Q2"))
        self.assertEqual(data.available_quarters(2024), ("Q1", "Q2"))
        self.assertEqual(data.latest_completed_quarter(), (2024, "Q2"))

    def test_future_monthly_report_additions_automatically_unlock_a_quarter(self):
        rows = list(data.monthly_records())
        rows.extend([
            monthly_row(2024, "July"),
            monthly_row(2024, "August"),
            monthly_row(2024, "September"),
        ])
        self.assertEqual(data.available_quarters(2024, rows), ("Q1", "Q2", "Q3"))

    def test_supplied_ocr_table_extract_maps_both_year_columns(self):
        text = """
        Real Estate Sales Volume 180,119,152 109,910,233 64%
        Real Estate Mortgages Volume 159,506,056 55,975,469 185%
        Waivers Market Value 74,584,954 73,410,000 2%
        Real Estate Sales Number 234 201 16%
        Real Estate Mortgages Number 98 40 145%
        Waivers Number 69 51 35%
        """
        rows = parse_monthly_table_text(
            text,
            month="February",
            current_year=2024,
            previous_year=2023,
            source_note="February report",
        )
        self.assertTrue(rows_are_complete(rows))
        self.assertEqual(rows[0]["year"], 2024)
        self.assertEqual(rows[0]["sales_v"], 180119152)
        self.assertEqual(rows[1]["year"], 2023)
        self.assertEqual(rows[1]["waiv_n"], 51)

    def test_partial_ocr_table_is_rejected_before_registry_ingestion(self):
        rows = parse_monthly_table_text(
            "Real Estate Sales Volume 1,000 900 11%",
            month="February",
            current_year=2024,
            previous_year=2023,
        )
        self.assertEqual(rows, ())


class RAKAnalyticsPresentationTests(unittest.TestCase):
    def test_plot_builders_share_dynamic_titles_and_monthly_quarter_series(self):
        annual = data.annual_snapshot(2024)
        quarterly = data.quarterly_snapshot(
            2024,
            "Q1",
            [monthly_row(2024, "January"), monthly_row(2024, "February"), monthly_row(2024, "March")],
        )
        self.assertEqual(len(charts.annual_value_chart(annual).data), 1)
        self.assertIn("2024", charts.annual_value_chart(annual).layout.title.text)
        monthly_chart = charts.quarterly_monthly_value_chart(quarterly)
        self.assertIn("Q1 2024", monthly_chart.layout.title.text)
        self.assertEqual(len(monthly_chart.data), 3)
        self.assertEqual(list(monthly_chart.data[0].x), ["January", "February", "March"])

    def test_dashboard_has_two_sections_and_no_legacy_tabbed_sections(self):
        dashboard = (Path(__file__).parents[1] / "regions/rak/dashboard.py").read_text()
        region_page = (Path(__file__).parents[1] / "platform_pages/region_rak.py").read_text()
        self.assertEqual(dashboard.count('ui.section('), 2)
        self.assertIn('"Yearly Analytics"', dashboard)
        self.assertIn('"Quarterly Analytics"', dashboard)
        self.assertNotIn("st.tabs", dashboard)
        self.assertNotIn("annual_count_chart", dashboard)
        self.assertNotIn("quarterly_count_chart", dashboard)
        self.assertNotIn("quarterly_value_chart", dashboard)
        self.assertNotIn("2024 vs 2025", dashboard)
        self.assertNotIn("2021 vs 2022", dashboard)
        self.assertNotIn("2024–2025", region_page)


if __name__ == "__main__":
    unittest.main()
