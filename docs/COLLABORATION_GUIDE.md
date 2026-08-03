# 협업자 가이드 — 서울 경사·기상 대중교통 보행접근성 분석

> 이 문서는 Google Drive로 프로젝트를 처음 받은 협업자를 위한 시작 안내서다.
> 처음부터 끝까지 한 번 읽고 나면 분석을 바로 이어받을 수 있다.

---

## 1. 프로젝트 한눈에

이 연구는 서울시에서 **경사와 기상 악화가 겹칠 때** 대중교통 보행접근성이 취약해지는 지역을 찾고, 정책 시나리오별 개선 효과를 정량 비교하는 학부 연구 프로젝트다. 분석 단위는 H3 resolution 9 육각격자(~174m)이며, 서울 시가지 4,551개 hex를 대상으로 한다. 비용 모형은 거리만 반영한 M0부터 경사·기상·상호작용을 모두 반영한 M3까지 4단계로 구성된다.

**현재 진행 단계**

| 단계 | 상태 |
|---|---|
| S0-M0 ~ S0-M3 기준선 산출 | 완료 |
| 취약 hex 식별 및 원인 진단 | 완료 |
| 생활이동 OD 보조 분석 | 완료 |
| 정책 시나리오 S1 / S3 / S4 | **미완 — 협업자 작업 대상** |

**협업자가 Drive에서 받는 것**

- `src/` — Python 분석 하네스 전체
- `configs/` — 설정 파일 (경로, 파라미터)
- `docs/` — 방법론 문서, QGIS 매뉴얼, 이 가이드
- `tests/` — 단위 테스트 46개
- `outputs/` — 보고서·QA JSON (재현 결과물)
- `qgis/` — QGIS 프로젝트 및 산출 레이어

> raw 데이터(`data/raw/`)는 별도 Drive 폴더에서 받는다. 아래 **3절** 참고.

---

## 2. 받은 후 첫 30분: 환경 세팅

### 2-1. 압축 풀기 / Drive 동기화

Drive에서 ZIP으로 받았다면 아래 위치에 압축을 푼다.

```
C:\Users\<본인계정>\SL프로젝트\      ← Windows 권장
~/SL프로젝트/                        ← macOS/Linux 권장
```

Drive 스트리밍 동기화(Google Drive for Desktop)를 사용한다면 해당 Drive 폴더 경로를 프로젝트 루트로 쓰면 된다. 경로에 **한글이나 공백이 포함되면 일부 도구에서 문제가 생길 수 있으니** 가급적 영문 경로를 권장한다.

---

### 2-2. Python 버전 확인

```bash
python --version
```

`Python 3.11.x` ~ `3.14.x` 범위면 OK. 3.10 이하라면 업그레이드 필요.

> **오류: 'python'을 찾을 수 없음 (Windows)**
> Windows Store Python shim이 잡히는 경우다. `python3 --version`으로 시도하거나, Windows 설정 → 앱 실행 별칭에서 `python.exe` Store 링크를 비활성화한다. 자세한 내용은 `README.md` 158번 줄 참고.

---

### 2-3. `uv` 설치 확인

```bash
uv --version
```

없으면 설치:

```bash
# pip으로 설치 (간단)
pip install uv

# 또는 공식 설치 스크립트 (권장, https://docs.astral.sh/uv/getting-started/installation/)
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

### 2-4. 가상환경 생성

프로젝트 루트에서 실행:

```bash
uv venv --python 3.14
```

> `--python 3.14` 대신 설치된 버전으로 바꿔도 된다 (예: `--python 3.11`).
> `.venv/` 폴더가 생기면 성공.

---

### 2-5. 의존성 설치

**Windows:**

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt
```

**macOS / Linux:**

```bash
uv pip install --python .venv/bin/python -r requirements-dev.txt
```

> **오류: `geopandas` 설치 실패 (Windows)**
> GDAL 바이너리 의존성 문제일 수 있다. `pip install geopandas` 단독으로 먼저 시도하거나, conda 환경 사용을 고려한다.
>
> **오류: `h3==4.4.2` 버전 충돌**
> h3 버전은 고정이다. 임의로 올리지 말 것. `pip install h3==4.4.2 --force-reinstall`로 재설치.

---

### 2-6. PYTHONPATH 환경변수 설정

**Windows (PowerShell, 현재 세션):**

```powershell
$env:PYTHONPATH = 'src'
```

**Windows (cmd):**

```cmd
set PYTHONPATH=src
```

**macOS / Linux:**

```bash
export PYTHONPATH=src
```

> 매번 설정하기 번거롭다면 `.env` 파일에 `PYTHONPATH=src`를 넣고 IDE에서 자동 로드하도록 설정한다.

---

### 2-7. 동작 확인

**Windows:**

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

**macOS / Linux:**

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider
```

기대 결과:

```
86 passed
```

(또는 그 이상 — 테스트가 추가되었을 수 있다. 2026-06-11 실측 기준 86개)

> 테스트 중 `ModuleNotFoundError: sl_accessibility` 가 나오면 PYTHONPATH가 설정되지 않은 것이다. 2-6단계를 다시 확인한다.

---

## 3. 데이터 받는 방법

### Drive 폴더 구조 (placeholder — 링크는 팀장이 추가 예정)

```
[Google Drive 공유 폴더]
├── data_raw/                    ← 이 폴더 전체를 로컬 data/raw/ 에 복사
│   ├── bus_stops/
│   ├── subway_exits/
│   ├── dem_tiles/               ← Google Elevation API 산출물 (재배포 제한)
│   ├── 서울시등록인구_2025_4분기.xlsx
│   └── ...
└── life_mobility/               ← 대용량 옵션 (아래 참고)
    └── life_mobility_admin_2025_summary.csv  (약 89GB)
```

> **Drive 링크:** `[TODO: 팀장이 링크 추가]`

### 로컬 배치 위치

Drive에서 받은 파일은 프로젝트 루트의 `data/raw/` 아래에 놓는다.

```
<프로젝트 루트>/
└── data/
    └── raw/
        ├── bus_stops/
        ├── subway_exits/
        └── ...
```

파일 경로의 **단일 진실원은 `configs/data_sources.yaml`** 이다. 파일명이나 경로를 바꿔야 한다면 이 파일만 수정한다. 코드 안에 경로를 하드코딩하지 않는다.

### 89GB 대용량 파일 (`life_mobility_admin_2025_summary.csv`)

이 파일은 선택 사항이다. 집계 산출물(`data/interim/life_mobility_od_admin_aux.parquet`)이 이미 있으므로 대부분의 작업은 raw CSV 없이 가능하다. 시나리오 S1/S3/S4 작업에는 필요하지 않을 가능성이 높다.

필요한 경우에만 받고, 받은 뒤에도 **절대 코드에서 통째로 읽지 않는다** (아래 7절 작업 규칙 참고).

---

## 4. 프로젝트 폴더 구조

```
<프로젝트 루트>/
├── src/sl_accessibility/    Python 분석 하네스 (핵심 로직 전부)
├── configs/                 경로·파라미터·데이터소스 설정 파일
├── data/
│   ├── raw/                 원본 데이터 (수정 금지)
│   ├── interim/             중간 산출물 (Parquet 등)
│   └── derived/             최종 파생 산출물
├── outputs/
│   └── reports/             QA JSON, 보고서, 통계표
├── qgis/                    QGIS 프로젝트 파일 및 산출 레이어 (.gpkg)
├── docs/                    방법론 문서, QGIS 매뉴얼, 이 가이드
├── tests/                   단위 테스트 (pytest)
├── scripts/                 CLI 실행용 wrapper 스크립트
└── skills/                  repo-local Codex 스킬 (참고용)
```

---

## 5. 첫 분석 재현하기 — 5분 데모

환경 설정이 끝나면 아래 명령으로 데이터 유효성 검사를 돌려본다.

**Windows:**

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python.exe -m sl_accessibility.cli validate-data
```

**macOS / Linux:**

```bash
export PYTHONPATH=src
.venv/bin/python -m sl_accessibility.cli validate-data
```

성공 시 아래 파일이 생성된다:

```
outputs/reports/data_validation.json
```

JSON 안에 `"status": "ok"` 가 있으면 환경 구성이 정상이다. 이 단계가 통과되면 분석 CLI를 쓸 준비가 된 것이다.

**주요 CLI 명령 목록 (참고):**

| 명령 | 설명 |
|---|---|
| `validate-data` | 데이터 계약 검증 |
| `build-hex-demand-final` | H3 수요 피처 최종 산출 |
| `build-vulnerability-final` | 취약도 최종 산출 |
| `build-life-mobility-od-aux` | 생활이동 OD 보조 집계 (89GB, 오래 걸림) |
| `build-hex-mobility-aux` | H3 이동 보조 레이어 생성 |

---

## 6. 작업 시작 전 필독 문서 5개

아래 문서를 순서대로 읽는다. 특히 앞 세 개는 반드시 읽을 것.

| 순서 | 파일 | 읽는 이유 |
|---|---|---|
| 1 | `README.md` | 현재 진행 상태, 빠른 실행 명령, 대용량 안전 규칙 |
| 2 | `docs/분석_진행_정리.md` | 방법론·결과·해석 본문 보고서 v2.0 (가장 중요) |
| 3 | `docs/working_plan.md` | 복구 기준점, 다음 우선순위 |
| 4 | `docs/methods/cost_function_parameters.md` | 비용함수 계수 — 수정 시 전체 결과가 바뀌므로 주의 |
| 5 | `docs/SCENARIO_TASK_ASSIGNMENT.md` | 시나리오별 작업 분담표 (같은 폴더에 위치) |

> 오류·가정·이미 알려진 수정 사항은 `docs/implementation_corrections.md` 에 정리되어 있다. 뭔가 이상하다 싶을 때 먼저 여기를 확인한다.

---

## 7. 작업 규칙 (협업 매너)

### 절대 직접 수정 금지

아래 파일은 건드리지 않는다. 수정이 필요하다면 팀 채팅에서 논의 후 팀장만 수정한다.

```
data/raw/*
configs/data_sources.yaml
pyproject.toml
```

### 결과물 저장 위치

본인이 생성한 결과물은 이름 prefix를 붙인다.

```
outputs/reports/<본인이름>_*.json
```

예: `outputs/reports/jisoo_s1_vulnerability.json`

### QGIS 레이어 명명 규칙

레이어 이름은 반드시 아래 접두어 중 하나로 시작한다.

| 접두어 | 의미 |
|---|---|
| `raw_` | 원본 그대로 로드 |
| `wrk_` | 작업 중간 레이어 |
| `qa_` | 검증용 레이어 |
| `out_` | 산출 레이어 |
| `map_` | 최종 지도 출력용 |

CRS는 **항상 `EPSG:5179`** (Korea 2000 / Unified CS). 다른 CRS로 저장하지 않는다.

### 대용량 파일 안전 규칙

아래 파일은 코드에서 통째로 읽지 않는다.

```
data/life_mobility_admin_2025_summary.csv     (~89GB)
data/bus_stop_ridership_2025_with_geom.csv
data/250_LOCAL_RESD_202511/*.csv
```

반드시 lazy scan, column projection, chunk 처리, 또는 Parquet 변환 산출물을 사용한다. 처리 방법은 `README.md` 146-154번 줄 참고.

### 작업 노트

본인이 한 작업은 반드시 노트북 파일에 기록한다.

```
<본인이름>_작업노트.ipynb
```

프로젝트 루트 또는 `notebooks/` 폴더에 저장한다.

---

## 8. 막혔을 때

**순서대로 확인한다.**

1. **`docs/implementation_corrections.md`** — 이미 알려진 가정·오류·수정 이력 정리
2. **`outputs/reports/*_audit.json`** — 자동화 감사 보고서, QA 수치 확인
3. **`outputs/reports/*_qa.json`** — 각 산출 단계별 QA 요약
4. **`src/sl_accessibility/<모듈명>.py`** — 각 파일 상단 docstring에 입출력 명세 있음
5. **`docs/current_status_audit_2026-05-13.md`** — 최신 상태 전체 감사 기록

그래도 해결이 안 되면:

- **팀 채팅:** `[TODO: 채팅방 링크 추가]`
- **이슈 카드:** `[TODO: 이슈 트래커 링크 추가]`

---

## 9. 시나리오 작업자에게 — S1 / S3 / S4 미리 알기

현재 미완인 시나리오 3개가 협업자의 주요 작업 대상이다.

| 시나리오 | 내용 |
|---|---|
| **S1** | 정류장 추가 (버스/지하철 정류장 위치 변경·신설) |
| **S3** | 경사로 개선 (경사 비용 감소 효과 시뮬레이션) |
| **S4** | 기상 대응 시설 (악천후 비용 감소 효과 시뮬레이션) |

### 반드시 지켜야 할 공통 규칙

> **S0-M3 기준선에서 고정된 아래 세 가지를 시나리오에서 절대 바꾸지 않는다.**

1. **분석 hex 집합** — `qgis/out_analysis_hex_h3res9.gpkg` 기준 4,551개
2. **정규화 파라미터** — S0-M3 산출 시 사용한 Min-Max 범위 그대로 적용
3. **취약 threshold** — `0.0288` 고정 (시나리오별 재정규화 금지)

시나리오별로 Min-Max 정규화를 다시 하면 기준선과의 비교가 깨진다. 이 규칙은 `README.md` 11번 줄에도 명시되어 있다.

상세 작업 지침은 **`docs/SCENARIO_TASK_ASSIGNMENT.md`** 를 참고한다.

---

## 10. 체크리스트 — 협업자 첫날 (Day-1)

아래를 순서대로 완료하면 작업 시작 준비가 된 것이다.

- [ ] 환경 세팅 완료 (`.venv` 생성 + 패키지 설치)
- [ ] `pytest` 86 passed (또는 그 이상) 확인
- [ ] `validate-data` 통과 및 `outputs/reports/data_validation.json` 확인
- [ ] `docs/분석_진행_정리.md` 정독
- [ ] `docs/SCENARIO_TASK_ASSIGNMENT.md` 에서 본인 담당 시나리오 확인
- [ ] `<본인이름>_작업노트.ipynb` 파일 생성

---

*마지막 업데이트: 2026-05-17*
