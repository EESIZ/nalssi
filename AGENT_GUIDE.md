# nalssi — LLM 에이전트 통합 가이드

이 문서는 LLM 에이전트(OpenClaw, Claude, GPT 등)가 `nalssi`를 **자동으로 설치하고 설정**할 수 있도록 작성되었습니다.

---

## 1. 설치

```bash
pip install nalssi
```

> Python 3.8+ 필요. 외부 의존성 없음 (표준 라이브러리만 사용).

설치 후 CLI 경로 확인:
```bash
which nalssi || python3 -m openclaw_weather
```

`which`로 찾을 수 없는 경우 `~/.local/bin/nalssi`에 설치되어 있을 수 있음.
이 경우 절대경로로 실행: `/home/<user>/.local/bin/nalssi`

---

## 2. API 키 발급 (사용자 행동 필요)

nalssi는 **기상청 API허브** 인증키가 필요합니다. 이 단계는 자동화할 수 없으며, 사용자에게 안내해야 합니다.

### 사용자에게 전달할 안내문

> 날씨 기능을 사용하려면 기상청 API허브 인증키가 필요합니다.
>
> 1. https://apihub.kma.go.kr/ 에서 **회원가입** 및 로그인
> 2. **API 목록**에서 '동네예보 조회서비스' 검색
> 3. 다음 2개 API를 **활용신청**:
>    - `getUltraSrtNcst` (초단기실황) — 현재 기온, 습도
>    - `getVilageFcst` (단기예보) — 최고/최저기온, 강수확률, 하늘상태
> 4. 마이페이지에서 발급된 **authKey**를 복사해서 알려주세요.

### API 활용신청 상세 경로

```
apihub.kma.go.kr 로그인
→ 상단 메뉴 "API 목록"
→ 검색: "동네예보"
→ "동네예보 조회서비스" 클릭
→ API 상세 페이지에서 "활용신청" 버튼
→ getUltraSrtNcst, getVilageFcst 각각 신청
→ 마이페이지 → 인증키 확인
```

> **주의**: 신청 직후 바로 사용 가능하나, 간혹 승인에 수 분이 소요될 수 있습니다.

---

## 3. API 키 등록

사용자로부터 키를 받으면:

```bash
nalssi config --set-key <사용자가_제공한_키>
```

키 유효성 확인:

```bash
nalssi config --check
```

### 응답별 판단

| status | 의미 | 다음 행동 |
|--------|------|-----------|
| `ConfigSaved` | 키 저장 완료 | `config --check`로 유효성 검증 |
| `KeyValid` | 키가 유효함 | 설정 완료, 날씨 조회 가능 |
| `KeyInvalid` | 키가 유효하지 않음 | 사용자에게 키 재확인 요청 |
| `KeyNotFound` | 저장된 키 없음 | 키 등록 절차 진행 |

---

## 4. 날씨 조회

```bash
nalssi --location 서울
nalssi --location Busan
nalssi --location 제주
```

지역을 지정하지 않으면 기본값 `Seoul`.

### 성공 응답 구조

```json
{
  "location": "서울",
  "status": "Success",
  "data": {
    "condition": "Clear",
    "temp_current": 7.2,
    "temp_max": 14.0,
    "temp_min": 2.0,
    "rain_chance": 0,
    "dust_pm10": "N/A",
    "humidity": 72
  },
  "timestamp": "2026-03-20T10:00:00Z"
}
```

### status별 에이전트 행동

```
status == "Success"       → data 필드에서 날씨 정보 추출, 사용자에게 브리핑
status == "SetupRequired" → setup.steps를 사용자에게 안내 (API 키 미설정)
status == "Error"         → error 필드를 사용자에게 전달
```

---

## 5. 응답 해석 및 브리핑 생성

### condition 한글 변환

| 영문 | 한글 | 이모지 |
|------|------|--------|
| Clear | 맑음 | ☀️ |
| Mostly Cloudy | 구름 많음 | ⛅ |
| Cloudy | 흐림 | ☁️ |
| Rain | 비 | 🌧️ |
| Snow | 눈 | 🌨️ |
| Rain/Snow | 비/눈 | 🌧️🌨️ |
| Shower | 소나기 | 🌦️ |

### 상황별 추가 안내

| 조건 | 메시지 |
|------|--------|
| `rain_chance >= 60` | ☂️ 우산 챙기세요! |
| `temp_max - temp_min >= 10` | 일교차가 크니 겉옷 챙기세요! |
| `temp_current <= 0` | 영하입니다, 따뜻하게 입으세요! |
| `temp_max >= 33` | 폭염 주의! 수분 보충 잊지 마세요! |
| `dust_pm10 == "N/A"` | 미세먼지 정보 생략 |

### 브리핑 예시

```
🌡️ 서울 날씨

맑음 ☀️ / 현재 7.2℃
최저 2.0℃ ~ 최고 14.0℃
습도 72% / 강수확률 0%
일교차가 크니 겉옷 챙기세요!
```

---

## 6. 지원 지역 목록

```bash
nalssi --list
```

30개 지역 지원:
서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종, 수원, 제주,
춘천, 청주, 전주, 창원, 강릉, 원주, 천안, 포항, 김해, 여수,
평택, 속초, 안동, 목포, 익산, 군산, 과천, 성남, 고양, 용인

> 한글 또는 영문 모두 사용 가능 (서울 = Seoul = seoul)

사용자가 지원되지 않는 지역을 요청하면, 가장 가까운 지원 지역을 추천하세요.

---

## 7. 설정 파일 위치

| 플랫폼 | 경로 |
|--------|------|
| Linux | `~/.config/nalssi/config.json` |
| macOS | `~/Library/Application Support/nalssi/config.json` |
| Windows | `%APPDATA%\nalssi\config.json` |

설정 관리 명령:

```bash
nalssi config --show     # 현재 설정 확인 (키 마스킹)
nalssi config --check    # 키 유효성 검증
nalssi config --clear    # 저장된 키 삭제
```

---

## 8. 키 조회 우선순위

nalssi는 다음 순서로 API 키를 찾습니다:

1. `--api-key` CLI 인자 (일회성)
2. `WEATHER_API_KEY` 환경변수
3. 설정 파일 (`config --set-key`로 저장)

> 에이전트가 여러 사용자를 지원하는 경우, `--api-key`로 직접 전달하는 방식이 적합합니다.

---

## 9. 에이전트 통합 체크리스트

```
[ ] pip install nalssi 실행
[ ] nalssi 실행 경로 확인 (which nalssi 또는 ~/.local/bin/nalssi)
[ ] 키 없이 실행 → SetupRequired 응답 확인
[ ] 사용자에게 API 키 발급 안내
[ ] 사용자로부터 키를 받아 config --set-key 실행
[ ] config --check로 키 유효성 확인
[ ] nalssi --location 서울 로 실제 조회 테스트
[ ] 브리핑 생성 로직 구현
```

---

## 10. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `SetupRequired` | API 키 미등록 | `config --set-key` 실행 |
| `KeyInvalid` | 키가 틀림 또는 만료 | 사용자에게 키 재확인 요청 |
| `HTTP Error 403` | API 활용신청 미완료 | 사용자에게 `getUltraSrtNcst`, `getVilageFcst` 활용신청 안내 |
| `Connection Error` | 네트워크 문제 | 인터넷 연결 확인 |
| `command not found` | PATH 문제 | 절대경로 사용 또는 `python3 -m openclaw_weather` |
| `temp_max`/`temp_min` null | `getVilageFcst` 미신청 | 사용자에게 해당 API 활용신청 안내 |
