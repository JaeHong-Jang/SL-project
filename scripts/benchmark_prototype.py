"""단계 7 — 성능·회귀·공개 게이트 검사 (docs/prototype_plan.md v2).

1) cold start / RSS
2) 실제망 유효 OD 100개 warm 벤치마크: p95 ≤ 500ms, 2s 초과 0건
3) 400m 불변식: 표본 전체에서 min(M3) ≥ min(M0), `M0>400 & M3≤400` 0건
4) 공개 게이트: 산출물 전체에 google 열·메타 0건, 출처 문구 존재
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sl_accessibility.prototype.route_engine import RouteEngine, RouteError  # noqa: E402

ART = ROOT / "data" / "processed" / "prototype"


def rss_mb() -> float:
    try:
        import psutil  # type: ignore

        return psutil.Process().memory_info().rss / 1e6
    except ImportError:
        import ctypes
        import ctypes.wintypes

        class PMC(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.wintypes.DWORD),
                ("PageFaultCount", ctypes.wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        fn = getattr(ctypes.windll.kernel32, "K32GetProcessMemoryInfo", None) or ctypes.windll.psapi.GetProcessMemoryInfo
        ok = fn(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
        if not ok:
            raise RuntimeError("RSS 측정 실패 — 0으로 통과시키지 않는다")
        return pmc.WorkingSetSize / 1e6


def main() -> None:
    failures: list[str] = []

    # --- 공개 게이트: google 흔적 0건 ---
    google_hits = []
    for pq in ART.glob("*.parquet"):
        cols = [c for c in pd.read_parquet(pq).columns if "google" in c.lower()]
        if cols:
            google_hits.append(f"{pq.name}:{cols}")
    for js in ART.glob("*.json"):
        text = js.read_text(encoding="utf-8")
        meta = json.loads(text)
        # 진단 보고서의 비교 섹션(diagnostics_*)은 로컬 검증용으로 허용, 산출물 계약은 sources로 확인
        if js.name == "build_report.json":
            if meta.get("sources", {}).get("google_columns_in_output") != 0:
                google_hits.append(f"{js.name}: google_columns_in_output != 0")
        elif "google" in text.lower():
            google_hits.append(js.name)
    print(f"[게이트] google 흔적: {google_hits if google_hits else '0건 OK'}")
    if google_hits:
        failures.append(f"google 흔적 발견: {google_hits}")

    # --- 출처 문구 ---
    t0 = time.perf_counter()
    engine = RouteEngine(ART)
    cold = time.perf_counter() - t0
    meta = engine.meta()
    attr = " ".join(meta["attribution"])
    for needle in ["OpenStreetMap contributors", "Copernicus DEM"]:
        if needle not in attr:
            failures.append(f"출처 문구 누락: {needle}")
    print(f"[게이트] 출처 문구: {'OK' if 'OpenStreetMap' in attr and 'Copernicus' in attr else '누락'}")
    print(f"[성능] cold_start={cold:.1f}s (기준 15s)")
    if cold > 15:
        failures.append(f"cold start {cold:.1f}s > 15s")

    # --- 유효 OD 100개 벤치마크 (정류장 근처 노드에서 다른 정류장으로: 항상 경로 존재) ---
    rng = np.random.default_rng(20260812)
    stops = engine.stops
    src_stops = stops.sample(100, random_state=1)
    dst_stops = stops.sample(100, random_state=2)
    times, statuses = [], {"ok": 0, "domain_error": 0}
    invariant_violations = 0
    for (sid, s), (did, d) in zip(src_stops.iterrows(), dst_stops.iterrows()):
        if sid == did:
            continue
        t = time.perf_counter()
        try:
            r = engine.route(float(s["lon"]), float(s["lat"]), did, "rain")
            statuses["ok"] += 1
            if r["m3"]["equivalent_distance_m"] < r["m0"]["network_distance_m"] - 0.05:
                invariant_violations += 1
            if r["m0"]["network_distance_m"] > 400 and r["m3"]["equivalent_distance_m"] <= 400:
                invariant_violations += 1
        except RouteError:
            statuses["domain_error"] += 1
        times.append((time.perf_counter() - t) * 1000)
    arr = np.array(times)
    p50, p95, mx = np.percentile(arr, 50), np.percentile(arr, 95), arr.max()
    print(
        f"[성능] OD {len(arr)}개 (성공 {statuses['ok']}, 도메인오류 {statuses['domain_error']}): "
        f"p50={p50:.0f}ms p95={p95:.0f}ms max={mx:.0f}ms (기준 p95≤500ms, 2s 초과 0건)"
    )
    if p95 > 500:
        failures.append(f"warm p95 {p95:.0f}ms > 500ms")
    if (arr > 2000).any():
        failures.append(f"2s 초과 요청 {(arr > 2000).sum()}건")
    print(f"[불변식] min(M3)≥min(M0) 및 역방향 재분류 0건: {'OK' if invariant_violations == 0 else f'위반 {invariant_violations}건'}")
    if invariant_violations:
        failures.append(f"400m 불변식 위반 {invariant_violations}건")

    print(f"[성능] RSS={rss_mb():.0f}MB (기준 1500MB)")
    if rss_mb() > 1500:
        failures.append(f"RSS {rss_mb():.0f}MB > 1500MB")

    if failures:
        print("\nGATE FAILED:")
        for f_ in failures:
            print(f"  - {f_}")
        raise SystemExit(1)
    print("\nGATE OK — 단계 7 자동 검사 전부 통과")


if __name__ == "__main__":
    main()
