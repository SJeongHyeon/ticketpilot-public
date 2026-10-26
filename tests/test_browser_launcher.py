import unittest

from browser_launcher import open_browser_url


class BrowserLauncherTests(unittest.TestCase):
    def test_reports_success_only_when_browser_accepts_url(self) -> None:
        self.assertTrue(open_browser_url("https://ticket.nol.com/places/12345", lambda *_: True))
        self.assertFalse(open_browser_url("https://ticket.nol.com/places/12345", lambda *_: False))

    def test_converts_browser_exception_to_failure(self) -> None:
        def broken_opener(_url: str, _new: int) -> bool:
            raise OSError("browser unavailable")

        self.assertFalse(open_browser_url("https://ticket.nol.com/places/12345", broken_opener))


if __name__ == "__main__":
    unittest.main()
