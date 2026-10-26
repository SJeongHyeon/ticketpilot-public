"""Loopback-only test page for verifying a scheduled browser button click."""

from __future__ import annotations

import json
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from collections.abc import Callable
from typing import Any


class LocalTestServer:
    """Serve one fixed test page and retain one scheduled click result."""

    def __init__(self, clock_ms: Callable[[], int] | None = None) -> None:
        self._lock = Lock()
        self._server: ThreadingHTTPServer | None = None
        self._thread: Thread | None = None
        self._scheduled_epoch_ms: int | None = None
        self._actual_epoch_ms: int | None = None
        self._active = False
        self._claimed = False
        self._last_heartbeat_epoch_ms: int | None = None
        self._clock_ms = clock_ms or (lambda: int(time.time() * 1000))

    def start(self) -> str:
        """Start a loopback HTTP server once and return its fixed test URL."""
        if self._server is None:
            manager = self

            class Handler(BaseHTTPRequestHandler):
                def do_GET(self) -> None:  # noqa: N802
                    if self.path == "/local-test":
                        self._send_html(manager._page_html())
                    elif self.path == "/api/schedule":
                        self._send_json(manager.get_result())
                    else:
                        self.send_error(HTTPStatus.NOT_FOUND)

                def do_POST(self) -> None:  # noqa: N802
                    if self.path == "/api/heartbeat":
                        manager.heartbeat()
                        self._send_json({"ok": True})
                        return
                    if self.path == "/api/claim-click":
                        self._send_json({"accepted": manager.claim_click()})
                        return
                    if self.path != "/api/click":
                        self.send_error(HTTPStatus.NOT_FOUND)
                        return
                    try:
                        size = int(self.headers.get("Content-Length", "0"))
                        payload = json.loads(self.rfile.read(size))
                        accepted = manager.record_click(int(payload["actual_epoch_ms"]))
                    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                        self.send_error(HTTPStatus.BAD_REQUEST)
                        return
                    self._send_json({"accepted": accepted})

                def _send_html(self, content: str) -> None:
                    encoded = content.encode("utf-8")
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)

                def _send_json(self, content: dict[str, Any]) -> None:
                    encoded = json.dumps(content).encode("utf-8")
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)

                def log_message(self, _format: str, *_args: object) -> None:
                    return

            self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            self._thread = Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
        return f"http://127.0.0.1:{self._server.server_port}/local-test"

    def stop(self) -> None:
        """Stop the loopback server if it was started."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            if self._thread is not None:
                self._thread.join(timeout=1)
        self._server = None
        self._thread = None

    def schedule(self, target_epoch_ms: int) -> None:
        """Replace any prior result with one active local-page reservation."""
        with self._lock:
            self._scheduled_epoch_ms = target_epoch_ms
            self._actual_epoch_ms = None
            self._active = True
            self._claimed = False

    def cancel(self) -> None:
        """Make an outstanding local-page reservation inert."""
        with self._lock:
            self._active = False

    def record_click(self, actual_epoch_ms: int) -> bool:
        """Record the first click from the fixed local page only."""
        with self._lock:
            if not self._claimed or self._actual_epoch_ms is not None:
                return False
            self._actual_epoch_ms = actual_epoch_ms
            return True

    def claim_click(self) -> bool:
        """Atomically grant exactly one page permission to dispatch its click."""
        with self._lock:
            if not self._active or self._claimed or self._actual_epoch_ms is not None:
                return False
            self._claimed = True
            self._active = False
            return True

    def heartbeat(self) -> None:
        """Record that at least one fixed local test page is still open."""
        with self._lock:
            self._last_heartbeat_epoch_ms = self._clock_ms()

    def get_result(self) -> dict[str, int | bool | None]:
        """Return the scheduled time, first actual time, and millisecond delta."""
        with self._lock:
            delta = None
            if self._scheduled_epoch_ms is not None and self._actual_epoch_ms is not None:
                delta = self._actual_epoch_ms - self._scheduled_epoch_ms
            return {
                "scheduled_epoch_ms": self._scheduled_epoch_ms,
                "actual_epoch_ms": self._actual_epoch_ms,
                "delta_ms": delta,
                "active": self._active,
                "claimed": self._claimed,
                "page_present": (
                    self._last_heartbeat_epoch_ms is not None
                    and self._clock_ms() - self._last_heartbeat_epoch_ms <= 1_500
                ),
            }

    @staticmethod
    def _page_html() -> str:
        return """<!doctype html>
<html lang="ko"><meta charset="utf-8"><title>로컬 예매 클릭 테스트</title>
<body><h1>로컬 예매 클릭 테스트</h1><p id="status">예약을 기다리는 중입니다.</p>
<button id="booking-button" type="button">예매하기</button>
<script>
(() => {
  let timer = null, target = null, fired = false;
  const status = document.getElementById('status');
  const button = document.getElementById('booking-button');
  button.addEventListener('click', () => { status.textContent = '버튼 클릭 이벤트가 실행되었습니다.'; });
  async function refresh() {
    await fetch('/api/heartbeat', {method: 'POST'});
    const state = await fetch('/api/schedule').then(r => r.json());
    if (!state.active || state.scheduled_epoch_ms === null) {
      clearTimeout(timer); timer = null; target = null; fired = false;
      return;
    }
    if (target !== state.scheduled_epoch_ms) {
      clearTimeout(timer); target = state.scheduled_epoch_ms; fired = false;
      timer = setTimeout(clickOnce, Math.max(0, target - Date.now()));
      status.textContent = '예약 시각: ' + new Date(target).toLocaleTimeString();
    }
  }
  async function clickOnce() {
    if (fired) return;
    fired = true;
    const claim = await fetch('/api/claim-click', {method: 'POST'}).then(r => r.json());
    if (!claim.accepted) return;
    button.click();
    await fetch('/api/click', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({actual_epoch_ms: Date.now()})});
  }
  setInterval(() => refresh().catch(() => {}), 100);
  refresh().catch(() => {});
})();
</script></body></html>"""
