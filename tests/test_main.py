import sys
import types
import unittest
from tkinter import TclError
from unittest.mock import Mock, patch


class MainEntrypointTests(unittest.TestCase):
    def test_main_delegates_to_the_application_runner(self) -> None:
        import main

        run = Mock()
        fake_app = types.SimpleNamespace(run=run)
        with patch.dict(sys.modules, {"app": fake_app}):
            main.main()

        run.assert_called_once_with()

    def test_main_exits_with_setup_message_when_tk_cannot_start(self) -> None:
        import main

        fake_app = types.SimpleNamespace(run=Mock(side_effect=TclError("missing init.tcl")))
        with patch.dict(sys.modules, {"app": fake_app}):
            with self.assertRaisesRegex(SystemExit, "Tcl/Tk"):
                main.main()


if __name__ == "__main__":
    unittest.main()
