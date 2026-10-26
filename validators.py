"""Validation helpers for the NOL Ticket countdown application."""

from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")
_ALLOWED_DOMAINS = ("ticket.nol.com", "nol.yanolja.com")


def validate_nol_ticket_url(url: str) -> str:
    """Return a normalized NOL Ticket event URL or raise ValueError."""
    normalized = url.strip()
    parsed = urlparse(normalized)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL은 http 또는 https로 시작해야 합니다.")
    if not parsed.hostname or not any(
        parsed.hostname == domain or parsed.hostname.endswith(f".{domain}")
        for domain in _ALLOWED_DOMAINS
    ):
        raise ValueError("NOL Ticket 허용 도메인 URL만 사용할 수 있습니다.")
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("URL의 포트 형식이 올바르지 않습니다.") from error
    if "@" in parsed.netloc or port is not None:
        raise ValueError("URL에 사용자 정보나 포트를 포함할 수 없습니다.")
    if parsed.fragment:
        raise ValueError("URL에 fragment(#...)를 포함할 수 없습니다.")
    if not parsed.path or parsed.path == "/":
        raise ValueError("공연 또는 스포츠 상세 페이지 URL을 입력해 주세요.")

    return normalized


def parse_kst_datetime(date_text: str, time_text: str) -> datetime:
    """Parse separate date/time inputs as a timezone-aware KST datetime."""
    try:
        parsed = datetime.strptime(
            f"{date_text.strip()} {time_text.strip()}", "%Y-%m-%d %H:%M:%S"
        )
    except ValueError as error:
        raise ValueError("날짜는 YYYY-MM-DD, 시각은 HH:MM:SS 형식으로 입력해 주세요.") from error
    return parsed.replace(tzinfo=KST)
