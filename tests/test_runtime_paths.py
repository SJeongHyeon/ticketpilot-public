from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import runtime_paths


class RuntimePathTests(unittest.TestCase):
    def test_resource_path_uses_project_directory_during_development(self) -> None:
        expected = Path(runtime_paths.__file__).resolve().parent / "assets" / "logo.png"

        self.assertEqual(runtime_paths.resource_path("assets", "logo.png"), expected)

    def test_resource_path_uses_pyinstaller_bundle_when_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle_root = Path(directory)
            with patch.object(sys, "_MEIPASS", str(bundle_root), create=True):
                self.assertEqual(
                    runtime_paths.resource_path("assets", "logo.png"),
                    bundle_root / "assets" / "logo.png",
                )

    def test_user_data_path_uses_local_app_data_ticketpilot_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict("os.environ", {"LOCALAPPDATA": directory}, clear=True):
                self.assertEqual(
                    runtime_paths.user_data_path("config.json"),
                    Path(directory) / "TicketPilot" / "config.json",
                )


if __name__ == "__main__":
    unittest.main()
