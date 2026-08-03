# M4-senior 고령자 보행 임피던스 방법 설계

작성일: 2026-05-31
대상: `.omx/plans/demand-scenario-redesign-v2_2-2026-05-31.md`

## 한 줄 결론

고령자 접근성은 `M0 거리`나 `M3 연령공통 경사·기상 비용`만으로는 부족하다. 별도 `M4-senior`를 만들고, 속도·경사·기상·계단을 **각각 분리된 프로필 시나리오**로 계산해야 한다.

## 왜 별도 M4가 필요한가

현재 M0-M3는 다음을 한다.

- M0: 길이
- M1: 길이 × 경사 penalty
- M2: M1 × 기상 additive factor
- M3: M1 × 기상+경사 상호작용 factor

하지만 비용함수에는 나이, 고령자 보행속도, 보행보조기, 계단 edge, 고령자별 기상 민감도가 없다. 고령 인구는 수요/노출 가중치로만 들어간다. 따라서 "고령자가 실제로 느끼는 접근비용"을 말하려면 M4가 필요하다.

## 전체 공식

권장 단위는 minutes다.

```text
edge_cost_m4_senior_min =
  length_m / (senior_flat_speed_m_per_s × 60)
  × slope_time_factor
  × weather_time_factor
  × step_time_factor
```

이렇게 하면 산출물이 해석 가능해진다.

- 속도: 고령자는 같은 거리도 더 오래 걸린다.
- 경사: 같은 거리도 오르막/내리막이면 시간이 늘어난다.
- 기상: 같은 경로도 비/눈/결빙에서는 부담이 커진다.
- 계단: 어떤 profile에서는 높은 부담이고, 어떤 profile에서는 접근 불가 barrier다.

## 1. 고령 보행속도

추천 profile:

| profile | 속도 | 사용 |
|---|---:|---|
| `very_slow` | 0.70 m/s | 보행보조기·매우 느린 보행자 민감도 |
| `slow` | 0.80 m/s | 취약 고령자, 보행보조기 가능성 있는 보수 시나리오 |
| `base` | 0.90 m/s | 기본 고령자 접근성 시나리오 |
| `optimistic` | 1.07 m/s | MUTCD 3.5ft/s와 비교 |
| `current_generic` | 1.12 m/s | 현행 67m/min 설정 비교용 |

근거:
- FHWA older pedestrian 자료는 고령 보행자가 일반 성인보다 느리며, 0.8~0.9m/s 수준의 설계 근거가 있음을 보여준다.
- MUTCD 11판은 pedestrian clearance 계산에서 3.5ft/s를 쓰지만, 느린 보행자가 많은 곳에서는 낮은 속도를 고려하도록 한다.
- 따라서 1.2m/s 일반 성인값을 고령자 기본값으로 쓰면 방어가 어렵다.

해석 예시:

```text
90m 평지:
0.90m/s → 1.67분
1.12m/s → 1.34분
```

즉 거리만 같아도 고령자 profile에서는 시간이 약 25% 늘어난다.

## 2. 고령 경사 민감도

경사는 두 겹으로 처리한다.

### 2.1 경사 band label

| grade_abs_percent | label | 이유 |
|---:|---|---|
| ≤2% | `near_flat` | 평지에 가까움 |
| 2~5% | `mild` | accessible walking surface 기준 안쪽 |
| 5~8.33% | `ramp_like` | 일반 보행면 기준을 넘고 ramp 영역 |
| 8.33~12% | `steep` | ramp 최대 경사를 넘는 고부담 |
| >12% | `very_steep` | 우회/현장검토 우선 |

5%와 8.33%는 ADA/Access Board 접근경로·ramp 기준에서 온 threshold다. 국내 장애인·노인·임산부 편의시설 기준도 외부 접근로 약 1/18(5.56%)과 경사로 1/12(8.33%) 구조를 사용하므로 한국 적용에서도 설명 가능하다. 이 값은 법적 판정이 아니라 보행 부담 해석 라벨이다.

### 2.2 slope_time_factor

권장은 Tobler hiking function을 그대로 쓰는 게 아니라, 고령자 평지속도에 정규화해 slope shape만 가져오는 것이다.

```text
s = signed_grade_percent / 100
slope_time_factor =
  exp(3.5 × (abs(s + 0.05) - abs(0.05)))

slope_time_factor = max(1.0, slope_time_factor)
```

이유:
- Tobler 함수는 slope를 walking velocity로 바꾸는 GIS 표준 출발점이다.
- 하지만 Tobler는 고령자 전용 함수가 아니다.
- 그래서 flat speed는 고령자 profile로 정하고, slope에 따라 속도가 변하는 모양만 Tobler에서 가져온다.

대안:
- 기존 M1과 비교하려면 `1 + alpha × grade`도 보조 산출한다.
- 이때 `alpha=0.03`은 현행 baseline, `0.06/0.09`는 senior sensitivity 실험으로만 둔다.
- 최종 주장은 `tobler_scaled`와 `linear_sensitivity`가 공통으로 잡는 후보에 집중한다.
- 보조 해석에는 `+5% ≈ 0.96×v0`, `+10% ≈ 0.89×v0`, `+15% ≈ 0.80×v0`처럼 평지속도 대비 감소율을 같이 제시한다.

## 3. 계단/steps

계단은 경사와 같은 연속 penalty가 아니라 discrete barrier로 다룬다.

현재 보행망에는 `highway`에 `steps`가 포함된 edge가 5,632개 있다. 따라서 모델링 단서는 이미 있다. 문제는 현행 비용함수가 이 값을 쓰지 않는다는 점이다.

추천 policy:

| policy | step factor | 해석 |
|---|---:|---|
| `steps_allowed` | 1.0 | 계단 미반영 비교군 |
| `steps_penalty` | 3.0 | 강한 부담으로 처리하는 탐색 시나리오 |
| `steps_barrier` | unreachable | 보행보조기/무장애 접근성 관점 |

가장 방어 가능한 주장은 `steps_barrier`다. Access Board/ADA의 accessible route는 walking surface, ramps, curb ramps, elevators, platform lifts 등으로 구성되며 stairs를 접근 가능한 route로 보지 않는다. 따라서 무장애 접근성 profile에서는 계단을 막는 것이 자연스럽다.

`steps_penalty=3.0`은 보정계수가 아니다. 단일 진실처럼 쓰면 안 되고, allowed/penalty/barrier 세 가지 민감도에서 반복되는 후보만 강건하다고 본다.

## 4. 기상

기상은 `보행 부담`과 `공간 변별력`을 분리해야 한다.

공식:

```text
weather_intensity = rain_mm + snow_weight × snow_cm
weather_time_factor = 1 + beta_weather × weather_intensity
```

추천 profile:

| profile | beta | snow_weight | 해석 |
|---|---:|---:|---|
| `dry` | 0 | 0 | 기상 부담 없음 |
| `rain` | 0.03 | 5 | 현행 M3와 정렬 |
| `snow` | 0.03 | 8 | snow/ice 고부담 |
| `senior_weather_high` | 0.05 | 8 | 취약 고령자 상한 시나리오 |

중요한 한계:
- Clarke et al.과 Delclòs-Alió et al.은 눈·비·온도가 고령자 walking/walkability 관계를 바꾼다는 근거를 준다.
- 하지만 그 값을 서울 hex별 비용계수로 바로 가져오면 안 된다.
- 현재 ASOS 단일 관측소 값은 모든 hex에 거의 동일하게 들어가므로, 공간 순위를 크게 바꾸지 못한다.
- 공간 변별력을 원하면 결빙 민원, 제설 취약 보도, 침수/배수, 그늘/일사, 보도 포장 상태 같은 local exposure 자료가 필요하다.

## 구현 산출물

Edge table:

- `senior_flat_speed_m_per_s`
- `senior_base_time_min`
- `grade_band`
- `senior_slope_factor`
- `weather_profile`
- `senior_weather_factor`
- `is_steps_edge`
- `step_policy`
- `senior_step_factor`
- `cost_m4_senior_min`

Hex table:

- `access_cost_m4_senior_min`
- `access_cost_m4_senior_reachable`
- `access_cost_m4_senior_profile`
- `access_cost_m4_senior_weather`
- `access_cost_m4_senior_step_policy`
- `step_edges_on_m4_path`
- `uses_steps_on_m4_path`
- `senior_vulnerability_m4`

## 검증 기준

| 검증 | PASS | FAIL |
|---|---|---|
| M0-M3 보존 | 기존 컬럼과 값 불변 | 기존 M0-M3를 덮어씀 |
| 속도 | 0.70/0.80/0.90/1.07 profile 산출 | generic 67m/min만 사용 |
| 경사 | signed grade 우선, abs fallback 기록 | grade band/factor 미기록 |
| 계단 | allowed/penalty/barrier 3개 비교 | steps edge 미사용 |
| 기상 | dry/rain/snow/high 비교와 ASOS 한계 명시 | 기상계수를 보정값처럼 주장 |
| 경로 | M4 기준 Dijkstra 재탐색 | 기존 M3 경로에 cost만 치환 |
| 효과 | Spearman/Jaccard/top-K 교체율 보고 | M4가 순위를 바꿨는지 미검증 |

## 기존 정책 산출물 해석 경계

현재 존재하는 S1/S3/S4 산출물은 M4-senior 구현의 근거 자료가 될 수는 있지만, 정책효과 검증 완료로 쓰면 안 된다.

- S1: `S1_all_48_candidate_stops_upper_bound` 상한선 스크리닝이다. 49개 hidden이 해소된 것으로 보이지만, 48개 후보를 모두 추가한 조건이고 도로운영·도로폭 타당성이 검증되지 않았다.
- S3: affected 진단은 있으나 resolved vulnerable/hidden이 0으로 확인되어, 보행환경 개선 효과 성공 사례라기보다 네트워크 규칙상 영향 여부 진단이다.
- S4: weather top20 후보 순위표는 쓸 수 있지만, 행정 라벨 결측과 ΔV 부재 때문에 보고서 주표 전 QA가 필요하다.

따라서 M4-senior 도입 후에도 표현은 "탐색적 후보", "상한선", "현장검토 우선순위"로 제한한다.

## 보고 문장

써도 되는 문장:

> M4-senior는 고령자 평지 보행속도, 경사별 통과시간 변화, 계단 barrier/penalty, 기상 시나리오를 분리해 계산한 네트워크 접근비용이다. 관측 보행자료로 보정된 행동모형이 아니므로 profile sensitivity로 해석한다.

쓰면 안 되는 문장:

> 이 계수들은 고령자의 실제 보행시간을 정확히 예측한다.

써도 되는 문장:

> M4에서 새로 드러난 후보는 "고령자 보행 프로필에서 추가로 취약해지는 현장검토 후보"다.

쓰면 안 되는 문장:

> M4 후보는 실제 고령자 탑승수요가 증가할 지역이다.

## 근거 링크

- FHWA Older Drivers and Pedestrians Handbook: https://www.fhwa.dot.gov/publications/research/safety/humanfac/01103/ch1.cfm
- MUTCD 11th Edition Part 4: https://mutcd.fhwa.dot.gov/pdfs/11th_Edition/part4.pdf
- ADA Accessible Routes: https://www.access-board.gov/ada/guides/chapter-4-accessible-routes/
- 국내 편의시설 기준 검색: https://www.law.go.kr/
- CODIL 편의시설 설계·시공 자료: https://www.codil.or.kr/filebank/original/RK/OTKCRK230438/OTKCRK230438.pdf
- FHWA Pedestrian Safety Guide for Transit Agencies: https://highways.dot.gov/safety/pedestrian-bicyclist/pedestrian-safety-guide-transit-agencies/chapter-4-actions-increase
- TCRP Report 153: https://nacto.org/wp-content/uploads/1-4_Coffell-et-al_Guidelines-for-Providing-Access-to-Public-Transportation-Stations_TCRP-153_2012.pdf
- Tobler 1993: https://geodyssey.github.io/papers/tobler93.html
- Goodchild 2020: https://doi.org/10.1111/gean.12253
- Akinci et al. 2022: https://link.springer.com/article/10.1186/s12877-022-03233-x
- Edwards & Dulai 2018: https://link.springer.com/article/10.1186/s12889-018-5945-0
- Clarke et al. 2017: https://pmc.ncbi.nlm.nih.gov/articles/PMC5423849/
- Delclòs-Alió et al. 2020: https://pmc.ncbi.nlm.nih.gov/articles/PMC6981853/
