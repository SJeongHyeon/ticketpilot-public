"""JSON configuration persistence for the NOL Ticket helper."""

import json
import os
from pathlib import Path
from typing import Mapping

from validators import parse_kst_datetime, validate_nol_ticket_url


DEFAULT_CONFIG: dict[str, str] = {
    "event_name": "",
    "url": "",
    "date": "",
    "time": "",
    "mode": "nol_manual",
}
_REQUIRED_FIELDS = ("event_name", "url", "date", "time")
_VALID_MODES = {"nol_manual", "local_test"}


def _normalize_config(config: Mapping[str, object]) -> dict[str, str]:
    """Validate required user settings and return a stripped copy."""
    if any(not isinstance(config.get(field), str) for field in _REQUIRED_FIELDS):
        raise ValueError("설정의 모든 항목은 문자열이어야 합니다.")
    normalized = {field: config[field].strip() for field in _REQUIRED_FIELDS}
    mode = config.get("mode", "nol_manual")
    if not isinstance(mode, str) or mode not in _VALID_MODES:
        raise ValueError("알 수 없는 실행 모드입니다.")
    if not normalized["event_name"]:
        raise ValueError("공연명을 입력해 주세요.")
    normalized["url"] = validate_nol_ticket_url(normalized["url"])
    parse_kst_datetime(normalized["date"], normalized["time"])
    normalized["mode"] = mode
    return normalized


def load_config(path: Path) -> dict[str, str]:
    """Load a valid saved configuration, falling back safely to defaults."""
    if not path.exists():
        return DEFAULT_CONFIG.copy()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("Configuration must be an object")
        return _normalize_config(loaded)
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return DEFAULT_CONFIG.copy()


def save_config(path: Path, config: Mapping[str, object]) -> None:
    """Validate and atomically write user configuration as UTF-8 JSON."""
    normalized = _normalize_config(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temporary_path, path)
