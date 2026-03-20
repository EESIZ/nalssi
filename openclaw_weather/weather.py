"""
기상청 API허브 연동 — API 호출, 지역 매핑, 데이터 포맷팅.
"""

import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta


# ============================================================================
# 지역 → 격자 좌표 매핑 (기상청 단기예보 격자 좌표)
# ============================================================================
LOCATION_GRID = {
    # 영문명: (nx, ny, 한글명)
    "seoul":       (60, 127, "서울"),
    "busan":       (98, 76,  "부산"),
    "daegu":       (89, 90,  "대구"),
    "incheon":     (55, 124, "인천"),
    "gwangju":     (58, 74,  "광주"),
    "daejeon":     (67, 100, "대전"),
    "ulsan":       (102, 84, "울산"),
    "sejong":      (66, 103, "세종"),
    "suwon":       (60, 121, "수원"),
    "jeju":        (52, 38,  "제주"),
    "chuncheon":   (73, 134, "춘천"),
    "cheongju":    (69, 106, "청주"),
    "jeonju":      (63, 89,  "전주"),
    "changwon":    (90, 77,  "창원"),
    "gangneung":   (92, 131, "강릉"),
    "wonju":       (76, 122, "원주"),
    "cheonan":     (63, 110, "천안"),
    "pohang":      (102, 94, "포항"),
    "gimhae":      (95, 77,  "김해"),
    "yeosu":       (73, 66,  "여수"),
    "pyeongtaek":  (62, 114, "평택"),
    "sokcho":      (87, 141, "속초"),
    "andong":      (91, 106, "안동"),
    "mokpo":       (50, 67,  "목포"),
    "iksan":       (60, 91,  "익산"),
    "gunsan":      (56, 92,  "군산"),
    "gwacheon":    (60, 124, "과천"),
    "seongnam":    (62, 123, "성남"),
    "goyang":      (57, 128, "고양"),
    "yongin":      (64, 119, "용인"),
}

# 한글 → 영문 매핑
KOREAN_TO_ENGLISH = {
    "서울": "seoul", "부산": "busan", "대구": "daegu", "인천": "incheon",
    "광주": "gwangju", "대전": "daejeon", "울산": "ulsan", "세종": "sejong",
    "수원": "suwon", "제주": "jeju", "춘천": "chuncheon", "청주": "cheongju",
    "전주": "jeonju", "창원": "changwon", "강릉": "gangneung", "원주": "wonju",
    "천안": "cheonan", "포항": "pohang", "김해": "gimhae", "여수": "yeosu",
    "평택": "pyeongtaek", "속초": "sokcho", "안동": "andong", "목포": "mokpo",
    "익산": "iksan", "군산": "gunsan", "과천": "gwacheon", "성남": "seongnam",
    "고양": "goyang", "용인": "yongin",
}

# 하늘상태 코드 → 텍스트
SKY_CODE = {
    "1": "Clear",
    "3": "Mostly Cloudy",
    "4": "Cloudy",
}

# 강수형태 코드 → 텍스트
PTY_CODE = {
    "0": None,
    "1": "Rain",
    "2": "Rain/Snow",
    "3": "Snow",
    "4": "Shower",
}

# 기상청 API허브 기본 URL
BASE_URL = "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0"


def resolve_location(location_str: str):
    """
    지역명을 격자 좌표(nx, ny)와 표시 이름으로 변환합니다.

    Returns:
        (nx, ny, display_name) 또는 None
    """
    key = location_str.strip().lower()

    if key in KOREAN_TO_ENGLISH:
        key = KOREAN_TO_ENGLISH[key]

    if key in LOCATION_GRID:
        nx, ny, kr_name = LOCATION_GRID[key]
        display_name = location_str.strip().title()
        return nx, ny, display_name

    return None


def get_base_time_vilage_fcst(now: datetime) -> tuple:
    """
    단기예보(getVilageFcst)의 base_date, base_time을 계산합니다.
    발표시각: 0200, 0500, 0800, 1100, 1400, 1700, 2000, 2300 (1일 8회)
    API 제공: 각 발표시각 + 10분 후
    """
    base_times = [2, 5, 8, 11, 14, 17, 20, 23]
    current_hour = now.hour
    current_min = now.minute

    selected = None
    for bt in reversed(base_times):
        if current_hour > bt or (current_hour == bt and current_min >= 10):
            selected = bt
            break

    if selected is None:
        selected = 23
        now = now - timedelta(days=1)

    base_date = now.strftime("%Y%m%d")
    base_time = f"{selected:02d}00"
    return base_date, base_time


def get_base_time_ultra_ncst(now: datetime) -> tuple:
    """
    초단기실황(getUltraSrtNcst)의 base_date, base_time을 계산합니다.
    매시간 정시 생성, 10분 후 API 제공
    """
    if now.minute < 10:
        now = now - timedelta(hours=1)

    base_date = now.strftime("%Y%m%d")
    base_time = f"{now.hour:02d}00"
    return base_date, base_time


def call_api(endpoint: str, service_key: str, params: dict) -> dict:
    """기상청 API허브를 호출하고 JSON 응답을 반환합니다."""
    params["authKey"] = service_key
    params["dataType"] = "JSON"

    url = f"{BASE_URL}/{endpoint}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP Error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection Error: {e.reason}")
    except json.JSONDecodeError:
        raise RuntimeError("API 응답을 JSON으로 파싱할 수 없습니다.")


def fetch_ultra_ncst(service_key: str, nx: int, ny: int, now: datetime) -> dict:
    """초단기실황 조회 — 현재 기온, 습도 등"""
    base_date, base_time = get_base_time_ultra_ncst(now)

    params = {
        "numOfRows": "10",
        "pageNo": "1",
        "base_date": base_date,
        "base_time": base_time,
        "nx": str(nx),
        "ny": str(ny),
    }

    data = call_api("getUltraSrtNcst", service_key, params)

    result_code = data.get("response", {}).get("header", {}).get("resultCode", "")
    if result_code != "00":
        msg = data.get("response", {}).get("header", {}).get("resultMsg", "Unknown")
        raise RuntimeError(f"초단기실황 API 에러: [{result_code}] {msg}")

    items = data["response"]["body"]["items"]["item"]

    ncst = {}
    for item in items:
        ncst[item["category"]] = item["obsrValue"]

    return ncst


def fetch_vilage_fcst(service_key: str, nx: int, ny: int, now: datetime) -> dict:
    """단기예보 조회 — 최고/최저기온, 강수확률, 하늘상태 등"""
    base_date, base_time = get_base_time_vilage_fcst(now)

    params = {
        "numOfRows": "1000",
        "pageNo": "1",
        "base_date": base_date,
        "base_time": base_time,
        "nx": str(nx),
        "ny": str(ny),
    }

    data = call_api("getVilageFcst", service_key, params)

    result_code = data.get("response", {}).get("header", {}).get("resultCode", "")
    if result_code != "00":
        msg = data.get("response", {}).get("header", {}).get("resultMsg", "Unknown")
        raise RuntimeError(f"단기예보 API 에러: [{result_code}] {msg}")

    items = data["response"]["body"]["items"]["item"]

    today = now.strftime("%Y%m%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y%m%d")

    fcst = {
        "TMX": None, "TMN": None, "POP": None,
        "SKY": None, "PTY": None, "REH": None,
    }

    current_fcst_time = f"{now.hour:02d}00"

    for item in items:
        cat = item["category"]
        fcst_date = item["fcstDate"]
        fcst_time = item["fcstTime"]
        value = item["fcstValue"]

        if cat == "TMX" and fcst_date in (today, tomorrow):
            if fcst[cat] is None:
                fcst[cat] = value
        elif cat == "TMN" and fcst_date in (today, tomorrow):
            if fcst[cat] is None:
                fcst[cat] = value
        elif cat in ("POP", "SKY", "PTY", "REH") and fcst_date == today:
            if fcst[cat] is None or fcst_time >= current_fcst_time:
                if fcst[cat] is None:
                    fcst[cat] = value

    return fcst


def determine_condition(sky_code: str, pty_code: str) -> str:
    """하늘상태와 강수형태를 조합하여 날씨 상태 문자열을 결정합니다."""
    if pty_code and pty_code != "0":
        pty_text = PTY_CODE.get(pty_code)
        if pty_text:
            return pty_text

    if sky_code and sky_code in SKY_CODE:
        return SKY_CODE[sky_code]
    return "Clear"


def safe_float(value, default=None):
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=None):
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def build_weather_output(location_name: str, ncst: dict, fcst: dict, now: datetime) -> dict:
    """MVP 사양에 맞는 날씨 JSON 출력 구조를 생성합니다."""
    temp_current = safe_float(ncst.get("T1H"))
    temp_max = safe_float(fcst.get("TMX"))
    temp_min = safe_float(fcst.get("TMN"))
    rain_chance = safe_int(fcst.get("POP"))
    humidity = safe_int(ncst.get("REH")) or safe_int(fcst.get("REH"))

    sky = fcst.get("SKY", "")
    pty = fcst.get("PTY", "") or ncst.get("PTY", "0")
    condition = determine_condition(sky, pty)

    return {
        "location": location_name,
        "status": "Success",
        "data": {
            "condition": condition,
            "temp_current": temp_current,
            "temp_max": temp_max,
            "temp_min": temp_min,
            "rain_chance": rain_chance,
            "dust_pm10": "N/A",
            "humidity": humidity,
        },
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def build_error_output(location_name: str, error_msg: str) -> dict:
    """에러 발생 시의 JSON 출력"""
    return {
        "location": location_name,
        "status": "Error",
        "error": error_msg,
        "data": None,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def get_weather(api_key: str, location: str) -> dict:
    """
    날씨 조회 메인 함수.
    성공 시 Success JSON, 실패 시 Error JSON 반환.
    """
    location_info = resolve_location(location)
    if location_info is None:
        return build_error_output(
            location,
            f"지원되지 않는 지역입니다: '{location}'. --list 옵션으로 지원 지역을 확인하세요."
        )

    nx, ny, display_name = location_info
    now = datetime.now()

    try:
        ncst = fetch_ultra_ncst(api_key, nx, ny, now)

        try:
            fcst = fetch_vilage_fcst(api_key, nx, ny, now)
        except RuntimeError:
            fcst = {}

        return build_weather_output(display_name, ncst, fcst, now)

    except RuntimeError as e:
        return build_error_output(display_name, str(e))
    except Exception as e:
        return build_error_output(display_name, f"예상치 못한 에러: {str(e)}")
