# A. 데이터 정의·진단 수치 검증 보고서 (팀원A · scientist)

**대상**: `.omx/plans/demand-scenario-redesign-2026-05-23.md` §1, §3, §4
**모드**: read-only. 본문 인용 file:line·수치·공식을 데이터/코드로 교차검증.

---

## V1. demand_index_final 산식 정합성 — **[PASS]**
- 확인 사실: `hex_features.py:308-317`의 실제 산식 = `(registered_population_norm + registered_senior_population_norm + living_population_norm + poi_total_norm) / 4.0`. 4개 norm 컬럼이 사전에 `_minmax()`(line 37-44)로 정규화. NaN은 `fillna(0)`. 본문 §5의 "Min-Max 0-1 정규화" 진술과 일치.
- 누락: 코드의 `_minmax`는 현재 dataset의 min/max를 그대로 쓰는 **in-sample fit**. §12 수락기준 "S0-M3 고정 min/max"는 별도 `FrozenBaseline` 구현 필요. §3에는 직접 영향 없음.
- 판정: PASS.

## V2. configs/data_sources.yaml 라인 매핑 — **[MINOR]**
- 확인 사실: L30 `local_resident_250m`(생활인구), L35 `registered_population`(등록·고령 동시), L47 `commercial_poi`, L53 `medical_poi`, L59 `senior_welfare_poi`. 5개 라인 모두 본문 의도와 일치.
- 누락: L35가 등록인구+고령인구 두 변수를 한 파일로 담는데 §3 표현이 "5개 라인 = 6개 변수"임을 명시 안 함.
- 권고: §3에 "L35는 등록인구·고령인구 두 컬럼을 공유한다" 한 줄 추가.
- 판정: MINOR.

## V3. §3 진단 수치 재현 — **[PASS]**
| 항목 | 본문 | 실측 | Δ |
|---|---:|---:|---:|
| H3 hex 수 | 4,551 | 4,551 | 0 |
| 평균 | 0.213233 | 0.213233 | 0 |
| std | 0.075278 | 0.075278 | 0 |
| Q1/Q2/Q3/max | 0.161314/0.215678/0.262949/0.527859 | 동일 | 0 |
| 상업/의료/노인복지/전체 POI | 500,744 / 21,174 / 443 / 522,361 | 동일 | 0 |

- 원본 csv 교차확인: commercial 534,978행 / medical 22,239행 / senior_welfare 482행. hex 집계값과의 차이는 서울 경계 외 또는 좌표 무효 제외(spatial join 손실: −34,234 / −1,065 / −39).
- 권고: §3에 "원본 csv → hex 집계 손실 N건" 부록 한 줄.
- 판정: PASS. 모든 수치 완전 일치.

## V4. 평균 기여 비중·Spearman 상관 — **[PASS]**
- 산출 방식: `share_i = norm_i / Σnorm_j (per hex)` 행별 정규화 후 평균.

| 구성요소 | 본문 share | 실측 | Δ |
|---|---:|---:|---:|
| senior_norm | 0.3635 | 0.3635 | 0 |
| registered_norm | 0.3224 | 0.3224 | 0 |
| living_norm | 0.2175 | 0.2175 | 0 |
| poi_norm | 0.0966 | 0.0966 | 0 |

- Spearman: registered 0.7812 / senior 0.7478 / living 0.6545 / poi 0.4250 — 본문 4행과 소수점 4자리까지 일치.
- 판정: PASS.

## V5. §4 4분위 표 — **[PASS 수치, MINOR universe 표기 누락]**
- §4 4분위 표는 **4,551 전체 universe**에서 pd.qcut(q=4) 산출 확인. hex 수(1,138/1,138/1,137/1,138), hidden 수(9/97/201/325 → 합 632), 평균 M3 접근비용, 고령등록인구 합 모두 셀 단위 일치.
- 누락: §3 끝부분 "S0-M3 universe=4,383"과 §4 universe=4,551이 서로 다른데도 §4가 명시 안 함.
- 권고: §4 표 캡션에 "universe=4,551 마스크 통과 전체 hex" 명시.
- 판정: 수치 PASS, 표기 MINOR.

## V6. §4 엄격 후보(demand Q4 + cost Q4 = 185 hex) — **[MAJOR universe 모순]**
- 6가지 정의를 시도한 결과, 본문 수치(185 / hidden 156 / vuln 185 / 등록 535,696 / 고령등록 112,385)와 **유일하게 일치하는 것은 4,383 valid-only universe에서 demand_q·cost_q를 둘 다 pd.qcut(q=4)로 재계산** 후 교집합.
- 4,551 전체에서 같은 정의 적용 시: **190 hex / hidden 160 / 등록 550,257 / 고령등록 115,039** — 본문과 5 hex 차이.
- **즉 §4 안에서 4분위 표(4,551)와 엄격 후보(4,383)가 서로 다른 universe를 사용**. 본문은 이 전환을 어디에서도 명시하지 않음.
- 권고: §4 엄격 후보 표 위에 "universe=4,383 valid-only (access_cost_m3가 NaN인 168 hex 제외)" 명시. §11.5 universe 감사표 작성 시 이 모순을 첫 항목으로 둘 것.
- 판정: MAJOR — §4 핵심 주장의 재현성에 직접 영향. §12 "고정 min/max threshold universe 기록" 항목과 연동.

## V7. §1 결론 요약의 핵심 주장 부합 — **[PASS]**
- (1) "POI 95% 이상이 상업 POI": 500,744/522,361 = **95.86%** → 사실.
- (2) "노인복지 POI 443건": hex 집계 sum = 443 (raw 482 → 39건 경계외/좌표무효 제외). 일치.
- (3) "버스/지하철은 이미 접근성 목적지 D":
  - `configs/data_sources.yaml:11, 18`에 `bus_ridership`/`subway_ridership` 정의
  - `cli.py:270-300`의 `build_transit_d_candidates`가 두 파일을 D 후보 GPKG로 변환
  - `cli.py:514`의 `poi_sources` dict는 `commercial/medical/senior_welfare` 3개 키만. bus/subway는 demand_index_final 입력에 들어가지 않고 D 목적지로만 사용. 본문 주장 사실 부합.
- 판정: PASS.

---

## 요약

| 판정 | 건수 | 항목 |
|---|---:|---|
| PASS | 5 | V1, V3, V4, V5(수치), V7 |
| MINOR | 2 | V2, V5(universe 표기) |
| MAJOR | 1 | **V6 (universe 모순)** |

**가장 결정적 발견 (MAJOR)**: §4 4분위 표(4,551 전체)와 엄격 후보(4,383 valid-only)가 서로 다른 universe를 사용하는데 본문이 명시하지 않음. 4,551에서 같은 정의 적용 시 185 → 190 hex로 5 hex 차이가 발생하며, hidden/등록인구/고령등록 모두 다른 값. §11.5 universe 감사표 작성 전에 본문 §4에 universe 전환을 명시해야 한다.