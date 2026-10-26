import unittest

from date_time_picker import format_date, format_time, month_weeks, shift_month, split_time


class CalendarModelTests(unittest.TestCase):
    def test_leap_year_february_contains_the_twenty_ninth_day(self) -> None:
        weeks = month_weeks(2028, 2)

        self.assertIn(29, [day for week in weeks for day in week])

    def test_non_leap_year_february_ends_on_the_twenty_eighth_day(self) -> None:
        weeks = month_weeks(2027, 2)

        self.assertNotIn(29, [day for week in weeks for day in week])

    def test_month_navigation_crosses_year_boundaries(self) -> None:
        self.assertEqual(shift_month(2026, 12, 1), (2027, 1))
        self.assertEqual(shift_month(2026, 1, -1), (2025, 12))

    def test_format_date_rejects_nonexistent_month_end(self) -> None:
        with self.assertRaises(ValueError):
            format_date(2027, 2, 29)


class TimeModelTests(unittest.TestCase):
    def test_formats_both_24_hour_boundary_values(self) -> None:
        self.assertEqual(format_time("00", "00", "00"), "00:00:00")
        self.assertEqual(format_time("23", "59", "59"), "23:59:59")

    def test_rejects_time_values_outside_the_selector_ranges(self) -> None:
        for values in (("24", "00", "00"), ("00", "60", "00"), ("00", "00", "60")):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    format_time(*values)

    def test_splits_a_saved_time_for_the_three_selectors(self) -> None:
        self.assertEqual(split_time("07:03:09"), ("07", "03", "09"))


if __name__ == "__main__":
    unittest.main()
