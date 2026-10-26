from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from validators import parse_kst_datetime, validate_nol_ticket_url


class UrlValidationTests(unittest.TestCase):
    def test_accepts_ticket_nol_com_event_url_and_trims_whitespace(self) -> None:
        url = "  https://ticket.nol.com/places/12345?tab=info  "

        self.assertEqual(
            validate_nol_ticket_url(url),
            "https://ticket.nol.com/places/12345?tab=info",
        )

    def test_accepts_current_nol_yanolja_ticket_url(self) -> None:
        self.assertEqual(
            validate_nol_ticket_url("https://nol.yanolja.com/ticket/genre/sports/lck"),
            "https://nol.yanolja.com/ticket/genre/sports/lck",
        )

    def test_rejects_deceptive_hostname(self) -> None:
        with self.assertRaisesRegex(ValueError, "NOL Ticket"):
            validate_nol_ticket_url("https://ticket.nol.com.evil.example/places/12345")

    def test_rejects_unsupported_scheme_and_host_without_event_path(self) -> None:
        with self.assertRaises(ValueError):
            validate_nol_ticket_url("ftp://ticket.nol.com/places/12345")
        with self.assertRaises(ValueError):
            validate_nol_ticket_url("https://ticket.nol.com")

    def test_rejects_zero_port_and_empty_credentials(self) -> None:
        with self.assertRaises(ValueError):
            validate_nol_ticket_url("https://ticket.nol.com:0/places/12345")
        with self.assertRaises(ValueError):
            validate_nol_ticket_url("https://@ticket.nol.com/places/12345")

    def test_rejects_url_fragment(self) -> None:
        with self.assertRaisesRegex(ValueError, "fragment"):
            validate_nol_ticket_url("https://ticket.nol.com/places/12345#booking")


class KstDateTimeParsingTests(unittest.TestCase):
    def test_parses_seconds_in_korea_standard_time(self) -> None:
        result = parse_kst_datetime("2026-11-01", "14:03:09")

        self.assertEqual(result, datetime(2026, 11, 1, 14, 3, 9, tzinfo=ZoneInfo("Asia/Seoul")))

    def test_rejects_invalid_datetime_text(self) -> None:
        with self.assertRaisesRegex(ValueError, "날짜"):
            parse_kst_datetime("2026/11/01", "14:03:09")


if __name__ == "__main__":
    unittest.main()
