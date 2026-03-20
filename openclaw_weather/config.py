"""
크로스플랫폼 설정 파일 관리 및 API 키 조회 체인.

키 조회 우선순위: --api-key 인자 > WEATHER_API_KEY 환경변수 > config.json
"""

import json
import os
import sys
import stat
from pathlib import Path


APP_NAME = "nalssi"


def get_config_dir() -> Path:
    """플랫폼별 설정 디렉터리 경로를 반환합니다."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_NAME
        return Path.home() / "AppData" / "Roaming" / APP_NAME
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            return Path(xdg) / APP_NAME
        return Path.home() / ".config" / APP_NAME


def get_config_path() -> Path:
    """config.json 파일의 전체 경로를 반환합니다."""
    return get_config_dir() / "config.json"


def load_config() -> dict:
    """설정 파일을 읽어 dict로 반환합니다. 파일이 없으면 빈 dict."""
    config_path = get_config_path()
    if not config_path.exists():
        return {}
    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data: dict) -> Path:
    """설정을 config.json에 저장합니다. 디렉터리가 없으면 생성."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # Unix 계열에서 파일 권한 제한 (API 키 보호)
    if sys.platform != "win32":
        config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    return config_path


def resolve_api_key(cli_arg: str = None) -> str | None:
    """
    API 키를 우선순위 체인으로 조회합니다.
    1. CLI 인자 (--api-key)
    2. 환경변수 (WEATHER_API_KEY)
    3. config.json
    """
    if cli_arg:
        return cli_arg

    env_key = os.environ.get("WEATHER_API_KEY")
    if env_key:
        return env_key

    config = load_config()
    return config.get("api_key")


def mask_key(key: str) -> str:
    """API 키를 마스킹하여 표시합니다. (앞 4자리만 노출)"""
    if not key or len(key) <= 4:
        return "****"
    return key[:4] + "*" * (len(key) - 4)
