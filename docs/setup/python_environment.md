# Python 환경 설정

## 확인된 문제

이 PC에서 `python.exe`는 실제 Python이 아니라 Windows Store shim으로 잡힌다.

```text
%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe
```

그래서 `python --version`이나 `python -m pytest`가 바로 동작하지 않았다.

다행히 `uv.exe`가 설치되어 있어 프로젝트용 `.venv`를 만들 수 있었다.

## 현재 작동한 설정

프로젝트 경로 안에서 다음 명령이 동작했다.

```powershell
$env:UV_CACHE_DIR='.uv-cache2'
uv venv --python 3.14
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt
$env:PYTHONPATH='src'
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

검증 결과:

```text
2026-06-11 재확인 기준 86 passed
```

## 왜 `python -m pip install -e .`를 쓰지 않았나

원 작업공간 경로에 한글과 공백이 포함되어 있었다.
`uv run python` 또는 editable install 과정에서 setuptools가 cache/build 폴더를 만들다가 Windows 권한 오류가 발생했다. 그래서 현재는 editable install 대신 다음 방식을 사용한다.

```powershell
$env:PYTHONPATH='src'
```

이렇게 하면 패키지를 wheel로 빌드하지 않고도 `src/sl_accessibility`를 바로 import할 수 있다.

## 전체 의존성 설치

```powershell
$env:UV_CACHE_DIR='.uv-cache2'
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt
```

현재 `geopandas`, `shapely`, `pyproj`, `pyarrow`, `polars` 설치와 import 확인이 완료되었다.

## 검증 명령

```powershell
$env:PYTHONPATH='src'
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.venv\Scripts\python.exe -m sl_accessibility.cli validate-data
```

`validate-data` 결과는 다음 파일에 저장된다.

```text
outputs/reports/data_validation.json
```

## 대안

나중에 geospatial 패키지 설치가 꼬이면 conda-forge 환경을 쓰는 것이 더 안정적이다.

```powershell
conda create -n sl-access python=3.11 geopandas shapely pyproj pyogrio pandas pyarrow polars networkx pyyaml typer pytest -c conda-forge
conda activate sl-access
$env:PYTHONPATH='src'
pytest -q -p no:cacheprovider
```
