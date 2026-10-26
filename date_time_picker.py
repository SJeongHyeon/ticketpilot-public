"""Dark calendar and time-selection helpers for TicketPilot."""

import calendar
from datetime import date
from typing import Callable

import customtkinter as ctk


ACCENT = "#3B82F6"
ACCENT_HOVER = "#2563EB"
FIELD = "#2A2A2A"
MUTED_TEXT = "#A3A3A3"
SURFACE = "#1B1B1B"
SURFACE_RAISED = "#242424"
TEXT = "#F5F5F5"

WEEKDAY_NAMES = ("일", "월", "화", "수", "목", "금", "토")
HOUR_VALUES = tuple(f"{hour:02d}" for hour in range(24))
MINUTE_SECOND_VALUES = tuple(f"{value:02d}" for value in range(60))


def month_weeks(year: int, month: int) -> list[list[int]]:
    """Return Sunday-first calendar rows, using zero for blank cells."""
    return calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """Move a year/month pair by a whole number of months."""
    if not 1 <= month <= 12:
        raise ValueError("월은 1부터 12 사이여야 합니다.")
    index = year * 12 + (month - 1) + delta
    return divmod(index, 12)[0], divmod(index, 12)[1] + 1


def format_date(year: int, month: int, day: int) -> str:
    """Validate and return a selected calendar date in configuration format."""
    return date(year, month, day).isoformat()


def format_time(hour: str, minute: str, second: str) -> str:
    """Validate selector values and return the existing configuration format."""
    try:
        values = tuple(int(value) for value in (hour, minute, second))
    except ValueError as error:
        raise ValueError("시각은 숫자여야 합니다.") from error
    hour_value, minute_value, second_value = values
    if not 0 <= hour_value <= 23:
        raise ValueError("시는 00부터 23 사이여야 합니다.")
    if not 0 <= minute_value <= 59 or not 0 <= second_value <= 59:
        raise ValueError("분과 초는 00부터 59 사이여야 합니다.")
    return f"{hour_value:02d}:{minute_value:02d}:{second_value:02d}"


def split_time(value: str) -> tuple[str, str, str]:
    """Validate a saved time and split it for the three selector controls."""
    parts = value.split(":")
    if len(parts) != 3:
        raise ValueError("시각 형식은 HH:MM:SS여야 합니다.")
    formatted = format_time(*parts)
    return tuple(formatted.split(":"))  # type: ignore[return-value]


class CalendarPopup(ctk.CTkToplevel):
    """A single-use dark-themed date picker backed by standard calendar data."""

    def __init__(
        self,
        master: ctk.CTk,
        selected_date: date,
        on_select: Callable[[str], None],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._selected_date = selected_date
        self._displayed_year = selected_date.year
        self._displayed_month = selected_date.month
        self._on_select = on_select
        self._on_close = on_close
        self.title("예매 시작 날짜 선택")
        self.configure(fg_color=SURFACE)
        self.resizable(False, False)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._build_widgets()
        self._render_calendar()

    def _build_widgets(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self._header = ctk.CTkFrame(self, fg_color="transparent")
        self._header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        self._header.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            self._header,
            text="‹",
            width=36,
            command=lambda: self._change_month(-1),
            fg_color="transparent",
            hover_color=SURFACE_RAISED,
            text_color=TEXT,
        ).grid(row=0, column=0)
        self._month_label = ctk.CTkLabel(
            self._header, text_color=TEXT, font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        )
        self._month_label.grid(row=0, column=1)
        ctk.CTkButton(
            self._header,
            text="›",
            width=36,
            command=lambda: self._change_month(1),
            fg_color="transparent",
            hover_color=SURFACE_RAISED,
            text_color=TEXT,
        ).grid(row=0, column=2)
        self._calendar_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._calendar_frame.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
        for column in range(7):
            self._calendar_frame.grid_columnconfigure(column, weight=1, minsize=38)

    def _render_calendar(self) -> None:
        for child in self._calendar_frame.winfo_children():
            child.destroy()
        self._month_label.configure(text=f"{self._displayed_year}년 {self._displayed_month:02d}월")
        for column, weekday in enumerate(WEEKDAY_NAMES):
            ctk.CTkLabel(
                self._calendar_frame,
                text=weekday,
                text_color=MUTED_TEXT,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            ).grid(row=0, column=column, padx=2, pady=(0, 4))
        for row, week in enumerate(month_weeks(self._displayed_year, self._displayed_month), start=1):
            for column, day in enumerate(week):
                if day == 0:
                    ctk.CTkLabel(self._calendar_frame, text="", width=36, height=32).grid(
                        row=row, column=column, padx=2, pady=2
                    )
                    continue
                is_selected = (
                    self._selected_date.year == self._displayed_year
                    and self._selected_date.month == self._displayed_month
                    and self._selected_date.day == day
                )
                ctk.CTkButton(
                    self._calendar_frame,
                    text=str(day),
                    width=36,
                    height=32,
                    command=lambda selected_day=day: self._select_day(selected_day),
                    fg_color=ACCENT if is_selected else FIELD,
                    hover_color=ACCENT_HOVER if is_selected else SURFACE_RAISED,
                    text_color=TEXT,
                ).grid(row=row, column=column, padx=2, pady=2)

    def _change_month(self, delta: int) -> None:
        self._displayed_year, self._displayed_month = shift_month(
            self._displayed_year, self._displayed_month, delta
        )
        self._render_calendar()

    def _select_day(self, day: int) -> None:
        self._selected_date = date(self._displayed_year, self._displayed_month, day)
        self._on_select(format_date(self._displayed_year, self._displayed_month, day))
        self._close()

    def _close(self) -> None:
        self._on_close()
        self.destroy()
