"""Focused tests for the Abu Dhabi prepared-data performance contract."""

from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from regions.abu_dhabi.config.settings import PARQUET_FILE, PREPARED_COLUMNS
from tools.build_abu_dhabi_parquet import SOURCE, TARGET, prepare
from regions.abu_dhabi.utils import data_loader


class AbuDhabiParquetTests(unittest.TestCase):
    def test_prepared_artifact_exists_and_has_runtime_schema(self):
        self.assertTrue(TARGET.exists(), TARGET)
        frame = pd.read_parquet(TARGET)
        self.assertEqual(list(frame.columns), list(PREPARED_COLUMNS))
        self.assertEqual(len(frame), 109097)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(frame["Sale Application Date"]))

    def test_prepared_artifact_matches_existing_csv_loader_contract(self):
        expected = prepare(pd.read_csv(SOURCE, low_memory=False))
        actual = pd.read_parquet(TARGET, columns=list(PREPARED_COLUMNS))
        pd.testing.assert_frame_equal(expected, actual, check_dtype=True, check_exact=True)

    def test_runtime_loader_is_parquet_only_and_fingerprint_keyed(self):
        source = Path(data_loader.__file__).read_text()
        self.assertIn("pd.read_parquet", source)
        self.assertNotIn("pd.read_csv", source)
        self.assertIn("modified_ns", source)
        self.assertEqual(data_loader._data_path().name, PARQUET_FILE)

    def test_report_module_does_not_import_pdf_renderer_for_district_list(self):
        source = Path("platform_core/abu_dhabi_report.py").read_text()
        self.assertIn("pd.read_parquet", source)
        self.assertNotIn("pd.read_csv", source)
        self.assertIn("def _pdf_renderer", source)


class PageTimingTests(unittest.TestCase):
    def test_shared_timer_covers_all_routes_with_friendly_output(self):
        source = Path("platform_core/performance.py").read_text()
        for route in ("overview", "abu_dhabi", "dubai", "sharjah", "rak",
                      "area", "report", "forecast", "experimental", "explore", "about"):
            self.assertIn(f'"{route}"', source)
        self.assertIn("perf_counter", source)
        self.assertIn("Page prepared in {elapsed:.2f}s", source)


if __name__ == "__main__":
    unittest.main()
