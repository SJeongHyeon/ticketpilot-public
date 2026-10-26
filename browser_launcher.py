"""Small, testable boundary around opening the operating system browser."""

from collections.abc import Callable


def open_browser_url(url: str, opener: Callable[[str, int], bool]) -> bool:
    """Ask the browser opener to open a new tab and return its success state."""
    try:
        return bool(opener(url, 2))
    except Exception:
        return False
