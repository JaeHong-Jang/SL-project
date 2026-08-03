"""취약 hex를 원인별 4유형으로 분류한다.

연구계획 §5 기여 3 표에 정의된 유형과 대응 정책 시나리오:

  supply_shortage   — M0 거리가 높아 공급 부족
                      → S1 정류장 위치할당: 정류장 자체가 멀어 접근비용이 높은 hex 대상
  slope_vulnerable  — 경사 비용 비율이 지배적
                      → S3 경사 취약 링크 비용 감소: 경사로가 구조적 장벽인 hex 대상
  weather_amplified — 경사×기상 상호작용 비용 비율이 높음
                      → S4 기상 대응 링크 개선: 비·눈 시 급증하는 보행 비용 개선 대상
  high_demand       — 수요 집중형 (나머지, 위 세 유형에 해당하지 않는 취약 hex)
                      → 서비스 수준 개선 방안 추가 논의 필요

임계값 주의:
  slope_share_threshold, interaction_share_threshold, distance_quantile 모두
  초기 탐색값(initial exploratory values)이며 보정된 확정값이 아니다.
  실제 분석 전 데이터 분포를 확인하고 연구팀과 합의한 뒤 조정해야 한다.
"""

from __future__ import annotations

import pandas as pd


def classify_vulnerability_typology(
    features: pd.DataFrame,
    *,
    suffix: str = "final",
    distance_quantile: float = 0.75,
    slope_share_threshold: float = 0.40,
    interaction_share_threshold: float = 0.25,
    type_column: str = "vulnerability_type",
) -> pd.DataFrame:
    """취약 hex를 4유형(공급부족/경사/기상/고수요)으로 분류한다.

    분류 우선순위 (나중이 먼저 덮어씀):
      1. high_demand (기본값)
      2. supply_shortage: access_cost_m0 >= 취약 hex 내 distance_quantile 분위수
      3. weather_amplified: interaction_share >= interaction_share_threshold
      4. slope_vulnerable: slope_share >= slope_share_threshold (최우선)

    Parameters
    ----------
    features:
        hex별 피처 DataFrame. ``vulnerable_m3_{suffix}`` 및
        ``access_cost_m0~m3`` 컬럼이 필요하다.
    suffix:
        취약도 컬럼 suffix (기본 ``"final"``).
    distance_quantile:
        공급부족 판단에 사용하는 취약 hex 내 M0 거리 분위수.
    slope_share_threshold:
        slope_share 가 이 이상이면 ``slope_vulnerable``.
    interaction_share_threshold:
        interaction_share 가 이 이상이면 ``weather_amplified``.
    type_column:
        결과 유형 컬럼명.

    Returns
    -------
    pd.DataFrame
        입력 복사본에 ``type_column`` 컬럼이 추가된 DataFrame.
        비취약 hex는 ``None``, 임시 ``_`` 접두사 컬럼은 포함하지 않는다.
    """
    vulnerable_col = f"vulnerable_m3_{suffix}"
    required_costs = ["access_cost_m0", "access_cost_m1", "access_cost_m2", "access_cost_m3"]

    if vulnerable_col not in features.columns:
        raise KeyError(f"취약도 컬럼이 없습니다: {vulnerable_col!r}")
    missing_costs = [col for col in required_costs if col not in features.columns]
    if missing_costs:
        raise KeyError(f"접근비용 컬럼이 없습니다: {missing_costs}")

    output = features.copy()
    output[type_column] = None

    vulnerable_mask = output[vulnerable_col].fillna(False).astype(bool)
    if not vulnerable_mask.any():
        return output

    # --- 증분 계산 (취약 hex 전체에 대해 계산) ---
    # M0→M1 증분: 경사 비용만의 기여 (기상 효과 없는 상태에서 경사 추가)
    # M2→M3 증분: 경사×기상 상호작용 비용 (additive 기상은 M1→M2이므로 제외)
    # M3-M0 전체: 보행환경 전체 패널티 (slope + weather_additive + interaction 합산, 분모로 사용)
    output["_slope_increment"] = output["access_cost_m1"] - output["access_cost_m0"]
    output["_interaction_increment"] = output["access_cost_m3"] - output["access_cost_m2"]
    output["_total_env_increment"] = output["access_cost_m3"] - output["access_cost_m0"]

    # M3==M0인 링크(평지, 무기상)는 환경 패널티가 없어 share를 계산할 수 없으므로 0으로 처리
    denom = output["_total_env_increment"].where(output["_total_env_increment"] != 0)
    output["_slope_share"] = (output["_slope_increment"] / denom).fillna(0)
    output["_interaction_share"] = (output["_interaction_increment"] / denom).fillna(0)

    # 분위수는 취약 hex 기준으로만 계산
    vuln_rows = output.loc[vulnerable_mask]
    distance_threshold = float(vuln_rows["access_cost_m0"].quantile(distance_quantile))

    # 분류는 덮어씌우기(overwrite) 패턴: 우선순위가 높은 유형이 마지막에 실행되어
    # 이전 유형을 덮어씀. slope_vulnerable이 최우선인 이유는 경사가 서울 구릉지에서
    # 접근성 불이익의 가장 지속적이고 구조적인 원인이기 때문이다.

    # 1. 기본값: high_demand (공급·경사·기상 중 어느 원인도 지배적이지 않은 수요 집중 취약 hex)
    output.loc[vulnerable_mask, type_column] = "high_demand"

    # 2. supply_shortage: 취약 hex 내부에서 상위 distance_quantile에 해당하는 hex
    # 정류장 자체가 멀어 취약 (공급 부족 → S1 정류장 위치할당 시나리오 대상)
    supply_mask = vulnerable_mask & (output["access_cost_m0"] >= distance_threshold)
    output.loc[supply_mask, type_column] = "supply_shortage"

    # 3. weather_amplified (supply_shortage보다 우선): interaction_share가 높은 hex
    # 비/눈 올 때 경사로에서 비용이 급증 (→ S4 기상 대응 보행환경 개선 시나리오 대상)
    weather_mask = vulnerable_mask & (output["_interaction_share"] >= interaction_share_threshold)
    output.loc[weather_mask, type_column] = "weather_amplified"

    # 4. slope_vulnerable (최우선): slope_share가 가장 높은 hex, 경사 자체가 주요 비용 원인
    # supply_shortage, weather_amplified보다 우선 — 경사 장벽은 정책 개입 없이는 구조적으로 지속됨
    # (→ S3 경사 취약 링크 비용 감소 시나리오 대상)
    slope_mask = vulnerable_mask & (output["_slope_share"] >= slope_share_threshold)
    output.loc[slope_mask, type_column] = "slope_vulnerable"

    # 임시 컬럼 제거
    output = output.drop(
        columns=["_slope_increment", "_interaction_increment", "_total_env_increment", "_slope_share", "_interaction_share"]
    )
    return output


def vulnerability_type_summary(
    features: pd.DataFrame,
    *,
    suffix: str = "final",
    type_column: str = "vulnerability_type",
    population_col: str = "registered_population",
    senior_col: str = "registered_senior_population",
) -> pd.DataFrame:
    """취약 유형별 집계 요약 DataFrame을 반환한다.

    Parameters
    ----------
    features:
        ``classify_vulnerability_typology`` 결과 DataFrame.
    suffix:
        취약도 컬럼 suffix (기본 ``"final"``).
    type_column:
        유형 컬럼명.
    population_col:
        인구 합산 컬럼명. 없으면 0으로 채운다.
    senior_col:
        노인 인구 합산 컬럼명. 없으면 0으로 채운다.

    Returns
    -------
    pd.DataFrame
        컬럼: vulnerability_type, hex_count, population_sum,
        senior_population_sum, population_share.
        index는 reset됨. 비취약(type_column==None) 행은 제외.
    """
    typed = features[features[type_column].notna()].copy()

    has_population = population_col in features.columns
    has_senior = senior_col in features.columns

    if not has_population:
        typed["_population"] = 0
    else:
        typed["_population"] = typed[population_col].fillna(0)

    if not has_senior:
        typed["_senior"] = 0
    else:
        typed["_senior"] = typed[senior_col].fillna(0)

    # type_column이 None인 행(비취약 hex)은 이미 위에서 필터링됨
    agg = (
        typed.groupby(type_column, sort=True)
        .agg(
            hex_count=(type_column, "count"),
            population_sum=("_population", "sum"),
            senior_population_sum=("_senior", "sum"),
        )
        .reset_index()
    )
    agg.columns = ["vulnerability_type", "hex_count", "population_sum", "senior_population_sum"]

    total_pop = float(agg["population_sum"].sum())
    agg["population_share"] = agg["population_sum"] / total_pop if total_pop > 0 else 0.0

    return agg
