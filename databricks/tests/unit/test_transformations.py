"""
Unit tests for duration formatting, holiday calculations, and transformation logic.
"""

import unittest
from datetime import date
from databricks.src.common.audit import format_duration
from databricks.src.common.holidays import FrenchHolidaysCalculator, calculate_easter_sunday


class TestCommonUtilities(unittest.TestCase):

    def test_format_duration_seconds(self):
        self.assertEqual(format_duration(5000), "5s")
        self.assertEqual(format_duration(45000), "45s")

    def test_format_duration_minutes(self):
        self.assertEqual(format_duration(65000), "01m 05s")
        self.assertEqual(format_duration(135000), "02m 15s")

    def test_format_duration_hours(self):
        self.assertEqual(format_duration(3665000), "1h 01m 05s")

    def test_easter_calculation(self):
        self.assertEqual(calculate_easter_sunday(2025), date(2025, 4, 20))
        self.assertEqual(calculate_easter_sunday(2026), date(2026, 4, 5))

    def test_french_holidays_2025(self):
        holidays_2025 = FrenchHolidaysCalculator.get_holidays_for_year(2025)
        self.assertEqual(holidays_2025[date(2025, 1, 1)], "Jour de l'An")
        self.assertEqual(holidays_2025[date(2025, 5, 1)], "Fête du Travail")
        self.assertEqual(holidays_2025[date(2025, 12, 25)], "Noël")
        self.assertEqual(holidays_2025[date(2025, 4, 21)], "Lundi de Pâques")


if __name__ == "__main__":
    unittest.main()
