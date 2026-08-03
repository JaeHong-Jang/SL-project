"""Build a Korean interactive HTML map for S1/S3/S4 scenario inspection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
QGIS_DIR = ROOT / "qgis"
SUMMARY_PATH = ROOT / "outputs" / "reports" / "scenario_counterfactual" / (
    "scenario_counterfactual_runner_summary.json"
)
OUT_DIR = ROOT / "outputs" / "maps"
OUT_HTML = OUT_DIR / "scenario_interactive_map.html"
OUT_MANIFEST = OUT_DIR / "scenario_interactive_map_manifest.json"
CRS_WEB = "EPSG:4326"
WALKING_SPEED_M_PER_MIN = 67.0


REASON_LABELS = {
    "high_demand": "\uc218\uc694\uc555\ub825 \ub192\uc74c",
    "high_demand_plus_near_400m_distance": "\uace0\uc218\uc694 + 400m \uac70\ub9ac\ubd80\ub2f4",
    "high_demand_plus_slope_weather_penalty": "\uace0\uc218\uc694 + \uacbd\uc0ac\u00b7\uae30\uc0c1 \ubd80\ub2f4",
    "mixed": "\ubcf5\ud569 \uc6d0\uc778",
    "near_400m_distance": "400m \uac70\ub9ac\ubd80\ub2f4",
    "slope_weather_penalty": "\uacbd\uc0ac\u00b7\uae30\uc0c1 \ubd80\ub2f4",
}

REASON_COLORS = {
    "high_demand": "#8c6d31",
    "high_demand_plus_near_400m_distance": "#d95f02",
    "high_demand_plus_slope_weather_penalty": "#b2182b",
    "mixed": "#969696",
    "near_400m_distance": "#fdae61",
    "slope_weather_penalty": "#ef3b2c",
}

LAYER_META = {
    "hidden": {
        "label": "\uae30\uc874 hidden \ucde8\uc57d\uc9c0\uc5ed",
        "description": "\ud604\ud589 400m \uae30\uc900\uc740 \uc591\ud638\uc9c0\ub9cc S0-M3 \ubaa8\ub378\uc5d0\uc11c\ub294 \ucde8\uc57d\ud55c hex",
        "color": "#b2182b",
        "type": "polygon",
    },
    "s1Reduced": {
        "label": "S1 \ubd80\ub2f4 \uac10\uc18c hex(\ud574\uc18c \uc544\ub2d8)",
        "description": "\ud6c4\ubcf4 \uc815\ub958\uc7a5 48\uac1c \ub3d9\uc2dc \ubc18\uc601 \uc2dc \uc811\uadfc\ube44\uc6a9 \ub610\ub294 \ucde8\uc57d\ub3c4 \ubd80\ub2f4\uc774 \uac10\uc18c\ud55c hex. \uc774 \ub808\uc774\uc5b4\ub294 \ud574\uc18c \uc758\ubbf8\uac00 \uc544\ub2d9\ub2c8\ub2e4.",
        "color": "#f59e0b",
        "type": "polygon",
    },
    "s1Resolved": {
        "label": "S1 hidden \ud574\uc18c hex(\ucde8\uc57d \ud574\uc81c)",
        "description": "\uc6d0\ub798 hidden \ucde8\uc57d\uc9c0\uc5ed \uc911 S1 \uc0c1\ud55c\uc120\uc5d0\uc11c \ucde8\uc57d\uc5d0\uc11c \ubc97\uc5b4\ub09c hex",
        "color": "#15803d",
        "type": "polygon",
    },
    "s1Candidates": {
        "label": "S1 \ud6c4\ubcf4 \uc815\ub958\uc7a5",
        "description": "\uc815\ub958\uc7a5 \ucd94\uac00 \ud6c4\ubcf4 48\uac1c \uc704\uce58",
        "color": "#facc15",
        "type": "point",
    },
    "busStops": {
        "label": "\uae30\uc874 \ubc84\uc2a4 \uc815\ub958\uc7a5",
        "description": "\uae30\uc874 \ubc84\uc2a4 \uc815\ub958\uc7a5 \uc704\uce58. \ud074\ub9ad\ud558\uba74 \uc815\ub958\uc7a5\uba85\uacfc \uc2b9\ucc28 \uc218\uc694 \uc9c0\ud45c\ub97c \ud655\uc778\ud569\ub2c8\ub2e4.",
        "color": "#f59e0b",
        "type": "point",
    },
    "subwayStops": {
        "label": "\uae30\uc874 \uc9c0\ud558\ucca0\uc5ed",
        "description": "\uae30\uc874 \uc9c0\ud558\ucca0\uc5ed \uc704\uce58. \ud074\ub9ad\ud558\uba74 \uc5ed\uba85\uacfc \uc218\uc694 \uc9c0\ud45c\ub97c \ud655\uc778\ud569\ub2c8\ub2e4.",
        "color": "#2563eb",
        "type": "point",
    },
    "s3Reduced": {
        "label": "S3 \ubd80\ub2f4 \uac10\uc18c hex(\ud574\uc18c \uc544\ub2d8)",
        "description": "\uae09\uacbd\uc0ac edge cap15 \ubc18\uc0ac\uc2e4\uc5d0\uc11c \uc811\uadfc\ube44\uc6a9 \ub610\ub294 \ucde8\uc57d\ub3c4 \ubd80\ub2f4\uc774 \uac10\uc18c\ud55c hex. \uc774 \ub808\uc774\uc5b4\ub294 \ud574\uc18c \uc758\ubbf8\uac00 \uc544\ub2d9\ub2c8\ub2e4.",
        "color": "#0891b2",
        "type": "polygon",
    },
    "s3Resolved": {
        "label": "S3 hidden \ud574\uc18c hex(\ucde8\uc57d \ud574\uc81c)",
        "description": "\uc6d0\ub798 hidden \ucde8\uc57d\uc9c0\uc5ed \uc911 S3 \uacbd\uc0ac \uac1c\uc120 \ubc18\uc0ac\uc2e4\uc5d0\uc11c \ucde8\uc57d\uc5d0\uc11c \ubc97\uc5b4\ub09c hex. \ud604\uc7ac \uacb0\uacfc\ub294 0\uac1c\uc785\ub2c8\ub2e4.",
        "color": "#15803d",
        "type": "polygon",
    },
    "s3Edges": {
        "label": "S3 \uacbd\uc0ac \uac1c\uc120 \ub300\uc0c1 \uad6c\uac04",
        "description": "grade_abs_percent > 30 edge\ub97c 15%\ub85c \uc644\ud654\ud55c \ub300\uc0c1 \uad6c\uac04",
        "color": "#c2410c",
        "type": "line",
    },
    "s4Reduced": {
        "label": "S4 \ube44\uc6a9 \uac10\uc18c hex(\ud574\uc18c \uc544\ub2d8)",
        "description": "\uae30\uc0c1\ud56d \uc81c\uac70 \uc0c1\ud55c\uc120\uc5d0\uc11c \uc811\uadfc\ube44\uc6a9 \ub610\ub294 \ucde8\uc57d\ub3c4 \ubd80\ub2f4\uc774 \uac10\uc18c\ud55c hex. \uc774 \ub808\uc774\uc5b4\ub294 \ud574\uc18c \uc758\ubbf8\uac00 \uc544\ub2d9\ub2c8\ub2e4.",
        "color": "#60a5fa",
        "type": "polygon",
    },
    "s4Resolved": {
        "label": "S4 hidden \ud574\uc18c hex(\ucde8\uc57d \ud574\uc81c)",
        "description": "\uc6d0\ub798 hidden \ucde8\uc57d\uc9c0\uc5ed \uc911 \uae30\uc0c1\ud56d \uc81c\uac70 \uc0c1\ud55c\uc120\uc5d0\uc11c \ucde8\uc57d\uc5d0\uc11c \ubc97\uc5b4\ub09c hex",
        "color": "#15803d",
        "type": "polygon",
    },
    "s4Priority": {
        "label": "S4 \uae30\uc0c1 \ub300\uc751 Top20",
        "description": "\uae30\uc0c1 \ub300\uc751 \uc6b0\uc120 \uac80\ud1a0 \ud6c4\ubcf4 20\uac1c",
        "color": "#7c3aed",
        "type": "point",
    },
}

PRESETS = {
    "baseline": {
        "label": "\uae30\uc900 \ubcf4\uae30",
        "layers": ["hidden", "busStops", "subwayStops"],
        "summary": "\uc6d0\ub798 hidden \ucde8\uc57d\uc9c0\uc5ed\ub9cc \ud45c\uc2dc\ud569\ub2c8\ub2e4. \uc0c9\uc740 \ucde8\uc57d \uc6d0\uc778 \ubd84\ub958\uc785\ub2c8\ub2e4.",
    },
    "s1": {
        "label": "S1 \uc815\ub958\uc7a5",
        "layers": ["hidden", "busStops", "subwayStops", "s1Reduced", "s1Resolved", "s1Candidates"],
        "summary": "\uae30\uc874 hidden \uc704\uc5d0 S1 \ud6c4\ubcf4 \uc815\ub958\uc7a5\uacfc \ucde8\uc57d\ub3c4 \uac10\uc18c\u00b7\ud574\uc18c hex\ub97c \uc62c\ub824 \uc804\ud6c4 \uad00\uacc4\ub97c \ud655\uc778\ud569\ub2c8\ub2e4.",
    },
    "s3": {
        "label": "S3 \uacbd\uc0ac",
        "layers": ["hidden", "busStops", "subwayStops", "s3Reduced", "s3Resolved", "s3Edges"],
        "summary": "\uacbd\uc0ac 30% \ucd08\uacfc edge cap15 \ubc18\uc0ac\uc2e4 \uacb0\uacfc\ub97c \ubd05\ub2c8\ub2e4. \ucde8\uc57d\ub3c4 \uac10\uc18c hex\ub294 \uc788\uc9c0\ub9cc hidden \ud574\uc18c\ub294 \uc544\uc9c1 0\uac1c\uc785\ub2c8\ub2e4.",
    },
    "s4": {
        "label": "S4 \uae30\uc0c1",
        "layers": ["hidden", "busStops", "subwayStops", "s4Reduced", "s4Resolved", "s4Priority"],
        "summary": "\uae30\uc0c1\ud56d \uc81c\uac70 \uc0c1\ud55c\uc120\uc5d0\uc11c \ud574\uc18c\ub418\ub294 hidden\uacfc \uae30\uc0c1 \ub300\uc751 Top20 \ud6c4\ubcf4\ub97c \ube44\uad50\ud569\ub2c8\ub2e4.",
    },
    "compare": {
        "label": "\uc804\uccb4 \ube44\uad50",
        "layers": ["hidden", "busStops", "subwayStops", "s1Resolved", "s1Candidates", "s3Resolved", "s3Reduced", "s3Edges", "s4Resolved", "s4Priority"],
        "summary": "\uc138 \uc2dc\ub098\ub9ac\uc624\uc758 \ud575\uc2ec \uacb0\uacfc\ub9cc \uacb9\uccd0 \ubd05\ub2c8\ub2e4. \ubcf5\uc7a1\ud558\uba74 S1/S3/S4 \ubc84\ud2bc\uc73c\ub85c \ub098\ub220 \ubcf4\uc138\uc694.",
    },
}

UI_TEXT = {
    "title": "S1\u00b7S3\u00b7S4 \uc811\uadfc\uc131 \uc2dc\ub098\ub9ac\uc624 \ube44\uad50 \uc9c0\ub3c4",
    "subtitle": "S0-M3 \uae30\uc900\uac12\uc744 \uace0\uc815\ud55c \uc0c1\ud0dc\uc5d0\uc11c \uc6d0\ub798 hidden \ucde8\uc57d\uc9c0\uc5ed\uacfc \uc2dc\ub098\ub9ac\uc624\ubcc4 \ubcc0\ud654 \uc704\uce58\ub97c \ube44\uad50\ud569\ub2c8\ub2e4.",
    "notice": "\uc2e4\uc81c \ud0d1\uc2b9\uc218\uc694 \uc608\uce21\uc774 \uc544\ub2c8\ub77c \ubaa8\ub378 \uc870\uac74\ud558\uc758 \uc811\uadfc\ube44\uc6a9\u00b7\ucde8\uc57d\ub3c4 \ubd80\ub2f4 \ubcc0\ud654\uc785\ub2c8\ub2e4. S1/S4\ub294 \uc0c1\ud55c\uc120 \uc2e4\ud5d8, S3\ub294 \uacbd\uc0ac \uac1c\uc120 \ubc18\uc0ac\uc2e4 \uc2e4\ud5d8\uc73c\ub85c \ud574\uc11d\ud569\ub2c8\ub2e4.",
    "quickView": "\ube60\ub978 \ubcf4\uae30",
    "legend": "\ud55c\uae00 \ubc94\ub840 / \ub808\uc774\uc5b4",
    "reasons": "\uae30\uc874 hidden \ucde8\uc57d\uc9c0\uc5ed \uc6d0\uc778",
    "reasonHelp": "\uc544\ub798 \uc6d0\uc778 \ubc94\ub840\ub97c \ub204\ub974\uba74 \ud574\ub2f9 \uc6d0\uc778\ub9cc \uc228\uae30\uac70\ub098 \ub2e4\uc2dc \ud45c\uc2dc\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
    "summary": "\ud604\uc7ac \ubcf4\uae30 \uc694\uc57d",
    "selected": "\uc120\ud0dd\ud55c \uc704\uce58",
    "detailPlaceholder": "\uc9c0\ub3c4\uc5d0\uc11c hex, \ud6c4\ubcf4 \uc815\ub958\uc7a5, \uac1c\uc120 edge\ub97c \ud074\ub9ad\ud558\uba74 \uc0c1\uc138\uac12\uc774 \uc5ec\uae30\uc5d0 \ud45c\uc2dc\ub429\ub2c8\ub2e4.",
    "footer": "\uc0dd\uc131 \ud30c\uc77c: outputs/maps/scenario_interactive_map.html<br />\uc6d0\ubcf8: qgis/*.gpkg, outputs/reports/scenario_counterfactual/*.json<br />\ubc30\uacbd\uc9c0\ub3c4\uc640 Leaflet \ub77c\uc774\ube0c\ub7ec\ub9ac\ub294 \uc628\ub77c\uc778 \uc811\uc18d\uc774 \ud544\uc694\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.",
    "custom": "\uc0ac\uc6a9\uc790 \uc870\ud569",
    "customSummary": "\uc0ac\uc6a9\uc790\uac00 \ubc94\ub840\ub97c \uc9c1\uc811 \uc870\ud569\ud55c \ubcf4\uae30\uc785\ub2c8\ub2e4.",
    "mapAria": "S1 S3 S4 \uc2dc\ub098\ub9ac\uc624 \uc9c0\ub3c4",
    "fields": {
        "hexId": "hex ID",
        "admin": "\ud589\uc815\ub3d9",
        "reason": "\uc6d0\uc778",
        "colorMeaning": "\uc0c9 \uc758\ubbf8",
        "baselineVulnerability": "\uae30\uc900 \ucde8\uc57d\ub3c4",
        "scenarioVulnerability": "\uc2dc\ub098\ub9ac\uc624 \ud6c4",
        "deltaVulnerability": "\u0394\ucde8\uc57d\ub3c4",
        "baselineCost": "\uae30\uc900 \uc811\uadfc\ube44\uc6a9",
        "scenarioCost": "\uc2dc\ub098\ub9ac\uc624 \uc811\uadfc\ube44\uc6a9",
        "deltaCost": "\u0394\uc811\uadfc\ube44\uc6a9",
        "deltaCostPct": "\u0394\uc811\uadfc\ube44\uc6a9 \ube44\uc728",
        "m0Cost": "M0 \uc21c\uc218\uac70\ub9ac",
        "m1Cost": "M1 \uacbd\uc0ac\ubc18\uc601 \ube44\uc6a9",
        "m2Cost": "M2 \uae30\uc0c1\uac00\uc0b0 \ube44\uc6a9",
        "m3Cost": "M3 \ucd5c\uc885 \uc811\uadfc\ube44\uc6a9",
        "m3Minutes": "M3 \ube44\uc6a9\ud658\uc0b0 \ub3c4\ubcf4\uc2dc\uac04",
        "slopeIncrement": "\uacbd\uc0ac \uc99d\uac00\ubd84",
        "weatherIncrement": "\uae30\uc0c1 \uac00\uc0b0\ubd84",
        "interactionIncrement": "\uacbd\uc0ac\u00d7\uae30\uc0c1 \uc0c1\ud638\uc791\uc6a9",
        "totalEnvIncrement": "\ucd1d \ud658\uacbd\ubd80\ub2f4",
        "nearestBus": "\uac00\uc7a5 \uac00\uae4c\uc6b4 \ubc84\uc2a4",
        "nearestSubway": "\uac00\uc7a5 \uac00\uae4c\uc6b4 \uc9c0\ud558\ucca0",
        "straightDistance": "\uc9c1\uc120\uac70\ub9ac",
        "straightTime": "\uc9c1\uc120\uac70\ub9ac \ud658\uc0b0 \uc2dc\uac04",
        "stopName": "\uc815\ub958\uc7a5/\uc5ed\uba85",
        "stopId": "\uc815\ub958\uc7a5 ID",
        "transitMode": "\uad50\ud1b5\uc218\ub2e8",
        "passengers": "\uc2b9\ucc28 \uc218\uc694 \uc9c0\ud45c",
        "rankImprovement": "\uc21c\uc704 \uac1c\uc120",
        "seniorPopulation": "\uace0\ub839 \uc778\uad6c",
        "candidateRank": "\ud6c4\ubcf4 \uc21c\uc704",
        "recommendedReview": "\uad8c\uc7a5 \uac80\ud1a0",
        "weatherRank": "\uae30\uc0c1 \ud6c4\ubcf4 \uc21c\uc704",
        "weatherAction": "\uae30\uc0c1 \ub300\uc751",
        "grade": "\uae30\uc874 \uacbd\uc0ac",
        "edgeCostReduction": "edge \ube44\uc6a9 \uac10\uc18c",
        "location": "\uc704\uce58",
        "s1CandidateRank": "S1 \ud6c4\ubcf4 \uc21c\uc704",
        "s4CandidateRank": "S4 \ud6c4\ubcf4 \uc21c\uc704",
        "s3Grade": "S3 \ub300\uc0c1 \uacbd\uc0ac",
    },
    "metrics": {
        "s1": "S1 \uac1c\uc120 hex / \ud574\uc18c hidden<br />\uc0c1\ud55c\uc120, \ud6c4\ubcf4 48\uac1c \ub3d9\uc2dc \ubc18\uc601",
        "s3": "S3 \uac1c\uc120 hex / \ud574\uc18c hidden<br />\uacbd\uc0ac cap15 \ubc18\uc0ac\uc2e4",
        "s4": "S4 \ube44\uc6a9\uac10\uc18c hex / \ud574\uc18c hidden<br />\uae30\uc0c1\ud56d \uc81c\uac70 \uc0c1\ud55c\uc120",
        "baseline": "\uae30\uc900 hidden \ucde8\uc57d\uc9c0\uc5ed<br />S0-M3 \uae30\uc900",
    },
}

HTML_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIINfQ8oXzUeVFYgK8WkGdQmNNZkC+f8hjs=" crossorigin="" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
  <style>
    /* Leaflet core fallback: keeps tiles/panes positioned even when CDN CSS is blocked. */
    .leaflet-container { overflow:hidden; }
    .leaflet-pane,
    .leaflet-tile,
    .leaflet-marker-icon,
    .leaflet-marker-shadow,
    .leaflet-tile-container,
    .leaflet-pane > svg,
    .leaflet-pane > canvas,
    .leaflet-zoom-box,
    .leaflet-image-layer,
    .leaflet-layer { position:absolute; left:0; top:0; }
    .leaflet-tile,
    .leaflet-marker-icon,
    .leaflet-marker-shadow { -webkit-user-select:none; user-select:none; -webkit-user-drag:none; }
    .leaflet-tile { visibility:hidden; }
    .leaflet-tile-loaded { visibility:inherit; }
    .leaflet-pane { z-index:400; }
    .leaflet-tile-pane { z-index:200; }
    .leaflet-overlay-pane { z-index:400; }
    .leaflet-shadow-pane { z-index:500; }
    .leaflet-marker-pane { z-index:600; }
    .leaflet-tooltip-pane { z-index:650; }
    .leaflet-popup-pane { z-index:700; }
    .leaflet-map-pane canvas { z-index:100; }
    .leaflet-map-pane svg { z-index:200; }
    .leaflet-control { position:relative; z-index:800; pointer-events:auto; }
    .leaflet-top,
    .leaflet-bottom { position:absolute; z-index:1000; pointer-events:none; }
    .leaflet-top { top:0; }
    .leaflet-right { right:0; }
    .leaflet-bottom { bottom:0; }
    .leaflet-left { left:0; }
    .leaflet-control { float:left; clear:both; }
    .leaflet-right .leaflet-control { float:right; }
    .leaflet-top .leaflet-control { margin-top:10px; }
    .leaflet-bottom .leaflet-control { margin-bottom:10px; }
    .leaflet-left .leaflet-control { margin-left:10px; }
    .leaflet-right .leaflet-control { margin-right:10px; }
    .leaflet-control-zoom { border:2px solid rgba(0,0,0,.2); border-radius:4px; overflow:hidden; background:#fff; }
    .leaflet-control-zoom a { display:block; width:26px; height:26px; line-height:26px; text-align:center; text-decoration:none; color:#111827; background:#fff; border-bottom:1px solid #d1d5db; }
    .leaflet-control-attribution { background:rgba(255,255,255,.82); padding:0 5px; font-size:11px; }
    .leaflet-popup { position:absolute; text-align:center; margin-bottom:20px; }
    .leaflet-popup-content-wrapper { padding:1px; text-align:left; border-radius:8px; background:#fff; box-shadow:0 3px 14px rgba(0,0,0,.25); }
    .leaflet-popup-content { margin:12px 14px; line-height:1.4; }
    .leaflet-popup-tip-container { width:40px; height:20px; position:absolute; left:50%; margin-left:-20px; overflow:hidden; pointer-events:none; }
    .leaflet-popup-tip { width:17px; height:17px; padding:1px; margin:-10px auto 0; transform:rotate(45deg); background:#fff; box-shadow:0 3px 14px rgba(0,0,0,.25); }
    .leaflet-interactive { cursor:pointer; }
    .leaflet-grab { cursor:grab; }
    .leaflet-dragging .leaflet-grab { cursor:move; }
    :root { --panel:#fff; --text:#1f2933; --muted:#667085; --line:#d9dee8; --soft:#f5f7fb; --accent:#0f766e; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:"Malgun Gothic","Apple SD Gothic Neo",Arial,sans-serif; color:var(--text); background:#eef2f6; }
    .app { display:grid; grid-template-columns:minmax(0,1fr) 370px; height:100vh; min-height:640px; }
    #map { width:100%; height:100%; }
    .panel { overflow:auto; background:var(--panel); border-left:1px solid var(--line); padding:18px 18px 22px; box-shadow:-8px 0 20px rgba(15,23,42,.08); }
    h1 { margin:0 0 8px; font-size:20px; line-height:1.35; letter-spacing:0; }
    h2 { margin:20px 0 10px; font-size:15px; letter-spacing:0; }
    p { margin:0; color:var(--muted); font-size:13px; line-height:1.55; }
    .notice { margin-top:12px; padding:10px 12px; border:1px solid #cfe2ff; background:#eff6ff; color:#174e82; border-radius:8px; font-size:12px; line-height:1.55; }
    .scenario-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:12px; }
    button { font:inherit; letter-spacing:0; }
    .scenario-btn,.legend-btn { width:100%; border:1px solid var(--line); background:#fff; color:var(--text); border-radius:8px; padding:9px 10px; cursor:pointer; }
    .scenario-btn { text-align:center; font-weight:700; font-size:13px; }
    .scenario-btn.active { border-color:var(--accent); background:#ecfdf5; color:#075e54; }
    .legend-btn { display:grid; grid-template-columns:18px minmax(0,1fr) auto; gap:8px; align-items:center; margin-bottom:7px; font-size:13px; text-align:left; }
    .legend-btn.off { opacity:.45; background:#f8fafc; }
    .swatch { width:15px; height:15px; border:1px solid rgba(17,24,39,.45); border-radius:4px; }
    .swatch.line { height:4px; border:0; border-radius:999px; }
    .count { color:var(--muted); font-size:12px; white-space:nowrap; }
    .reason-grid { display:grid; grid-template-columns:1fr; gap:6px; margin-top:8px; }
    .reason-btn { display:grid; grid-template-columns:18px minmax(0,1fr); gap:8px; align-items:center; border:1px solid var(--line); background:var(--soft); border-radius:8px; padding:7px 9px; cursor:pointer; font-size:12px; text-align:left; }
    .reason-btn.off { opacity:.38; text-decoration:line-through; }
    .summary-card { margin-top:10px; padding:11px 12px; border:1px solid var(--line); border-radius:8px; background:#fbfcff; font-size:12px; line-height:1.65; }
    .metric-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:10px; }
    .metric { border:1px solid var(--line); background:#fff; border-radius:8px; padding:9px; }
    .metric strong { display:block; font-size:16px; line-height:1.2; }
    .metric span { display:block; margin-top:3px; color:var(--muted); font-size:11px; line-height:1.35; }
    .detail { margin-top:12px; padding:12px; border:1px solid #f3d18a; background:#fffbeb; border-radius:8px; min-height:78px; font-size:12px; line-height:1.55; }
    .detail table { width:100%; border-collapse:collapse; margin-top:6px; }
    .detail th,.detail td { border-top:1px solid rgba(120,113,108,.25); padding:4px 0; text-align:left; vertical-align:top; }
    .detail th { width:42%; color:#6b5f50; font-weight:700; }
    .footer { margin-top:16px; padding-top:12px; border-top:1px solid var(--line); color:var(--muted); font-size:11px; line-height:1.5; }
    .leaflet-popup-content { min-width:230px; font-family:"Malgun Gothic","Apple SD Gothic Neo",Arial,sans-serif; font-size:12px; }
    .popup-title { margin-bottom:6px; font-weight:800; }
    .popup-row { display:grid; grid-template-columns:92px 1fr; gap:8px; padding:2px 0; border-top:1px solid #edf0f4; }
    @media (max-width:980px) { .app { grid-template-columns:1fr; grid-template-rows:minmax(420px,62vh) auto; height:auto; } .panel { border-left:0; border-top:1px solid var(--line); } }
  </style>
</head>
<body>
  <div class="app">
    <main id="map"></main>
    <aside class="panel">
      <h1 id="title"></h1>
      <p id="subtitle"></p>
      <div class="notice" id="notice"></div>
      <h2 id="quickViewTitle"></h2>
      <div class="scenario-grid" id="scenarioButtons"></div>
      <h2 id="legendTitle"></h2>
      <div id="legendButtons"></div>
      <h2 id="reasonsTitle"></h2>
      <p id="reasonHelp"></p>
      <div class="reason-grid" id="reasonButtons"></div>
      <h2 id="summaryTitle"></h2>
      <div class="summary-card" id="summaryText"></div>
      <div class="metric-grid" id="metricGrid"></div>
      <h2 id="selectedTitle"></h2>
      <div class="detail" id="detailBox"></div>
      <div class="footer" id="footer"></div>
    </aside>
  </div>
  <script>
    const MAP_DATA = __MAP_DATA__;
    const ui = MAP_DATA.ui;
    const layerMeta = MAP_DATA.layerMeta;
    const presets = MAP_DATA.presets;
    const map = L.map("map", { preferCanvas: true, zoomControl: true });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    let activePreset = "s1";
    let activeLayerKeys = new Set(presets.s1.layers);
    let activeReasons = new Set(Object.keys(MAP_DATA.reasonLabels));
    const leafletLayers = {};
    const fmt = new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 2 });
    const fmt0 = new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 0 });
    const fmt1 = new Intl.NumberFormat("ko-KR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    const fmt6 = new Intl.NumberFormat("ko-KR", { minimumFractionDigits: 6, maximumFractionDigits: 6 });

    function initText() {
      document.title = ui.title;
      document.getElementById("map").setAttribute("aria-label", ui.mapAria);
      document.getElementById("title").textContent = ui.title;
      document.getElementById("subtitle").textContent = ui.subtitle;
      document.getElementById("notice").textContent = ui.notice;
      document.getElementById("quickViewTitle").textContent = ui.quickView;
      document.getElementById("legendTitle").textContent = ui.legend;
      document.getElementById("reasonsTitle").textContent = ui.reasons;
      document.getElementById("reasonHelp").textContent = ui.reasonHelp;
      document.getElementById("summaryTitle").textContent = ui.summary;
      document.getElementById("selectedTitle").textContent = ui.selected;
      document.getElementById("detailBox").textContent = ui.detailPlaceholder;
      document.getElementById("footer").innerHTML = ui.footer;
    }

    function fmtValue(value, suffix = "") {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
      return `${fmt.format(Number(value))}${suffix}`;
    }
    function fmtMeters(value) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
      return `${fmt1.format(Number(value))} m`;
    }
    function fmtMinutes(value) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
      return `${fmt1.format(Number(value))}분`;
    }
    function fmtVulnerability(value) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
      const n = Number(value);
      if (n !== 0 && Math.abs(n) < 0.000001) return n.toExponential(2);
      return fmt6.format(n);
    }
    function fmtPercentValue(value) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
      return `${fmt1.format(Number(value) * 100)}%`;
    }
    function escapeHtml(value) {
      return String(value ?? "-").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
    }
    function row(label, value) {
      return `<div class="popup-row"><strong>${label}</strong><span>${escapeHtml(value)}</span></div>`;
    }
    function adminText(props) {
      return `${props.district_name ?? ""} ${props.admin_name ?? ""}`.trim();
    }
    function popupHtml(layerKey, props) {
      const f = ui.fields;
      const rows = [];
      if (props.mode_ko) rows.push(row(f.transitMode, props.mode_ko));
      if (props.stop_name) rows.push(row(f.stopName, props.stop_name));
      if (props.stop_id) rows.push(row(f.stopId, props.stop_id));
      if (props.passengers_sum !== undefined) rows.push(row(f.passengers, fmt0.format(Number(props.passengers_sum || 0))));
      if (props.hex_id) rows.push(row(f.hexId, props.hex_id));
      if (props.district_name || props.admin_name) rows.push(row(f.admin, adminText(props)));
      if (props.primary_reason_ko) rows.push(row(f.reason, props.primary_reason_ko));
      if (props.baseline_vulnerability !== undefined) rows.push(row(f.baselineVulnerability, fmtVulnerability(props.baseline_vulnerability)));
      if (props.scenario_vulnerability !== undefined) rows.push(row(f.scenarioVulnerability, fmtVulnerability(props.scenario_vulnerability)));
      if (props.delta_vulnerability !== undefined) rows.push(row(f.deltaVulnerability, fmtVulnerability(props.delta_vulnerability)));
      if (props.baseline_cost !== undefined) rows.push(row(f.baselineCost, fmtMeters(props.baseline_cost)));
      if (props.scenario_cost !== undefined) rows.push(row(f.scenarioCost, fmtMeters(props.scenario_cost)));
      if (props.delta_cost !== undefined) rows.push(row(f.deltaCost, fmtMeters(props.delta_cost)));
      if (props.delta_cost_pct !== undefined) rows.push(row(f.deltaCostPct, fmtPercentValue(props.delta_cost_pct)));
      if (props.access_cost_m0 !== undefined) rows.push(row(f.m0Cost, fmtMeters(props.access_cost_m0)));
      if (props.access_cost_m1 !== undefined) rows.push(row(f.m1Cost, fmtMeters(props.access_cost_m1)));
      if (props.access_cost_m2 !== undefined) rows.push(row(f.m2Cost, fmtMeters(props.access_cost_m2)));
      if (props.access_cost_m3 !== undefined) rows.push(row(f.m3Cost, fmtMeters(props.access_cost_m3)));
      if (props.access_time_m3_min !== undefined) rows.push(row(f.m3Minutes, fmtMinutes(props.access_time_m3_min)));
      if (props.slope_increment_m1_m0 !== undefined) rows.push(row(f.slopeIncrement, fmtMeters(props.slope_increment_m1_m0)));
      if (props.weather_additive_increment_m2_m1 !== undefined) rows.push(row(f.weatherIncrement, fmtMeters(props.weather_additive_increment_m2_m1)));
      if (props.interaction_increment_m3_m2 !== undefined) rows.push(row(f.interactionIncrement, fmtMeters(props.interaction_increment_m3_m2)));
      if (props.total_env_increment_m3_m0 !== undefined) rows.push(row(f.totalEnvIncrement, fmtMeters(props.total_env_increment_m3_m0)));
      if (props.nearest_bus_stop_name) rows.push(row(f.nearestBus, `${props.nearest_bus_stop_name} / ${fmtMeters(props.nearest_bus_distance_m)} / ${fmtMinutes(props.nearest_bus_time_min)}`));
      if (props.nearest_subway_stop_name) rows.push(row(f.nearestSubway, `${props.nearest_subway_stop_name} / ${fmtMeters(props.nearest_subway_distance_m)} / ${fmtMinutes(props.nearest_subway_time_min)}`));
      if (props.delta_rank_improvement !== undefined) rows.push(row(f.rankImprovement, fmtValue(props.delta_rank_improvement)));
      if (props.registered_senior_population !== undefined) rows.push(row(f.seniorPopulation, fmtValue(props.registered_senior_population, " 명")));
      if (props.candidate_priority_rank !== undefined) rows.push(row(f.candidateRank, props.candidate_priority_rank));
      if (props.recommended_action) rows.push(row(f.recommendedReview, props.recommended_action));
      if (props.scenario3_rank !== undefined) rows.push(row(f.weatherRank, props.scenario3_rank));
      if (props.recommended_actions) rows.push(row(f.weatherAction, props.recommended_actions));
      if (props.grade_abs_percent !== undefined) rows.push(row(f.grade, fmtValue(props.grade_abs_percent, "%")));
      if (props.delta_edge_cost_m3 !== undefined) rows.push(row(f.edgeCostReduction, fmtValue(props.delta_edge_cost_m3, " m")));
      return `<div class="popup-title">${escapeHtml(layerMeta[layerKey].label)}</div>${rows.join("")}`;
    }
    function showDetail(layerKey, props) {
      const f = ui.fields;
      const tr = (label, value) => `<tr><th>${label}</th><td>${escapeHtml(value)}</td></tr>`;
      const rows = [];
      if (props.mode_ko) rows.push(tr(f.transitMode, props.mode_ko));
      if (props.stop_name) rows.push(tr(f.stopName, props.stop_name));
      if (props.stop_id) rows.push(tr(f.stopId, props.stop_id));
      if (props.passengers_sum !== undefined) rows.push(tr(f.passengers, fmt0.format(Number(props.passengers_sum || 0))));
      if (props.hex_id) rows.push(tr(f.hexId, props.hex_id));
      if (props.district_name || props.admin_name) rows.push(tr(f.location, adminText(props)));
      if (props.primary_reason_ko) rows.push(tr(f.colorMeaning, props.primary_reason_ko));
      if (props.baseline_vulnerability !== undefined) rows.push(tr(f.baselineVulnerability, fmtVulnerability(props.baseline_vulnerability)));
      if (props.scenario_vulnerability !== undefined) rows.push(tr(f.scenarioVulnerability, fmtVulnerability(props.scenario_vulnerability)));
      if (props.delta_vulnerability !== undefined) rows.push(tr(f.deltaVulnerability, fmtVulnerability(props.delta_vulnerability)));
      if (props.baseline_cost !== undefined) rows.push(tr(f.baselineCost, fmtMeters(props.baseline_cost)));
      if (props.scenario_cost !== undefined) rows.push(tr(f.scenarioCost, fmtMeters(props.scenario_cost)));
      if (props.delta_cost !== undefined) rows.push(tr(f.deltaCost, fmtMeters(props.delta_cost)));
      if (props.delta_cost_pct !== undefined) rows.push(tr(f.deltaCostPct, fmtPercentValue(props.delta_cost_pct)));
      if (props.access_cost_m0 !== undefined) rows.push(tr(f.m0Cost, fmtMeters(props.access_cost_m0)));
      if (props.access_cost_m1 !== undefined) rows.push(tr(f.m1Cost, fmtMeters(props.access_cost_m1)));
      if (props.access_cost_m2 !== undefined) rows.push(tr(f.m2Cost, fmtMeters(props.access_cost_m2)));
      if (props.access_cost_m3 !== undefined) rows.push(tr(f.m3Cost, fmtMeters(props.access_cost_m3)));
      if (props.access_time_m3_min !== undefined) rows.push(tr(f.m3Minutes, fmtMinutes(props.access_time_m3_min)));
      if (props.slope_increment_m1_m0 !== undefined) rows.push(tr(f.slopeIncrement, fmtMeters(props.slope_increment_m1_m0)));
      if (props.weather_additive_increment_m2_m1 !== undefined) rows.push(tr(f.weatherIncrement, fmtMeters(props.weather_additive_increment_m2_m1)));
      if (props.interaction_increment_m3_m2 !== undefined) rows.push(tr(f.interactionIncrement, fmtMeters(props.interaction_increment_m3_m2)));
      if (props.total_env_increment_m3_m0 !== undefined) rows.push(tr(f.totalEnvIncrement, fmtMeters(props.total_env_increment_m3_m0)));
      if (props.nearest_bus_stop_name) rows.push(tr(f.nearestBus, `${props.nearest_bus_stop_name} / ${fmtMeters(props.nearest_bus_distance_m)} / ${fmtMinutes(props.nearest_bus_time_min)}`));
      if (props.nearest_subway_stop_name) rows.push(tr(f.nearestSubway, `${props.nearest_subway_stop_name} / ${fmtMeters(props.nearest_subway_distance_m)} / ${fmtMinutes(props.nearest_subway_time_min)}`));
      if (props.delta_rank_improvement !== undefined) rows.push(tr(f.rankImprovement, fmtValue(props.delta_rank_improvement)));
      if (props.registered_senior_population !== undefined) rows.push(tr(f.seniorPopulation, fmtValue(props.registered_senior_population, " 명")));
      if (props.candidate_priority_rank !== undefined) rows.push(tr(f.s1CandidateRank, props.candidate_priority_rank));
      if (props.scenario3_rank !== undefined) rows.push(tr(f.s4CandidateRank, props.scenario3_rank));
      if (props.grade_abs_percent !== undefined) rows.push(tr(f.s3Grade, fmtValue(props.grade_abs_percent, "%")));
      document.getElementById("detailBox").innerHTML = `
        <strong>${escapeHtml(layerMeta[layerKey].label)}</strong>
        <p>${escapeHtml(layerMeta[layerKey].description)}</p>
        <table><tbody>${rows.join("")}</tbody></table>`;
    }
    function hiddenStyle(feature) {
      const reason = feature.properties.primary_reason;
      const color = MAP_DATA.reasonColors[reason] || "#969696";
      return { color, fillColor: color, weight: 1, opacity: .85, fillOpacity: activeReasons.has(reason) ? .22 : 0, interactive: activeReasons.has(reason) };
    }
    function polygonStyle(color, opacity) {
      return { color, fillColor: color, weight: 1.3, opacity: .95, fillOpacity: opacity };
    }
    function resolvedStyle(color) {
      return { color: "#111827", fillColor: color, weight: 2.8, opacity: 1, fillOpacity: .86 };
    }
    function createLayer(layerKey) {
      const meta = layerMeta[layerKey];
      return L.geoJSON(MAP_DATA.layers[layerKey], {
        style: (feature) => {
          if (layerKey === "hidden") return hiddenStyle(feature);
          if (layerKey === "s4Reduced") return polygonStyle(meta.color, .12);
          if (layerKey === "s1Reduced" || layerKey === "s3Reduced") return polygonStyle(meta.color, .24);
          if (layerKey === "s1Resolved" || layerKey === "s3Resolved" || layerKey === "s4Resolved") return resolvedStyle(meta.color);
          if (layerKey === "s3Edges") return { color: meta.color, weight: 4.2, opacity: .95, dashArray: "7 3" };
          return polygonStyle(meta.color, .45);
        },
        pointToLayer: (feature, latlng) => {
          const radius = layerKey === "busStops" ? 2.4 : layerKey === "subwayStops" ? 5.2 : layerKey === "s1Candidates" ? 6 : 7;
          const fillOpacity = layerKey === "busStops" ? .55 : .9;
          return L.circleMarker(latlng, { radius, color: "#1f2937", weight: 1.3, fillColor: meta.color, fillOpacity });
        },
        filter: (feature) => layerKey !== "hidden" || activeReasons.has(feature.properties.primary_reason),
        onEachFeature: (feature, layer) => {
          layer.bindPopup(popupHtml(layerKey, feature.properties));
          layer.on("click", () => showDetail(layerKey, feature.properties));
        }
      });
    }
    function redrawLayers() {
      Object.values(leafletLayers).forEach((layer) => map.removeLayer(layer));
      Object.keys(leafletLayers).forEach((key) => delete leafletLayers[key]);
      for (const key of activeLayerKeys) leafletLayers[key] = createLayer(key).addTo(map);
      updatePanelState();
    }
    function setPreset(key) {
      activePreset = key;
      activeLayerKeys = new Set(presets[key].layers);
      redrawLayers();
    }
    function toggleLayer(key) {
      if (activeLayerKeys.has(key)) activeLayerKeys.delete(key);
      else activeLayerKeys.add(key);
      activePreset = "custom";
      redrawLayers();
    }
    function toggleReason(reason) {
      if (activeReasons.has(reason)) activeReasons.delete(reason);
      else activeReasons.add(reason);
      if (activeLayerKeys.has("hidden")) redrawLayers();
      else updatePanelState();
    }
    function updatePanelState() {
      document.querySelectorAll(".scenario-btn").forEach((btn) => btn.classList.toggle("active", btn.dataset.preset === activePreset));
      document.querySelectorAll(".legend-btn").forEach((btn) => btn.classList.toggle("off", !activeLayerKeys.has(btn.dataset.layer)));
      document.querySelectorAll(".reason-btn").forEach((btn) => btn.classList.toggle("off", !activeReasons.has(btn.dataset.reason)));
      updateSummary();
    }
    function updateSummary() {
      const summary = activePreset === "custom" ? ui.customSummary : presets[activePreset].summary;
      const title = activePreset === "custom" ? ui.custom : presets[activePreset].label;
      document.getElementById("summaryText").innerHTML = `<strong>${escapeHtml(title)}</strong><br />${escapeHtml(summary)}`;
      const s = MAP_DATA.scenarioSummary;
      const c = MAP_DATA.layerCounts;
      document.getElementById("metricGrid").innerHTML = `
        <div class="metric"><strong>${fmt.format(c.s1Reduced)} / ${fmt.format(s.S1.resolved_hidden_count)}</strong><span>${ui.metrics.s1}</span></div>
        <div class="metric"><strong>${fmt.format(c.s3Reduced)} / ${fmt.format(s.S3.resolved_hidden_count)}</strong><span>${ui.metrics.s3}</span></div>
        <div class="metric"><strong>${fmt.format(c.s4Reduced)} / ${fmt.format(s.S4.resolved_hidden_count)}</strong><span>${ui.metrics.s4}</span></div>
        <div class="metric"><strong>${fmt.format(s.baseline_hidden_count)}</strong><span>${ui.metrics.baseline}</span></div>`;
    }
    function buildControls() {
      document.getElementById("scenarioButtons").innerHTML = Object.entries(presets).map(([key, preset]) => `<button class="scenario-btn" data-preset="${key}" type="button">${preset.label}</button>`).join("");
      document.querySelectorAll(".scenario-btn").forEach((btn) => btn.addEventListener("click", () => setPreset(btn.dataset.preset)));
      document.getElementById("legendButtons").innerHTML = Object.entries(layerMeta).map(([key, meta]) => {
        const swatchClass = meta.type === "line" ? "swatch line" : "swatch";
        return `<button class="legend-btn" data-layer="${key}" type="button" title="${escapeHtml(meta.description)}"><span class="${swatchClass}" style="background:${meta.color}"></span><span>${escapeHtml(meta.label)}</span><span class="count">${fmt.format(MAP_DATA.layerCounts[key] || 0)}</span></button>`;
      }).join("");
      document.querySelectorAll(".legend-btn").forEach((btn) => btn.addEventListener("click", () => toggleLayer(btn.dataset.layer)));
      document.getElementById("reasonButtons").innerHTML = Object.entries(MAP_DATA.reasonLabels).map(([reason, label]) => `<button class="reason-btn" data-reason="${reason}" type="button"><span class="swatch" style="background:${MAP_DATA.reasonColors[reason] || "#969696"}"></span><span>${escapeHtml(label)}</span></button>`).join("");
      document.querySelectorAll(".reason-btn").forEach((btn) => btn.addEventListener("click", () => toggleReason(btn.dataset.reason)));
    }
    initText();
    buildControls();
    redrawLayers();
    function fitMapToData() {
      map.invalidateSize(true);
      if (MAP_DATA.bounds) map.fitBounds([[MAP_DATA.bounds[1], MAP_DATA.bounds[0]], [MAP_DATA.bounds[3], MAP_DATA.bounds[2]]], { padding: [18, 18] });
      else map.setView([37.5665, 126.9780], 11);
    }
    fitMapToData();
    setTimeout(fitMapToData, 150);
  </script>
</body>
</html>
"""


def read_summary() -> dict[str, Any]:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def scenario_by_id(summary: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    for scenario in summary["scenarios"]:
        if scenario["scenario_id"] == scenario_id:
            return scenario
    raise KeyError(f"Missing scenario summary: {scenario_id}")


def read_gpkg(name: str) -> gpd.GeoDataFrame:
    return gpd.read_file(QGIS_DIR / name)


def read_transit_candidates() -> gpd.GeoDataFrame:
    transit = gpd.read_file(QGIS_DIR / "out_transit_d_candidates.gpkg", layer="out_transit_d_candidates")
    transit = transit.loc[transit.geometry.notna()].copy()
    transit["mode_ko"] = transit["mode"].map({"bus": "\ubc84\uc2a4", "subway": "\uc9c0\ud558\ucca0"}).fillna(transit["mode"])
    return transit


def select_existing(gdf: gpd.GeoDataFrame, columns: list[str]) -> gpd.GeoDataFrame:
    selected = [column for column in columns if column in gdf.columns]
    return gdf[selected + ["geometry"]].copy()


def add_time_fields(gdf: gpd.GeoDataFrame | pd.DataFrame) -> gpd.GeoDataFrame | pd.DataFrame:
    result = gdf.copy()
    cost_to_time = {
        "access_cost_m0": "access_time_m0_min",
        "access_cost_m1": "access_time_m1_min",
        "access_cost_m2": "access_time_m2_min",
        "access_cost_m3": "access_time_m3_min",
        "baseline_cost": "baseline_time_min",
        "scenario_cost": "scenario_time_min",
        "delta_cost": "delta_time_min",
    }
    for cost_col, time_col in cost_to_time.items():
        if cost_col in result.columns:
            result[time_col] = pd.to_numeric(result[cost_col], errors="coerce") / WALKING_SPEED_M_PER_MIN
    return result


def nearest_transit_table(hexes: gpd.GeoDataFrame, transit: gpd.GeoDataFrame, mode: str, prefix: str) -> pd.DataFrame:
    # QGIS popup support: nearest existing stop is a centroid-to-stop reference, not the network path itself.
    base = hexes[["hex_id", "geometry"]].dropna(subset=["geometry"]).drop_duplicates("hex_id").copy()
    result = pd.DataFrame({"hex_id": base["hex_id"]})
    for suffix in ["stop_id", "stop_name", "passengers_sum", "distance_m", "time_min"]:
        result[f"{prefix}_{suffix}"] = pd.NA
    stops = transit.loc[
        transit["mode"].eq(mode),
        ["stop_id", "stop_name", "passengers_sum", "geometry"],
    ].copy()
    if base.empty or stops.empty:
        return result

    centroids = base.copy()
    centroids["geometry"] = centroids.geometry.centroid
    distance_col = f"{prefix}_distance_m"
    joined = gpd.sjoin_nearest(centroids, stops, how="left", distance_col=distance_col)
    joined = joined.sort_values(["hex_id", distance_col]).drop_duplicates("hex_id")
    joined = joined[
        ["hex_id", "stop_id", "stop_name", "passengers_sum", distance_col]
    ].rename(
        columns={
            "stop_id": f"{prefix}_stop_id",
            "stop_name": f"{prefix}_stop_name",
            "passengers_sum": f"{prefix}_passengers_sum",
        }
    )
    result = base[["hex_id"]].merge(joined, on="hex_id", how="left")
    result[f"{prefix}_time_min"] = pd.to_numeric(result[distance_col], errors="coerce") / WALKING_SPEED_M_PER_MIN
    return result


def build_nearest_transit_table(hexes: gpd.GeoDataFrame, transit: gpd.GeoDataFrame) -> pd.DataFrame:
    bus = nearest_transit_table(hexes, transit, "bus", "nearest_bus")
    subway = nearest_transit_table(hexes, transit, "subway", "nearest_subway")
    return bus.merge(subway, on="hex_id", how="outer")


def merge_hex_fields(gdf: gpd.GeoDataFrame, fields: pd.DataFrame) -> gpd.GeoDataFrame:
    if gdf.empty or "hex_id" not in gdf.columns or fields.empty:
        return gdf
    return gdf.merge(fields, on="hex_id", how="left")


def clean_for_geojson(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    result = gdf.copy()
    for column in result.columns:
        if column != "geometry" and pd.api.types.is_float_dtype(result[column]):
            result[column] = result[column].round(6)
    return result


def as_geojson(gdf: gpd.GeoDataFrame, *, simplify_m: float = 0.0) -> dict[str, Any]:
    work = gdf.copy()
    if simplify_m > 0:
        work["geometry"] = work.geometry.simplify(simplify_m, preserve_topology=True)
    work = clean_for_geojson(work.to_crs(CRS_WEB))
    return json.loads(work.to_json(drop_id=True))


def build_payload() -> tuple[dict[str, Any], dict[str, Any]]:
    summary = read_summary()
    common_columns = [
        "hex_id",
        "district_name",
        "admin_name",
        "primary_reason",
        "primary_reason_ko",
        "baseline_cost",
        "scenario_cost",
        "delta_cost",
        "delta_cost_pct",
        "baseline_vulnerability",
        "scenario_vulnerability",
        "delta_vulnerability",
        "delta_rank_improvement",
        "registered_population",
        "registered_senior_population",
    ]

    hidden = read_gpkg("out_hidden_vulnerability_reason_diagnostics.gpkg")
    hidden["primary_reason_ko"] = hidden["primary_reason"].map(REASON_LABELS).fillna("\uae30\ud0c0")
    hidden_layer = select_existing(
        hidden,
        [
            "hex_id",
            "district_name",
            "admin_name",
            "primary_reason",
            "primary_reason_ko",
            "vulnerability_m3_final",
            "access_cost_m0",
            "access_cost_m1",
            "access_cost_m2",
            "access_cost_m3",
            "slope_increment_m1_m0",
            "weather_additive_increment_m2_m1",
            "interaction_increment_m3_m2",
            "total_env_increment_m3_m0",
            "cost_gap_m3_minus_m0",
            "cost_gap_ratio_m3_over_m0",
            "demand_index_final",
            "demand_percentile_final",
            "cost_m3_percentile_final",
            "env_penalty_percentile_final",
            "high_demand_pressure",
            "high_m3_cost_pressure",
            "high_env_penalty",
            "near_400m_distance_pressure",
            "registered_population",
            "registered_senior_population",
        ],
    )
    hidden_layer["baseline_vulnerability"] = hidden_layer["vulnerability_m3_final"]
    hidden_layer["baseline_cost"] = hidden_layer["access_cost_m3"]
    hidden_layer = add_time_fields(hidden_layer)
    diagnostic_columns = [
        "hex_id",
        "access_cost_m0",
        "access_cost_m1",
        "access_cost_m2",
        "access_cost_m3",
        "slope_increment_m1_m0",
        "weather_additive_increment_m2_m1",
        "interaction_increment_m3_m2",
        "total_env_increment_m3_m0",
        "cost_gap_m3_minus_m0",
        "cost_gap_ratio_m3_over_m0",
        "demand_percentile_final",
        "cost_m3_percentile_final",
        "env_penalty_percentile_final",
        "high_demand_pressure",
        "high_m3_cost_pressure",
        "high_env_penalty",
        "near_400m_distance_pressure",
    ]
    hidden_diagnostics = hidden[
        [column for column in diagnostic_columns if column in hidden.columns]
    ].drop_duplicates("hex_id")
    hidden_diagnostics = add_time_fields(hidden_diagnostics)

    s1 = read_gpkg("S1_delta_vulnerability_runner.gpkg")
    s1["primary_reason_ko"] = s1["primary_reason"].map(REASON_LABELS).fillna("\uae30\ud0c0")
    s1_reduced = s1.loc[pd.to_numeric(s1["delta_vulnerability"], errors="coerce") > 0]
    s1_resolved = s1.loc[s1["resolved_hidden"].fillna(False).astype(bool)]
    transit = read_transit_candidates()
    nearest_transit = build_nearest_transit_table(s1[["hex_id", "geometry"]], transit)

    s1_candidates = read_gpkg("S1_candidates.gpkg")
    s1_candidate_layer = select_existing(
        s1_candidates,
        [
            "candidate_priority_rank",
            "district_name",
            "admin_name",
            "hex_id",
            "primary_reason",
            "vulnerability_m3_final",
            "demand_index_final",
            "access_cost_m3",
            "registered_senior_population",
            "recommended_action",
            "site_feasibility",
            "manual_check_required",
        ],
    )
    s1_candidate_layer = merge_hex_fields(add_time_fields(s1_candidate_layer), nearest_transit)

    s3 = read_gpkg("S3_delta_vulnerability_runner.gpkg")
    s3["primary_reason_ko"] = s3["primary_reason"].map(REASON_LABELS).fillna("\uae30\ud0c0")
    s3_reduced = s3.loc[pd.to_numeric(s3["delta_vulnerability"], errors="coerce") > 0]
    s3_resolved = s3.loc[s3["resolved_hidden"].fillna(False).astype(bool)]
    s3_edges = read_gpkg("S3_improved_edges_cap15.gpkg")
    s3_edge_layer = select_existing(
        s3_edges,
        [
            "u",
            "v",
            "name",
            "highway",
            "length_m",
            "grade_abs_percent",
            "baseline_cost_m3",
            "scenario_cost_m3",
            "delta_edge_cost_m3",
        ],
    )

    s4 = read_gpkg("S4_weather_off_delta_vulnerability_runner.gpkg")
    s4["primary_reason_ko"] = s4["primary_reason"].map(REASON_LABELS).fillna("\uae30\ud0c0")
    s4_reduced = s4.loc[pd.to_numeric(s4["delta_vulnerability"], errors="coerce") > 0]
    s4_resolved = s4.loc[s4["resolved_hidden"].fillna(False).astype(bool)]
    s4_priority = read_gpkg("scenario3_weather_response_top20_admin_fixed.gpkg")
    s4_priority_layer = select_existing(
        s4_priority,
        [
            "scenario3_rank",
            "district_name",
            "admin_name",
            "hex_id",
            "scenario3_score",
            "primary_low_cost_type",
            "recommended_actions",
            "weather_effect",
            "weather_additive_increment_m2_m1",
            "interaction_increment_m3_m2",
            "registered_senior_population",
            "primary_reason",
        ],
    )
    s4_priority_layer = merge_hex_fields(add_time_fields(s4_priority_layer), nearest_transit)

    hidden_layer = merge_hex_fields(hidden_layer, nearest_transit)

    def scenario_layer(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        layer = add_time_fields(select_existing(gdf, common_columns))
        layer = merge_hex_fields(layer, hidden_diagnostics)
        return merge_hex_fields(layer, nearest_transit)

    layer_gdfs = {
        "hidden": hidden_layer,
        "busStops": select_existing(
            transit.loc[transit["mode"].eq("bus")],
            ["mode", "mode_ko", "stop_id", "stop_name", "passengers_sum", "source_rows"],
        ),
        "subwayStops": select_existing(
            transit.loc[transit["mode"].eq("subway")],
            ["mode", "mode_ko", "stop_id", "stop_name", "passengers_sum", "source_rows"],
        ),
        "s1Reduced": scenario_layer(s1_reduced),
        "s1Resolved": scenario_layer(s1_resolved),
        "s1Candidates": s1_candidate_layer,
        "s3Reduced": scenario_layer(s3_reduced),
        "s3Resolved": scenario_layer(s3_resolved),
        "s3Edges": s3_edge_layer,
        "s4Reduced": scenario_layer(s4_reduced),
        "s4Resolved": scenario_layer(s4_resolved),
        "s4Priority": s4_priority_layer,
    }

    s1_summary = scenario_by_id(summary, "S1")
    s3_summary = scenario_by_id(summary, "S3")
    s4_summary = scenario_by_id(summary, "S4")
    assert len(layer_gdfs["s1Resolved"]) == s1_summary["resolved_hidden_count"]
    assert len(layer_gdfs["s3Reduced"]) == s3_summary["nonzero_delta_vulnerability_count"]
    assert len(layer_gdfs["s3Resolved"]) == s3_summary["resolved_hidden_count"]
    assert len(layer_gdfs["s4Resolved"]) == s4_summary["resolved_hidden_count"]

    bounds_df = pd.concat(
        [
            layer_gdfs["hidden"].to_crs(CRS_WEB).bounds,
            layer_gdfs["s1Candidates"].to_crs(CRS_WEB).bounds,
            layer_gdfs["s4Priority"].to_crs(CRS_WEB).bounds,
        ],
        ignore_index=True,
    )
    bounds = [
        float(bounds_df["minx"].min()),
        float(bounds_df["miny"].min()),
        float(bounds_df["maxx"].max()),
        float(bounds_df["maxy"].max()),
    ]

    layers = {
        "hidden": as_geojson(layer_gdfs["hidden"], simplify_m=2.0),
        "busStops": as_geojson(layer_gdfs["busStops"]),
        "subwayStops": as_geojson(layer_gdfs["subwayStops"]),
        "s1Reduced": as_geojson(layer_gdfs["s1Reduced"], simplify_m=2.0),
        "s1Resolved": as_geojson(layer_gdfs["s1Resolved"], simplify_m=2.0),
        "s1Candidates": as_geojson(layer_gdfs["s1Candidates"]),
        "s3Reduced": as_geojson(layer_gdfs["s3Reduced"], simplify_m=2.0),
        "s3Resolved": as_geojson(layer_gdfs["s3Resolved"], simplify_m=2.0),
        "s3Edges": as_geojson(layer_gdfs["s3Edges"], simplify_m=1.0),
        "s4Reduced": as_geojson(layer_gdfs["s4Reduced"], simplify_m=2.0),
        "s4Resolved": as_geojson(layer_gdfs["s4Resolved"], simplify_m=2.0),
        "s4Priority": as_geojson(layer_gdfs["s4Priority"]),
    }

    payload = {
        "ui": UI_TEXT,
        "layerMeta": LAYER_META,
        "presets": PRESETS,
        "bounds": bounds,
        "reasonLabels": REASON_LABELS,
        "reasonColors": REASON_COLORS,
        "layerCounts": {key: int(len(gdf)) for key, gdf in layer_gdfs.items()},
        "scenarioSummary": {
            "baseline_hidden_count": int(s1_summary["baseline_hidden_count"]),
            "S1": {"resolved_hidden_count": int(s1_summary["resolved_hidden_count"])},
            "S3": {"resolved_hidden_count": int(s3_summary["resolved_hidden_count"])},
            "S4": {"resolved_hidden_count": int(s4_summary["resolved_hidden_count"])},
        },
        "layers": layers,
    }

    manifest = {
        "html": str(OUT_HTML.relative_to(ROOT)),
        "source_summary": str(SUMMARY_PATH.relative_to(ROOT)),
        "layer_counts": payload["layerCounts"],
        "scenario_summary": payload["scenarioSummary"],
        "claim_scope": "Interactive inspection map for accessibility burden counterfactuals; not a ridership demand forecast.",
    }
    return payload, manifest


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload, manifest = build_payload()
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    html = HTML_TEMPLATE.replace("__TITLE__", UI_TEXT["title"]).replace("__MAP_DATA__", data_json)
    OUT_HTML.write_text(html, encoding="utf-8")
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
