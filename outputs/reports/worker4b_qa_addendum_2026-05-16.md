# Worker 4b QA Addendum

작성자 역할: Worker 4b, Worker 3/4 산출물 독립 재검토 QA  
작성 시각: 2026-05-16 18:25 KST  
범위: 기존 Worker 3 재생성/검증 로그와 Worker 4 QA 보고서를 읽기 전용으로 대조하고, 검토 addendum만 추가

## 1. 검토 대상

| 구분 | 확인 파일 |
|---|---|
| Worker 4 QA 보고서 | `.omx/worker4_qa_report_2026-05-16.md` |
| Worker 3 로그 | `outputs/reports/worker3_build_transit_d_candidates.log` |
| Worker 3 로그 | `outputs/reports/worker3_build_vulnerability_final.log` |
| Worker 3 로그 | `outputs/reports/worker3_export_hidden_vulnerability_diagnostics.log` |
| Worker 3 로그 | `outputs/reports/worker3_validate_data.log` |
| Worker 3 로그 | `outputs/reports/worker3_validate_vulnerability_final.log` |
| QA 산출물 | `outputs/reports/data_validation.json` |
| QA 산출물 | `outputs/reports/data_validation.manifest.json` |
| QA 산출물 | `outputs/reports/hex_vulnerability_final_qa.json` |
| QA 산출물 | `outputs/reports/hex_vulnerability_final_audit.json` |
| QA 산출물 | `outputs/reports/hidden_vulnerability_reason_diagnostics_qa.json` |
| Manifest 설계 문서/코드 | `docs/run_manifest.md`, `src/sl_accessibility/run_manifest.py`, `src/sl_accessibility/cli.py` |

## 2. 확인한 증거

### Worker 3 로그

Worker 3 로그 5개는 모두 Windows PowerShell `Start-Transcript` 형식이며 각 24줄이다. 각 로그에는 실행 명령, 시작/종료 시각, PowerShell 환경 정보가 남아 있다.

| 로그 | 명령 | 기록 시각 |
|---|---|---|
| `worker3_build_transit_d_candidates.log` | `build-transit-d-candidates` | 2026-05-16 18:19:10-18:19:15 KST |
| `worker3_build_vulnerability_final.log` | `build-vulnerability-final` | 2026-05-16 18:19:28-18:19:29 KST |
| `worker3_export_hidden_vulnerability_diagnostics.log` | `export-hidden-vulnerability-diagnostics` | 2026-05-16 18:19:40-18:19:41 KST |
| `worker3_validate_data.log` | `validate-data` | 2026-05-16 18:19:50-18:20:02 KST |
| `worker3_validate_vulnerability_final.log` | `validate-vulnerability-final` | 2026-05-16 18:20:11-18:20:12 KST |

주의: 이 transcript들은 CLI stdout/stderr, `$LASTEXITCODE` 값, `Traceback`/오류 메시지, `pass` echo를 직접 포함하지 않는다. 따라서 "명령이 호출되었다"는 증거로는 충분하지만, 단독으로 성공 종료를 입증하기에는 약하다.

### 산출물 갱신 시각

Worker 3 로그 시각과 다음 산출물의 mtime이 대응한다.

| 산출물 | mtime KST | 크기 |
|---|---:|---:|
| `qgis/out_transit_d_candidates.gpkg` | 2026-05-16 18:19:15 | 1,843,200 bytes |
| `qgis/out_hex_vulnerability_final.gpkg` | 2026-05-16 18:19:29 | 2,703,360 bytes |
| `data/derived/hex_vulnerability_final.parquet` | 2026-05-16 18:19:29 | 1,268,803 bytes |
| `outputs/reports/hex_vulnerability_final_qa.json` | 2026-05-16 18:19:29 | 636 bytes |
| `outputs/reports/hidden_vulnerability_reason_diagnostics.csv` | 2026-05-16 18:19:41 | 298,197 bytes |
| `qgis/out_hidden_vulnerability_reason_diagnostics.gpkg` | 2026-05-16 18:19:41 | 581,632 bytes |
| `outputs/reports/data_validation.json` | 2026-05-16 18:19:58 | 7,030 bytes |
| `outputs/reports/data_validation.manifest.json` | 2026-05-16 18:20:02 | 10,893 bytes |
| `outputs/reports/hex_vulnerability_final_audit.json` | 2026-05-16 18:20:12 | 2,724 bytes |

mtime는 Worker 3 재실행과 산출물 갱신의 정황 증거로 충분하다. 다만 로그가 exit code를 담지 않아 "산출 후 manifest 작성 단계에서 실패했는지"까지는 배제하지 못한다.

### QA JSON 내용

확인한 QA 수치:

- `data_validation.json`: 보행망, 정류장 승하차, ASOS, 2025-11 생활인구 30개 파일 샘플 계약이 모두 `ok: true`.
- `hex_vulnerability_final_qa.json`: 4,551 hex, 분석 유효 4,383, 취약 877, hidden vulnerable 632, threshold `0.028838610230807495`.
- `hex_vulnerability_final_audit.json`: `status: pass`, Parquet/GPKG/QA count와 threshold 일치, hidden 공식 mismatch 0, official 400m 공식 mismatch 0, CRS `EPSG:5179`, geometry invalid 0.
- `hidden_vulnerability_reason_diagnostics_qa.json`: hidden vulnerable 632건, 주요 원인 분포 기록. `slope_weather_penalty` 191, `high_demand` 167, `high_demand_plus_slope_weather_penalty` 140 등.

### Manifest 확인

파일 시스템에서 발견된 manifest는 `outputs/reports/data_validation.manifest.json` 하나뿐이다.

`data_validation.manifest.json`에 대해 별도 Node 기반 구조 검증을 수행했다. 결과:

- command: `validate-data`
- created_at_utc: `2026-05-16T09:20:02.548240+00:00`
- config 집계 hash 일치: true
- input 집계 hash 일치: true
- output 집계 hash 일치: true
- config/input/output entry 수: 39
- 현재 파일 존재/크기 불일치: 0

추가 spot-check:

- `outputs/reports/data_validation.json` 현재 SHA-256은 manifest의 출력 SHA-256 `959e97c328865916d5b8ac668029dfc8c645278ee0f575468e03fb4288d6a9de`와 일치.
- `configs/default.yaml`, `configs/data_sources.yaml`, `configs/model_params.yaml` 현재 SHA-256도 manifest 기록과 일치.

공식 CLI 기반 `validate-run-manifest` 재실행은 현재 Linux 환경에서 수행하지 못했다. `.venv-linux/bin/python3`는 있으나 `pytest`와 `yaml`이 없어 `tests/test_run_manifest.py`와 `sl_accessibility.run_manifest` import가 실패했다.

## 3. Manifest 반영 여부

`docs/run_manifest.md`와 `src/sl_accessibility/cli.py` 기준으로 CLI는 주요 산출물 생성 후 anchor 파일의 stem에 `.manifest.json`을 붙인 sidecar manifest를 써야 한다.

현재 확인 결과:

| Worker 3 명령 | 기대 manifest | 현재 상태 |
|---|---|---|
| `build-transit-d-candidates` | `qgis/out_transit_d_candidates.manifest.json` | 없음 |
| `build-vulnerability-final` | `outputs/reports/hex_vulnerability_final_qa.manifest.json` | 없음 |
| `export-hidden-vulnerability-diagnostics` | `outputs/reports/hidden_vulnerability_reason_diagnostics_qa.manifest.json` | 없음 |
| `validate-data` | `outputs/reports/data_validation.manifest.json` | 있음, 구조/크기/집계 hash 확인 |
| `validate-vulnerability-final` | `outputs/reports/hex_vulnerability_final_audit.manifest.json` | 없음 |

따라서 manifest 반영은 부분적이다. `validate-data`는 충분히 반영되었지만, Worker 3의 나머지 4개 재생성/검증 명령은 현재 작업공간에 sidecar manifest가 남아 있지 않다.

특히 현재 `src/sl_accessibility/cli.py`에는 위 명령들 모두 `_write_cli_run_manifest(...)` 호출이 존재한다. sidecar가 없는 원인은 다음 둘 중 하나일 가능성이 있다.

- Worker 3 실행 시점의 코드가 현재 코드와 달랐거나,
- 산출물 작성 이후 manifest 작성 또는 echo 단계에서 실패했으나 transcript가 실패 원인을 기록하지 못했거나.

현재 증거만으로는 두 가능성을 구분할 수 없다.

## 4. Worker 4 보고서에 대한 재검토 의견

Worker 4 보고서의 핵심 관찰은 대체로 현재 파일 상태와 일치한다.

- Git 저장소로 인식되지 않는다는 지적은 재확인했다. `.git` 디렉터리명은 있으나 내부 파일이 없고 `git rev-parse --show-toplevel` 및 `git status --short`가 실패한다.
- WSL/Linux 환경에서 테스트 재현이 어렵다는 지적은 여전히 유효하다. 새로 보이는 `.venv-linux`도 최소 Python만 있고 `pytest`, `yaml`이 없다.
- final vulnerability audit가 `status: pass`라는 기록은 현재 `hex_vulnerability_final_audit.json`과 일치한다.
- hidden vulnerability 632건 및 원인진단 QA 수치는 현재 JSON과 일치한다.

보강할 점은 manifest coverage다. Worker 4 보고서는 기존 QA JSON 중심으로 충분성을 평가했지만, 현재 코드/문서 기준의 sidecar manifest 누락은 별도 리스크로 명시해야 한다.

## 5. 발견 이슈 / 남은 리스크

| 심각도 | 이슈 | 근거 | 영향 |
|---|---|---|---|
| 높음 | Worker 3 transcript가 성공 종료를 단독 입증하지 못함 | 로그 5개에 exit code/stdout/stderr가 없음 | 산출물 mtime과 QA JSON으로 보강 가능하지만, 실패한 후 중간 산출물만 남은 경우를 완전히 배제할 수 없음 |
| 높음 | Worker 3 명령 5개 중 4개 manifest sidecar 누락 | 파일 시스템에는 `data_validation.manifest.json`만 존재 | 입력/config/output hash 기반 재현성 기록이 final vulnerability, diagnostics, transit 후보에 남지 않음 |
| 중간 | `build-transit-d-candidates` 산출물의 별도 QA JSON 부재 | GPKG mtime/크기만 확인 가능, transcript stdout도 없음 | 후보 수, CRS, geometry validity, boundary outside QA를 독립 확인하기 어려움 |
| 중간 | 현재 Linux 환경에서 공식 테스트/manifest validator 재실행 불가 | `.venv-linux`에 `pytest`, `yaml` 없음 | QA addendum은 구조 검증과 기존 산출물 검토에 의존 |
| 중간 | Git 기반 변경 추적 불가 | `.git` 내부 파일 없음, git 명령 실패 | 다른 worker 변경과 이번 QA addendum만의 변경 범위를 Git으로 증명할 수 없음 |
| 낮음 | data_validation manifest의 입력 SHA 전체 재계산은 미수행 | 입력 전체가 수 GB 규모 | manifest 내부 집계 hash/파일 크기와 주요 출력/config SHA는 확인했으나 모든 입력 내용 hash 재계산은 후속 검증 권고 |

## 6. 권고

1. Windows PowerShell 정상 Python 환경에서 Worker 3 명령을 다시 실행하거나, 최소한 누락된 sidecar manifest를 생성하는 재검증을 수행한다.
2. 재실행 로그에는 `$LASTEXITCODE`를 명시적으로 출력한다. 예: `Write-Output "LASTEXITCODE=$code"`를 `Stop-Transcript` 전에 남긴다.
3. 다음 manifest 파일의 존재와 `validate-run-manifest` 통과를 확인한다.
   - `qgis/out_transit_d_candidates.manifest.json`
   - `outputs/reports/hex_vulnerability_final_qa.manifest.json`
   - `outputs/reports/hidden_vulnerability_reason_diagnostics_qa.manifest.json`
   - `outputs/reports/hex_vulnerability_final_audit.manifest.json`
4. `build-transit-d-candidates`에 대해 후보 row count, CRS, geometry validity, boundary outside count를 담은 QA JSON 또는 audit 로그를 남긴다.
5. 현재 작업공간이 Git 없는 복사본인지, 실제 Git 루트가 따로 있는지 확정한다. 이후 QA/산출물 변경 추적은 유효한 Git 루트 또는 별도 checksum inventory로 관리한다.

## 7. Worker 4b 변경 내역

이번 Worker 4b 작업에서 추가한 파일은 이 addendum 하나뿐이다.

```text
outputs/reports/worker4b_qa_addendum_2026-05-16.md
```
