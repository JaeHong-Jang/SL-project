"""단계 4 — FastAPI 서비스 (docs/prototype_plan.md v2 §7).

실행:
    .venv/Scripts/python.exe -m uvicorn sl_accessibility.prototype.api:app --port 8000

같은 origin에서 프론트 빌드(dist)와 stops.geojson도 서비스한다.
로그에는 프로필·처리시간·오류 코드만 남기고 개인 식별정보를 저장하지 않는다.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from sl_accessibility.prototype.route_engine import RouteEngine, RouteError
from sl_accessibility.prototype.schemas import RouteRequest

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACTS = ROOT / "data" / "processed" / "prototype"
FRONTEND_DIST = ROOT / "prototype" / "frontend" / "dist"

logger = logging.getLogger("prototype.api")

# RouteError 코드 → HTTP 상태 매핑 (일관 계약)
ERROR_STATUS = {
    "origin_snap_failed": 422,
    "unknown_weather": 422,
    "same_node": 422,
    "unknown_stop": 404,
    "no_path": 404,
}


def create_app(artifacts_dir: Path | None = None) -> FastAPI:
    art_dir = Path(artifacts_dir or DEFAULT_ARTIFACTS)
    app = FastAPI(title="M3 보행부담 경로 프로토타입", docs_url="/api/docs")
    engine = RouteEngine(art_dir)
    stops_geojson_path = art_dir / "stops.geojson"

    @app.get("/api/meta")
    def meta() -> dict:
        return engine.meta()

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "graphs_loaded": sorted(engine.graphs.keys()),
            "nodes": int(engine.n_nodes),
            "stops": int(len(engine.stops)),
            "data_version": engine.meta()["data_version"],
        }

    @app.get("/api/stops")
    def stops() -> FileResponse:
        return FileResponse(stops_geojson_path, media_type="application/geo+json")

    @app.post("/api/route")
    def route(req: RouteRequest) -> JSONResponse:
        t0 = time.perf_counter()
        try:
            result = engine.route(
                req.origin.lng, req.origin.lat, req.destination.stop_id, req.weather
            )
        except RouteError as e:
            status = ERROR_STATUS.get(e.code, 422)
            logger.info("route error code=%s elapsed_ms=%.0f", e.code, (time.perf_counter() - t0) * 1000)
            raise HTTPException(status_code=status, detail={"code": e.code, "message": str(e)})
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(
            "route ok profile=%s elapsed_ms=%.0f", result["request"]["profile"], elapsed
        )
        result["metadata"] = {
            "data_version": engine.meta()["data_version"],
            "profile_id": result["request"]["profile"],
            "elapsed_ms": round(elapsed),
        }
        return JSONResponse(result)

    if FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
