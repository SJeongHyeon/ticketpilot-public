"""Non-blocking schedule state logic, independent of the GUI toolkit."""

from collections.abc import Callable
from datetime import datetime
from math import ceil

from validators import KST


class ScheduleController:
    """Track one ticket sale schedule and emit each action at most once."""

    def __init__(
        self,
        target: datetime,
        url: str,
        on_alert: Callable[[str], None],
        on_open: Callable[[str], None],
    ) -> None:
        self.target = self._as_kst(target)
        self.url = url
        self.on_alert = on_alert
        self.on_open = on_open
        self.is_running = False
        self._ten_minute_alerted = False
        self._one_minute_alerted = False
        self._opened = False

    @staticmethod
    def _as_kst(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=KST)
        return value.astimezone(KST)

    def start(self) -> None:
        self.is_running = True
        self._ten_minute_alerted = False
        self._one_minute_alerted = False
        self._opened = False

    def stop(self) -> None:
        self.is_running = False

    def tick(self, now: datetime) -> str:
        """Process one clock update and return the display countdown string."""
        if self._opened:
            return "00:00:00"
        if not self.is_running:
            return "--:--:--"

        remaining_duration = self.target - self._as_kst(now)
        if remaining_duration.total_seconds() <= 0:
            if not self._opened:
                self._opened = True
                self.on_open(self.url)
            self.is_running = False
            return "00:00:00"

        remaining_seconds = ceil(remaining_duration.total_seconds())

        if remaining_seconds <= 10 * 60 and not self._ten_minute_alerted:
            self._ten_minute_alerted = True
            self.on_alert("예매 시작 10분 전입니다.")
        if remaining_seconds <= 60 and not self._one_minute_alerted:
            self._one_minute_alerted = True
            self.on_alert("예매 시작 1분 전입니다.")

        hours, remainder = divmod(remaining_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
