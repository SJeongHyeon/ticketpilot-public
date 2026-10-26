"""Windows GUI for a personal NOL Ticket sale-time reminder."""

from datetime import date, datetime
from pathlib import Path
import webbrowser
import tkinter as tk
import tkinter.messagebox as messagebox

import customtkinter as ctk

from browser_launcher import open_browser_url
from config_manager import load_config, save_config
from date_time_picker import (
    CalendarPopup,
    HOUR_VALUES,
    MINUTE_SECOND_VALUES,
    format_time,
    split_time,
)
from local_test_server import LocalTestServer
from runtime_paths import resource_path, user_data_path
from scheduler import ScheduleController
from validators import KST, parse_kst_datetime, validate_nol_ticket_url


CONFIG_PATH = user_data_path("config.json")

BACKGROUND = "#111111"
SURFACE = "#1B1B1B"
SURFACE_RAISED = "#242424"
FIELD = "#2A2A2A"
TEXT = "#F5F5F5"
MUTED_TEXT = "#A3A3A3"
ACCENT = "#3B82F6"
ACCENT_HOVER = "#2563EB"
STOP = "#8F3232"
STOP_HOVER = "#722626"


def logo_asset_path() -> Path:
    """Return the bundled TicketPilot logo path without touching app settings."""
    return resource_path("assets", "logo.png")


def load_logo_image(path: Path) -> tk.PhotoImage | None:
    """Load a compact Tk logo image, falling back cleanly when unavailable."""
    if not path.is_file():
        return None
    try:
        return tk.PhotoImage(file=str(path)).subsample(14, 14)
    except (tk.TclError, OSError):
        return None


class TicketHelperApp(ctk.CTk):
    """A non-blocking desktop helper; it never automates the ticket site."""

    def __init__(self) -> None:
        super().__init__()
        self.title("TicketPilot | 예매 시작 알림")
        self.geometry("860x780")
        self.minsize(720, 660)
        self.configure(fg_color=BACKGROUND)

        self.controller: ScheduleController | None = None
        self._after_id: str | None = None
        self._result_after_id: str | None = None
        self._browser_opened = False
        self._click_result_logged = False
        self._current_mode = "nol_manual"
        self.local_test_server = LocalTestServer()
        self.mode_var = ctk.StringVar(value="nol_manual")
        self.date_var = ctk.StringVar(value=datetime.now(KST).date().isoformat())
        self.hour_var = ctk.StringVar(value="00")
        self.minute_var = ctk.StringVar(value="00")
        self.second_var = ctk.StringVar(value="00")
        self._calendar_popup: CalendarPopup | None = None
        self._build_widgets()
        self._load_saved_config()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_widgets(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=32, pady=(24, 12), sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        self._logo_image = load_logo_image(logo_asset_path())
        if self._logo_image:
            ctk.CTkLabel(header, text="", image=self._logo_image).grid(
                row=0, column=0, rowspan=2, padx=(0, 14), sticky="w"
            )
        ctk.CTkLabel(
            header,
            text="TicketPilot",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=TEXT,
        ).grid(row=0, column=1, sticky="sw")
        ctk.CTkLabel(
            header,
            text="개인 예매 시작 알림",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=MUTED_TEXT,
        ).grid(row=1, column=1, pady=(2, 0), sticky="nw")

        status = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=18)
        status.grid(row=1, column=0, padx=32, pady=(0, 16), sticky="ew")
        status.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            status,
            text="예매 시작까지",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=ACCENT,
        ).grid(row=0, column=0, pady=(22, 0))
        self.countdown_label = ctk.CTkLabel(
            status,
            text="--:--:--",
            font=ctk.CTkFont(family="Consolas", size=62, weight="bold"),
            text_color=TEXT,
        )
        self.countdown_label.grid(row=1, column=0, pady=(4, 2))
        self.status_label = ctk.CTkLabel(
            status,
            text="설정을 저장한 뒤 시작하세요.",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=MUTED_TEXT,
        )
        self.status_label.grid(row=2, column=0, padx=20, pady=(2, 22))

        form = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16)
        form.grid(row=2, column=0, padx=32, pady=(0, 16), sticky="ew")
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            form,
            text="예매 정보",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=TEXT,
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(18, 6), sticky="w")

        self.event_name_entry = self._add_entry(form, 1, "공연명", "예: 2026 콘서트")
        self.url_entry = self._add_entry(
            form, 2, "NOL Ticket URL", "https://nol.yanolja.com/ticket/..."
        )

        schedule_frame = ctk.CTkFrame(form, fg_color="transparent")
        schedule_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=(6, 8), sticky="ew")
        schedule_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(
            schedule_frame, text="예매 시작 날짜 (KST)", text_color=MUTED_TEXT
        ).grid(row=0, column=0, padx=(0, 6), pady=(0, 5), sticky="w")
        ctk.CTkLabel(
            schedule_frame, text="예매 시작 시각 (KST)", text_color=MUTED_TEXT
        ).grid(row=0, column=1, padx=(6, 0), pady=(0, 5), sticky="w")
        self.date_button = ctk.CTkButton(
            schedule_frame,
            textvariable=self.date_var,
            command=self.open_calendar,
            fg_color=FIELD,
            border_color="#3A3A3A",
            border_width=1,
            text_color=TEXT,
            height=38,
            anchor="w",
            hover_color=SURFACE_RAISED,
        )
        self.date_button.grid(row=1, column=0, padx=(0, 6), sticky="ew")
        time_picker = ctk.CTkFrame(schedule_frame, fg_color="transparent")
        time_picker.grid(row=1, column=1, padx=(6, 0), sticky="ew")
        time_picker.grid_columnconfigure((0, 1, 2), weight=1)
        self.hour_menu = self._add_time_menu(time_picker, 0, self.hour_var, HOUR_VALUES, "시")
        self.minute_menu = self._add_time_menu(
            time_picker, 1, self.minute_var, MINUTE_SECOND_VALUES, "분"
        )
        self.second_menu = self._add_time_menu(
            time_picker, 2, self.second_var, MINUTE_SECOND_VALUES, "초"
        )

        mode_frame = ctk.CTkFrame(form, fg_color=SURFACE_RAISED, corner_radius=10)
        mode_frame.grid(row=4, column=0, columnspan=2, padx=20, pady=(8, 20), sticky="ew")
        ctk.CTkLabel(mode_frame, text="실행 방식", text_color=TEXT).pack(side="left", padx=(14, 8), pady=10)
        ctk.CTkRadioButton(
            mode_frame,
            text="NOL 알림(직접 클릭)",
            variable=self.mode_var,
            value="nol_manual",
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT,
        ).pack(side="left", padx=8)
        ctk.CTkRadioButton(
            mode_frame,
            text="로컬 테스트 자동 클릭",
            variable=self.mode_var,
            value="local_test",
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT,
        ).pack(side="left", padx=8)

        button_frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16)
        button_frame.grid(row=3, column=0, padx=32, pady=(0, 16), sticky="ew")
        button_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkLabel(
            button_frame,
            text="제어",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=TEXT,
        ).grid(row=0, column=0, columnspan=4, padx=20, pady=(16, 6), sticky="w")
        ctk.CTkButton(
            button_frame,
            text="설정 저장",
            command=self.save_settings,
            fg_color="transparent",
            border_width=1,
            border_color="#4A4A4A",
            text_color=TEXT,
            hover_color=SURFACE_RAISED,
        ).grid(
            row=1, column=0, padx=(20, 5), pady=(0, 18), sticky="ew"
        )
        self.start_button = ctk.CTkButton(
            button_frame,
            text="시작",
            command=self.start_schedule,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT,
        )
        self.start_button.grid(row=1, column=1, padx=5, pady=(0, 18), sticky="ew")
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="중지",
            command=self.stop_schedule,
            fg_color=STOP,
            hover_color=STOP_HOVER,
            text_color=TEXT,
            state="disabled",
        )
        self.stop_button.grid(row=1, column=2, padx=5, pady=(0, 18), sticky="ew")
        ctk.CTkButton(
            button_frame,
            text="페이지 미리 열기",
            command=self.open_prepared_page,
            fg_color="transparent",
            border_width=1,
            border_color="#4A4A4A",
            text_color=TEXT,
            hover_color=SURFACE_RAISED,
        ).grid(
            row=1, column=3, padx=(5, 20), pady=(0, 18), sticky="ew"
        )

        log_frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16)
        log_frame.grid(row=4, column=0, padx=32, pady=(0, 28), sticky="nsew")
        ctk.CTkLabel(
            log_frame,
            text="실행 로그",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=TEXT,
            anchor="w",
        ).pack(
            padx=20, pady=(16, 6), fill="x"
        )
        self.log_box = ctk.CTkTextbox(
            log_frame,
            height=160,
            fg_color=FIELD,
            text_color=TEXT,
            border_width=0,
        )
        self.log_box.pack(padx=20, pady=(0, 20), fill="both", expand=True)
        self.log_box.configure(state="disabled")

    @staticmethod
    def _add_entry(parent: ctk.CTkFrame, row: int, label: str, placeholder: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, text_color=MUTED_TEXT).grid(
            row=row, column=0, padx=(20, 10), pady=8, sticky="w"
        )
        entry = ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            fg_color=FIELD,
            border_color="#3A3A3A",
            text_color=TEXT,
            height=38,
        )
        entry.grid(row=row, column=1, padx=(0, 20), pady=8, sticky="ew")
        return entry

    @staticmethod
    def _add_time_menu(
        parent: ctk.CTkFrame,
        column: int,
        variable: ctk.StringVar,
        values: tuple[str, ...],
        suffix: str,
    ) -> ctk.CTkOptionMenu:
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=0, column=column, padx=2, sticky="ew")
        container.grid_columnconfigure(0, weight=1)
        menu = ctk.CTkOptionMenu(
            container,
            variable=variable,
            values=list(values),
            fg_color=FIELD,
            button_color="#3A3A3A",
            button_hover_color="#4A4A4A",
            text_color=TEXT,
            dropdown_fg_color=SURFACE_RAISED,
            dropdown_hover_color="#3A3A3A",
            height=38,
            width=76,
        )
        menu.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(container, text=suffix, text_color=MUTED_TEXT).grid(
            row=1, column=0, pady=(2, 0)
        )
        return menu

    def _load_saved_config(self) -> None:
        config = load_config(CONFIG_PATH)
        for field, entry in (
            ("event_name", self.event_name_entry),
            ("url", self.url_entry),
        ):
            entry.insert(0, config[field])
        if config["date"]:
            self.date_var.set(config["date"])
        if config["time"]:
            hour, minute, second = split_time(config["time"])
            self.hour_var.set(hour)
            self.minute_var.set(minute)
            self.second_var.set(second)
        self.mode_var.set(config["mode"])
        if config["event_name"]:
            self._log("저장된 설정을 불러왔습니다.")

    def _collect_config(self) -> dict[str, str]:
        config = {
            "event_name": self.event_name_entry.get().strip(),
            "url": self.url_entry.get().strip(),
            "date": self.date_var.get(),
            "time": format_time(
                self.hour_var.get(), self.minute_var.get(), self.second_var.get()
            ),
            "mode": self.mode_var.get(),
        }
        if not config["event_name"]:
            raise ValueError("공연명을 입력해 주세요.")
        config["url"] = validate_nol_ticket_url(config["url"])
        parse_kst_datetime(config["date"], config["time"])
        return config

    def open_calendar(self) -> None:
        """Open one date-picker popup, raising it when it already exists."""
        if self._calendar_popup and self._calendar_popup.winfo_exists():
            self._calendar_popup.lift()
            self._calendar_popup.focus_force()
            return
        selected_date = date.fromisoformat(self.date_var.get())
        self._calendar_popup = CalendarPopup(
            self, selected_date, self._set_selected_date, self._on_calendar_closed
        )

    def _set_selected_date(self, value: str) -> None:
        self.date_var.set(value)

    def _on_calendar_closed(self) -> None:
        self._calendar_popup = None

    def save_settings(self) -> None:
        try:
            config = self._collect_config()
            save_config(CONFIG_PATH, config)
        except (ValueError, OSError) as error:
            self._show_error(str(error))
            return
        self._log("설정을 config.json에 저장했습니다.")
        self.status_label.configure(text="설정이 저장되었습니다.")

    def start_schedule(self) -> None:
        try:
            config = self._collect_config()
            target = parse_kst_datetime(config["date"], config["time"])
            if target <= datetime.now(KST):
                raise ValueError("예매 시작 시각은 현재 한국 시간보다 미래여야 합니다.")
            save_config(CONFIG_PATH, config)
            if config["mode"] == "local_test":
                self.local_test_server.start()
                self.local_test_server.schedule(int(target.timestamp() * 1000))
            else:
                self.local_test_server.cancel()
        except (ValueError, OSError) as error:
            self._show_error(str(error))
            return

        self._cancel_tick()
        self._cancel_result_poll()
        self._browser_opened = False
        self._click_result_logged = False
        self._current_mode = config["mode"]
        self.controller = ScheduleController(target, config["url"], self._notify, self._on_target)
        self.controller.start()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        mode_text = "로컬 테스트 클릭" if config["mode"] == "local_test" else "NOL 직접 클릭 알림"
        self.status_label.configure(text=f"‘{config['event_name']}’ {mode_text}을 감시 중입니다.")
        self._log(f"감시 시작: {target.strftime('%Y-%m-%d %H:%M:%S KST')}")
        self._tick()

    def stop_schedule(self) -> None:
        self._cancel_tick()
        self._cancel_result_poll()
        self.local_test_server.cancel()
        if self.controller:
            self.controller.stop()
        self.controller = None
        self.countdown_label.configure(text="--:--:--")
        self.status_label.configure(text="감시를 중지했습니다.")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self._log("감시를 중지했습니다.")

    def _tick(self) -> None:
        self._after_id = None
        if not self.controller:
            return
        remaining = self.controller.tick(datetime.now(KST))
        self.countdown_label.configure(text=remaining)
        if self.controller.is_running:
            self._after_id = self.after(250, self._tick)
        else:
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            if self._current_mode == "local_test":
                self.status_label.configure(text="로컬 테스트 버튼 클릭 결과를 확인 중입니다.")
                self._poll_local_result()
            else:
                self._log("정각 알림 처리 완료: NOL 페이지는 사용자가 직접 클릭합니다.")

    def _notify(self, message: str) -> None:
        self.bell()
        self.status_label.configure(text=message)
        self._log(message)

    def open_prepared_page(self) -> None:
        """Open either the saved NOL page or the fixed loopback test page."""
        try:
            config = self._collect_config()
            if config["mode"] == "local_test":
                url = self.local_test_server.start()
                label = "로컬 테스트 페이지"
            else:
                url = config["url"]
                label = "NOL 페이지"
        except (ValueError, OSError) as error:
            self._show_error(str(error))
            return
        self._browser_opened = open_browser_url(url, webbrowser.open)
        if self._browser_opened:
            self._log(f"기본 브라우저로 {label}를 열었습니다. 정각 전까지 페이지를 유지하세요.")
            self.status_label.configure(text=f"{label}를 미리 열었습니다.")
        else:
            self._log(f"오류: {label}를 열지 못했습니다.")

    def _on_target(self, _url: str) -> None:
        """Handle target time without ever automating the saved NOL URL."""
        if self._current_mode == "local_test":
            self._notify("정각입니다. 로컬 테스트 페이지의 버튼 클릭 결과를 확인합니다.")
            self._poll_local_result()
            return
        self._notify("예매 시작 시각입니다. 미리 열린 NOL 페이지에서 직접 클릭하세요.")

    def _poll_local_result(self) -> None:
        if self._current_mode != "local_test" or self._click_result_logged:
            return
        result = self.local_test_server.get_result()
        actual = result["actual_epoch_ms"]
        if actual is not None:
            self._click_result_logged = True
            scheduled = result["scheduled_epoch_ms"]
            delta = result["delta_ms"]
            self._log(f"로컬 클릭 기록: 예정 {scheduled}ms / 실제 {actual}ms / 차이 {delta}ms")
            self.status_label.configure(text=f"로컬 테스트 버튼이 1회 클릭되었습니다. 차이: {delta}ms")
            return
        if result["active"]:
            if not result["page_present"]:
                self.local_test_server.cancel()
                self._notify("로컬 테스트 페이지가 열려 있지 않아 예약을 취소했습니다.")
                return
            self._result_after_id = self.after(50, self._poll_local_result)
        elif result["claimed"] and result["page_present"]:
            self._result_after_id = self.after(50, self._poll_local_result)

    def _cancel_result_poll(self) -> None:
        if self._result_after_id:
            self.after_cancel(self._result_after_id)
            self._result_after_id = None

    def _cancel_tick(self) -> None:
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _show_error(self, message: str) -> None:
        self._log(f"오류: {message}")
        messagebox.showerror("입력 오류", message, parent=self)

    def _log(self, message: str) -> None:
        timestamp = datetime.now(KST).strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{timestamp}] {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _on_close(self) -> None:
        self._cancel_tick()
        if self.controller:
            self.controller.stop()
        self.local_test_server.cancel()
        self.local_test_server.stop()
        self.destroy()


def run() -> None:
    """Configure CustomTkinter and start the desktop application."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    TicketHelperApp().mainloop()


if __name__ == "__main__":
    run()
