# Run Manifest

파이프라인 CLI는 주요 산출물 생성 후 sidecar JSON manifest를 남긴다. 기본 파일명은
주 산출물 또는 QA report의 stem에 `.manifest.json`을 붙인다.

예:

- `outputs/reports/hex_vulnerability_final_qa.json`
- `outputs/reports/hex_vulnerability_final_qa.manifest.json`

## Schema v1.0

필수 최상위 필드:

- `schema_version`: 현재 `"1.0"`
- `created_at_utc`: manifest 생성 시각
- `command`: 실행한 CLI 명령 이름
- `project_root`: 파일 경로 검증 기준 root
- `environment`: Python/platform 정보
- `cli_args`: CLI 인자 값
- `cli_args_hash`: `cli_args`의 정렬 JSON SHA-256
- `config.files`: `configs/default.yaml`, `configs/data_sources.yaml`, `configs/model_params.yaml`
- `config.hash`: config 파일 entry 집계 SHA-256
- `inputs`: 입력 파일 entry 목록
- `input_hash`: 입력 파일 entry 집계 SHA-256
- `outputs`: 출력 파일 entry 목록
- `output_hash`: 출력 파일 entry 집계 SHA-256

파일 entry 필드:

- `role`: 입력/출력 역할 이름
- `path`: project root 기준 상대 경로 또는 절대 경로. 새 manifest는 상대 경로를 `/` 구분자로 기록한다.
- `exists`: manifest 작성 시점 존재 여부
- `size_bytes`: 파일 크기
- `sha256`: 파일 내용 SHA-256

## Validation

```bash
sl-accessibility validate-run-manifest outputs/reports/hex_vulnerability_final_qa.manifest.json
```

검증은 필수 키 존재 여부, schema version, `cli_args_hash`, config/input/output 집계 hash,
개별 파일 hash 일치 여부를 확인한다. Windows에서 생성된 기존 manifest의 `\` 상대 경로도
검증 시 project root 기준 경로로 해석한다.
