from datetime import datetime, timedelta
import unittest
from zoneinfo import ZoneInfo

from scheduler import ScheduleController


KST = ZoneInfo("Asia/Seoul")


class ScheduleControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.target = datetime(2026, 11, 1, 14, 0, 0, tzinfo=KST)
        self.alerts: list[str] = []
        self.opened_urls: list[str] = []
        self.controller = ScheduleController(
            self.target,
            "https://ticket.nol.com/places/12345",
            self.alerts.append,
            self.opened_urls.append,
        )
        self.controller.start()

    def test_alerts_at_ten_minutes_and_one_minute_only_once(self) -> None:
        self.assertEqual(self.controller.tick(self.target - timedelta(minutes=10)), "00:10:00")
        self.assertEqual(self.controller.tick(self.target - timedelta(minutes=9, seconds=59)), "00:09:59")
        self.assertEqual(self.controller.tick(self.target - timedelta(minutes=1)), "00:01:00")
        self.assertEqual(self.controller.tick(self.target - timedelta(seconds=59)), "00:00:59")

        self.assertEqual(self.alerts, ["예매 시작 10분 전입니다.", "예매 시작 1분 전입니다."])

    def test_opens_once_when_tick_reaches_or_passes_target(self) -> None:
        self.assertEqual(self.controller.tick(self.target + timedelta(seconds=2)), "00:00:00")
        self.assertEqual(self.controller.tick(self.target + timedelta(seconds=5)), "00:00:00")

        self.assertEqual(self.opened_urls, ["https://ticket.nol.com/places/12345"])

    def test_does_not_open_in_the_fractional_second_before_target(self) -> None:
        just_before_target = self.target - timedelta(microseconds=500_000)

        self.assertEqual(self.controller.tick(just_before_target), "00:00:01")
        self.assertEqual(self.opened_urls, [])

    def test_stopped_controller_performs_no_callback_actions(self) -> None:
        self.controller.stop()

        self.assertEqual(self.controller.tick(self.target - timedelta(minutes=10)), "--:--:--")
        self.assertEqual(self.alerts, [])
        self.assertEqual(self.opened_urls, [])


if __name__ == "__main__":
    unittest.main()
