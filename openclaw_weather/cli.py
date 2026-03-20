"""
CLI 진입점 — 서브커맨드 라우팅 및 JSON 출력.

사용법:
    nalssi --location 서울
    nalssi --list
    nalssi config --set-key KEY
    nalssi config --check
    nalssi config --show
    nalssi config --clear
"""

import argparse
import json
import sys
from datetime import datetime

from openclaw_weather.config import (
    get_config_path,
    load_config,
    mask_key,
    resolve_api_key,
    save_config,
)
from openclaw_weather.weather import (
    LOCATION_GRID,
    get_weather,
)


def _json_print(data: dict):
    """JSON을 stdout으로 출력합니다."""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def build_setup_required_output(location: str = None) -> dict:
    """API 키 미설정 시 LLM이 사용자를 안내할 수 있는 구조화된 응답."""
    return {
        "location": location,
        "status": "SetupRequired",
        "error": "API key가 설정되지 않았습니다",
        "setup": {
            "summary": "기상청 API허브(KMA API Hub) 인증키가 필요합니다.",
            "steps": [
                {
                    "step": 1,
                    "action": "https://apihub.kma.go.kr/ 에서 회원가입 및 로그인",
                },
                {
                    "step": 2,
                    "action": (
                        "'동네예보 조회서비스'에서 다음 API를 활용신청: "
                        "getUltraSrtNcst(초단기실황), getVilageFcst(단기예보)"
                    ),
                },
                {
                    "step": 3,
                    "action": "마이페이지에서 발급된 authKey를 복사",
                },
                {
                    "step": 4,
                    "action": "실행: nalssi config --set-key YOUR_AUTH_KEY",
                },
            ],
            "urls": {
                "signup": "https://apihub.kma.go.kr/",
                "api_list": "https://apihub.kma.go.kr/apiList.do",
            },
            "alternative": "또는 직접 전달: nalssi --api-key YOUR_KEY --location 서울",
        },
        "data": None,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00"),
    }


# ============================================================================
# config 서브커맨드 핸들러
# ============================================================================

def handle_config(args):
    """config 서브커맨드 처리."""
    if args.set_key:
        config = load_config()
        config["api_key"] = args.set_key
        config_path = save_config(config)
        _json_print({
            "status": "ConfigSaved",
            "message": f"API key가 저장되었습니다.",
            "config_path": str(config_path),
        })

    elif args.check:
        api_key = resolve_api_key()
        if not api_key:
            _json_print({
                "status": "KeyNotFound",
                "error": "저장된 API key가 없습니다.",
                "hint": "nalssi config --set-key YOUR_KEY 로 설정하세요.",
            })
            sys.exit(1)

        # 실제 API 호출 + resultCode 검증 (서울 초단기실황)
        try:
            from openclaw_weather.weather import fetch_ultra_ncst
            now = datetime.now()
            ncst = fetch_ultra_ncst(api_key, 60, 127, now)
            _json_print({
                "status": "KeyValid",
                "message": "API key가 유효합니다. getUltraSrtNcst 응답 정상.",
                "key_preview": mask_key(api_key),
                "sample": {"T1H": ncst.get("T1H")},
            })
        except RuntimeError as e:
            _json_print({
                "status": "KeyInvalid",
                "error": str(e),
                "hint": "인증키를 확인하거나 API 활용신청 상태를 확인하세요.",
                "urls": {
                    "api_hub": "https://apihub.kma.go.kr/",
                },
            })
            sys.exit(1)

    elif args.show:
        config = load_config()
        api_key = config.get("api_key")
        _json_print({
            "status": "ConfigInfo",
            "config_path": str(get_config_path()),
            "api_key": mask_key(api_key) if api_key else None,
            "key_source": _describe_key_source(),
        })

    elif args.clear:
        config = load_config()
        config.pop("api_key", None)
        config_path = save_config(config)
        _json_print({
            "status": "ConfigCleared",
            "message": "저장된 API key가 삭제되었습니다.",
            "config_path": str(config_path),
        })

    else:
        # config 서브커맨드만 입력한 경우 → show와 동일
        handle_config(argparse.Namespace(
            set_key=None, check=False, show=True, clear=False,
        ))


def _describe_key_source() -> str:
    """현재 API 키가 어디서 오는지 설명합니다."""
    import os
    if os.environ.get("WEATHER_API_KEY"):
        return "environment variable (WEATHER_API_KEY)"
    config = load_config()
    if config.get("api_key"):
        return f"config file ({get_config_path()})"
    return "not set"


# ============================================================================
# weather 조회 (기본 동작)
# ============================================================================

def handle_weather(args):
    """날씨 조회 (기본 커맨드)."""
    api_key = resolve_api_key(args.api_key)

    if not api_key:
        _json_print(build_setup_required_output(args.location))
        sys.exit(1)

    result = get_weather(api_key, args.location)
    _json_print(result)

    if result.get("status") == "Error":
        sys.exit(1)


def handle_list(args):
    """지원 지역 목록을 JSON으로 출력합니다."""
    locations = []
    for eng_key, (nx, ny, kr_name) in sorted(LOCATION_GRID.items()):
        locations.append({
            "name_en": eng_key,
            "name_kr": kr_name,
            "nx": nx,
            "ny": ny,
        })
    _json_print({
        "status": "LocationList",
        "total": len(locations),
        "locations": locations,
    })


# ============================================================================
# argparse 설정
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        prog="nalssi",
        description="nalssi — 기상청 API허브 연동 날씨 모듈",
    )

    subparsers = parser.add_subparsers(dest="command")

    # --- config 서브커맨드 ---
    config_parser = subparsers.add_parser(
        "config",
        help="API 키 설정 관리",
    )
    config_group = config_parser.add_mutually_exclusive_group()
    config_group.add_argument(
        "--set-key", metavar="KEY",
        help="API 키를 설정 파일에 저장",
    )
    config_group.add_argument(
        "--check", action="store_true",
        help="저장된 API 키의 유효성 검증",
    )
    config_group.add_argument(
        "--show", action="store_true",
        help="현재 설정 정보 확인",
    )
    config_group.add_argument(
        "--clear", action="store_true",
        help="저장된 API 키 삭제",
    )

    # --- 기본 커맨드 옵션 (날씨 조회) ---
    parser.add_argument(
        "--location", "-l",
        type=str,
        default="Seoul",
        help="조회할 지역명 (한글 또는 영문, 기본값: Seoul)",
    )
    parser.add_argument(
        "--api-key", "-k",
        type=str,
        default=None,
        help="기상청 API 인증키 (미입력시 저장된 키 사용)",
    )
    parser.add_argument(
        "--list", "-L",
        action="store_true",
        help="지원되는 지역 목록 출력",
    )

    args = parser.parse_args()

    # 라우팅
    if args.command == "config":
        handle_config(args)
    elif args.list:
        handle_list(args)
    else:
        handle_weather(args)


if __name__ == "__main__":
    main()
