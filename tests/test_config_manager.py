import json
from pathlib import Path
import tempfile
import unittest

from config_manager import DEFAULT_CONFIG, load_config, save_config


class ConfigManagerTests(unittest.TestCase):
    def test_saves_and_loads_valid_configuration(self) -> None:
        config = {
            "event_name": "테스트 공연",
            "url": "https://ticket.nol.com/places/12345",
            "date": "2026-11-01",
            "time": "14:03:09",
            "mode": "local_test",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            save_config(path, config)

            self.assertEqual(load_config(path), config)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), config)

    def test_loads_legacy_configuration_as_manual_nol_mode(self) -> None:
        legacy_config = {
            "event_name": "기존 공연",
            "url": "https://ticket.nol.com/places/12345",
            "date": "2026-11-01",
            "time": "14:03:09",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(legacy_config), encoding="utf-8")

            self.assertEqual(load_config(path), {**legacy_config, "mode": "nol_manual"})

    def test_returns_defaults_for_corrupt_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text("{not valid json", encoding="utf-8")

            self.assertEqual(load_config(path), DEFAULT_CONFIG)

    def test_rejects_configuration_with_invalid_url(self) -> None:
        config = {
            "event_name": "테스트 공연",
            "url": "https://example.com/places/12345",
            "date": "2026-11-01",
            "time": "14:03:09",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"

            with self.assertRaisesRegex(ValueError, "NOL Ticket"):
                save_config(path, config)

    def test_rejects_non_string_required_values(self) -> None:
        config = {
            "event_name": None,
            "url": "https://ticket.nol.com/places/12345",
            "date": "2026-11-01",
            "time": "14:03:09",
        }
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "문자열"):
                save_config(Path(directory) / "config.json", config)


if __name__ == "__main__":
    unittest.main()
