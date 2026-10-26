import json
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from local_test_server import LocalTestServer


class LocalTestServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = LocalTestServer()

    def tearDown(self) -> None:
        self.server.stop()

    def test_start_returns_loopback_local_test_url(self) -> None:
        url = self.server.start()

        self.assertRegex(url, r"^http://127\.0\.0\.1:\d+/local-test$")

    def test_records_only_the_first_click_for_an_active_reservation(self) -> None:
        self.server.schedule(1_800_000_000_000)

        self.assertTrue(self.server.claim_click())
        self.assertFalse(self.server.claim_click())
        self.assertTrue(self.server.record_click(1_800_000_000_012))
        self.assertFalse(self.server.record_click(1_800_000_000_024))
        self.assertEqual(
            self.server.get_result(),
            {
                "scheduled_epoch_ms": 1_800_000_000_000,
                "actual_epoch_ms": 1_800_000_000_012,
                "delta_ms": 12,
                "active": False,
                "claimed": True,
                "page_present": False,
            },
        )

    def test_cancel_prevents_a_click_from_being_recorded(self) -> None:
        self.server.schedule(1_800_000_000_000)
        self.server.cancel()

        self.assertFalse(self.server.record_click(1_800_000_000_012))
        self.assertIsNone(self.server.get_result()["actual_epoch_ms"])

    def test_heartbeat_expires_when_the_test_page_is_closed(self) -> None:
        now = [1_800_000_000_000]
        server = LocalTestServer(clock_ms=lambda: now[0])
        self.addCleanup(server.stop)
        server.schedule(now[0] + 10_000)

        self.assertFalse(server.get_result()["page_present"])
        server.heartbeat()
        self.assertTrue(server.get_result()["page_present"])
        now[0] += 1_501
        self.assertFalse(server.get_result()["page_present"])

    def test_loopback_api_allows_one_claim_and_rejects_unknown_paths(self) -> None:
        page_url = self.server.start()
        api_base = page_url.removesuffix("/local-test")
        self.server.schedule(1_800_000_000_000)

        with self.assertRaises(HTTPError) as error:
            urlopen(f"{api_base}/not-a-route")
        self.assertEqual(error.exception.code, 404)

        self.assertTrue(self._post_json(f"{api_base}/api/claim-click", {})["accepted"])
        self.assertFalse(self._post_json(f"{api_base}/api/claim-click", {})["accepted"])
        self.assertTrue(
            self._post_json(
                f"{api_base}/api/click", {"actual_epoch_ms": 1_800_000_000_012}
            )["accepted"]
        )
        self.assertEqual(self.server.get_result()["actual_epoch_ms"], 1_800_000_000_012)

    @staticmethod
    def _post_json(url: str, payload: dict[str, int]) -> dict[str, bool]:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            return json.loads(response.read())


if __name__ == "__main__":
    unittest.main()
