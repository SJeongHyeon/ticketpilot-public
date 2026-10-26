from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from pathlib import Path

from PIL import Image

import app
from app import TicketHelperApp, load_logo_image, logo_asset_path


class TargetHandlingTests(unittest.TestCase):
    def test_logo_uses_blue_symbol_with_transparent_antialiased_edges(self) -> None:
        for asset in (logo_asset_path(), logo_asset_path().with_name("app.ico")):
            with Image.open(asset) as image:
                rgba = image.convert("RGBA")
                pixels = list(rgba.get_flattened_data())

            visible = [pixel for pixel in pixels if pixel[3] > 0]
            self.assertTrue(visible, asset)
            self.assertTrue(any(pixel[3] == 0 for pixel in pixels), asset)
            self.assertTrue(any(0 < pixel[3] < 255 for pixel in pixels), asset)
            self.assertTrue(
                all(pixel[:3] == (59, 130, 246) for pixel in visible), asset
            )

    def test_logo_asset_path_points_to_project_asset(self) -> None:
        self.assertEqual(
            logo_asset_path(),
            Path(app.__file__).with_name("assets") / "logo.png",
        )

    def test_logo_loader_returns_none_when_asset_is_missing(self) -> None:
        self.assertIsNone(load_logo_image(Path("missing-logo.png")))

    @patch("app.tk.PhotoImage", side_effect=app.tk.TclError("unreadable logo"))
    def test_logo_loader_returns_none_when_image_cannot_be_read(self, _photo_image: Mock) -> None:
        self.assertIsNone(load_logo_image(logo_asset_path()))

    def test_nol_target_only_notifies_user_without_automating_the_url(self) -> None:
        notifications: list[str] = []
        fake_app = SimpleNamespace(
            _current_mode="nol_manual",
            _notify=notifications.append,
            _poll_local_result=Mock(),
        )

        TicketHelperApp._on_target(fake_app, "https://ticket.nol.com/places/12345")

        self.assertEqual(notifications, ["예매 시작 시각입니다. 미리 열린 NOL 페이지에서 직접 클릭하세요."])
        fake_app._poll_local_result.assert_not_called()

    def test_local_target_checks_for_the_loopback_click_result(self) -> None:
        fake_app = SimpleNamespace(
            _current_mode="local_test",
            _notify=Mock(),
            _poll_local_result=Mock(),
        )

        TicketHelperApp._on_target(fake_app, "https://ticket.nol.com/places/12345")

        fake_app._poll_local_result.assert_called_once_with()

    def test_local_result_poll_cancels_when_the_test_page_is_not_present(self) -> None:
        server = SimpleNamespace(
            get_result=Mock(
                return_value={
                    "scheduled_epoch_ms": 1_800_000_000_000,
                    "actual_epoch_ms": None,
                    "delta_ms": None,
                    "active": True,
                    "claimed": False,
                    "page_present": False,
                }
            ),
            cancel=Mock(),
        )
        fake_app = SimpleNamespace(
            _current_mode="local_test",
            _click_result_logged=False,
            local_test_server=server,
            _notify=Mock(),
            _log=Mock(),
            after=Mock(),
            _poll_local_result=Mock(),
        )

        TicketHelperApp._poll_local_result(fake_app)

        server.cancel.assert_called_once_with()
        fake_app._notify.assert_called_once_with("로컬 테스트 페이지가 열려 있지 않아 예약을 취소했습니다.")
        fake_app.after.assert_not_called()


class SchedulePickerIntegrationTests(unittest.TestCase):
    def test_collect_config_formats_picker_values_for_existing_validation(self) -> None:
        fake_app = SimpleNamespace(
            event_name_entry=SimpleNamespace(get=lambda: "테스트 공연"),
            url_entry=SimpleNamespace(get=lambda: "https://ticket.nol.com/places/12345"),
            date_var=SimpleNamespace(get=lambda: "2027-02-28"),
            hour_var=SimpleNamespace(get=lambda: "23"),
            minute_var=SimpleNamespace(get=lambda: "59"),
            second_var=SimpleNamespace(get=lambda: "59"),
            mode_var=SimpleNamespace(get=lambda: "local_test"),
        )

        self.assertEqual(
            TicketHelperApp._collect_config(fake_app),
            {
                "event_name": "테스트 공연",
                "url": "https://ticket.nol.com/places/12345",
                "date": "2027-02-28",
                "time": "23:59:59",
                "mode": "local_test",
            },
        )

    @patch("app.load_config")
    def test_saved_picker_values_restore_into_date_and_time_controls(self, load_config: Mock) -> None:
        load_config.return_value = {
            "event_name": "저장 공연",
            "url": "https://ticket.nol.com/places/12345",
            "date": "2028-02-29",
            "time": "00:00:00",
            "mode": "nol_manual",
        }
        fake_app = SimpleNamespace(
            event_name_entry=Mock(),
            url_entry=Mock(),
            date_var=Mock(),
            hour_var=Mock(),
            minute_var=Mock(),
            second_var=Mock(),
            mode_var=Mock(),
            _log=Mock(),
        )

        TicketHelperApp._load_saved_config(fake_app)

        fake_app.date_var.set.assert_called_once_with("2028-02-29")
        fake_app.hour_var.set.assert_called_once_with("00")
        fake_app.minute_var.set.assert_called_once_with("00")
        fake_app.second_var.set.assert_called_once_with("00")
        fake_app.mode_var.set.assert_called_once_with("nol_manual")

    def test_open_calendar_raises_existing_popup_without_creating_another(self) -> None:
        popup = Mock()
        popup.winfo_exists.return_value = True
        fake_app = SimpleNamespace(_calendar_popup=popup)

        TicketHelperApp.open_calendar(fake_app)

        popup.lift.assert_called_once_with()
        popup.focus_force.assert_called_once_with()

    def test_calendar_close_and_selection_update_picker_state(self) -> None:
        date_var = Mock()
        fake_app = SimpleNamespace(date_var=date_var, _calendar_popup=Mock())

        TicketHelperApp._set_selected_date(fake_app, "2027-03-01")
        TicketHelperApp._on_calendar_closed(fake_app)

        date_var.set.assert_called_once_with("2027-03-01")
        self.assertIsNone(fake_app._calendar_popup)

    def test_start_rejects_a_past_picker_datetime_with_existing_policy(self) -> None:
        fake_app = SimpleNamespace(
            _collect_config=Mock(
                return_value={
                    "event_name": "지난 공연",
                    "url": "https://ticket.nol.com/places/12345",
                    "date": "2000-01-01",
                    "time": "00:00:00",
                    "mode": "nol_manual",
                }
            ),
            _show_error=Mock(),
        )

        TicketHelperApp.start_schedule(fake_app)

        fake_app._show_error.assert_called_once_with("예매 시작 시각은 현재 한국 시간보다 미래여야 합니다.")


if __name__ == "__main__":
    unittest.main()
