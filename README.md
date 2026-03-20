# nalssi 🌡️

!https://github.com/EESIZ/nalssi/blob/main/img.png


한국 기상청 API허브 연동 날씨 CLI 도구.
LLM 에이전트가 `exec`으로 실행하여 실시간 날씨 데이터를 JSON으로 받아갈 수 있습니다.

> **외부 라이브러리 불필요** — Python 3.8+ 표준 라이브러리만 사용합니다.

## 설치

```bash
pip install git+https://github.com/EESIZ/nalssi.git
```

> PyPI 배포 예정. 현재는 GitHub에서 직접 설치합니다.

## 초기 설정

기상청 API허브 인증키가 필요합니다. 키 없이 실행하면 발급 안내가 JSON으로 출력됩니다.

```bash
nalssi
# → {"status": "SetupRequired", "setup": {"steps": [...], "urls": {...}}}
```

### API 키 발급

1. [기상청 API허브](https://apihub.kma.go.kr/) 회원가입 및 로그인
2. API 목록에서 **'동네예보 조회서비스'** 검색 후 아래 API 활용신청:
   - `getUltraSrtNcst` (초단기실황)
   - `getVilageFcst` (단기예보)
3. 마이페이지에서 발급된 **authKey** 복사

### 키 등록 및 확인

```bash
nalssi config --set-key 발급받은_인증키
nalssi config --check
# → {"status": "KeyValid", ...}
```

## 사용법

```bash
nalssi                        # 서울 날씨 (기본)
nalssi --location 부산         # 한글 지역명
nalssi --location Jeju         # 영문 지역명
nalssi --list                  # 지원 지역 목록 (JSON)
```

### 설정 관리

```bash
nalssi config --set-key KEY    # 키 저장
nalssi config --check          # 키 유효성 검증
nalssi config --show           # 현재 설정 확인
nalssi config --clear          # 저장된 키 삭제
```

### 키 조회 우선순위

1. `--api-key` CLI 인자 (일회성)
2. `WEATHER_API_KEY` 환경변수
3. 설정 파일 (`nalssi config --set-key`로 저장)

## 출력 형식

모든 출력은 JSON입니다. `status` 필드로 결과를 판단합니다.

### Success

```json
{
  "location": "서울",
  "status": "Success",
  "data": {
    "condition": "Cloudy",
    "temp_current": 5.2,
    "temp_max": 10.5,
    "temp_min": -1.2,
    "rain_chance": 20,
    "dust_pm10": "N/A",
    "humidity": 45
  },
  "timestamp": "2026-03-20T09:00:00+09:00"
}
```

### SetupRequired (키 미설정)

```json
{
  "status": "SetupRequired",
  "setup": {
    "steps": [...],
    "urls": {"signup": "https://apihub.kma.go.kr/"}
  }
}
```

### Error

```json
{
  "status": "Error",
  "error": "에러 메시지",
  "data": null
}
```

## 데이터 필드

| 필드 | 설명 | 출처 |
|------|------|------|
| `condition` | 날씨 상태 (Clear, Mostly Cloudy, Cloudy, Rain, Snow 등) | 단기예보 SKY + PTY |
| `temp_current` | 현재 기온 (℃) | 초단기실황 T1H |
| `temp_max` | 오늘 최고기온 (℃) | 단기예보 TMX |
| `temp_min` | 오늘 최저기온 (℃) | 단기예보 TMN |
| `rain_chance` | 강수확률 (%) | 단기예보 POP |
| `dust_pm10` | 미세먼지 (현재 N/A) | 에어코리아 연동 예정 |
| `humidity` | 습도 (%) | 초단기실황 REH |

## 지원 지역 (30개)

서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종, 수원, 제주,
춘천, 청주, 전주, 창원, 강릉, 원주, 천안, 포항, 김해, 여수,
평택, 속초, 안동, 목포, 익산, 군산, 과천, 성남, 고양, 용인

## LLM 에이전트 연동

에이전트가 `exec`으로 실행:

```
exec: nalssi --location 서울
```

`status` 필드로 동작 판단:

| status | 에이전트 행동 |
|--------|--------------|
| `Success` | `data` 필드에서 날씨 정보 추출, 사용자에게 브리핑 |
| `SetupRequired` | `setup.steps`를 사용자에게 안내 (API 키 발급 유도) |
| `Error` | `error` 필드를 사용자에게 전달 |

> 상세한 에이전트 통합 가이드는 [AGENT_GUIDE.md](AGENT_GUIDE.md) 참조

## 설정 파일 위치

| 플랫폼 | 경로 |
|--------|------|
| Linux | `~/.config/nalssi/config.json` |
| macOS | `~/Library/Application Support/nalssi/config.json` |
| Windows | `%APPDATA%\nalssi\config.json` |

## 향후 계획

- [ ] 미세먼지(PM10) 데이터 연동 (에어코리아 API)
- [ ] 자외선 지수 추가
- [ ] 주간 예보 지원

## 라이선스

MIT
