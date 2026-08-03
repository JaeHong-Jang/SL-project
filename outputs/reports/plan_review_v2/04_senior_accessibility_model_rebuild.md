# Senior Accessibility Model Rebuild Review

작성일: 2026-05-31
대상 계획: `.omx/plans/demand-scenario-redesign-v2_2-2026-05-31.md`

## 4+1 판정

사용자 질문의 전제는 맞다. 연구 목적은 "고령자 접근성 취약 지점과 정책 제안"이고, 400m 직선거리/순수거리 기준이 고령자의 실제 보행 부담을 충분히 반영하지 못한다는 문제의식도 타당하다.

하지만 현재 산출물은 그 목적을 **완전히 구현한 고령자 전용 비용모형**이 아니다. 현재 구조는 다음과 같다.

| 층 | 현재 상태 | 판정 |
|---|---|---|
| 고령 수요/노출 | `registered_senior_population`, `senior_welfare`, `medical` POI 반영 | 구현됨 |
| 일반 경사·기상 접근비용 | M1/M2/M3에 경사·비·눈·상호작용 반영 | 구현됨, 연령공통 |
| 고령 보행속도 | 전역 `walking_speed_m_per_min: 67` helper만 있음 | 고령자별 최단경로 비용 아님 |
| 고령 경사 민감도 | 비용함수에 age/profile 입력 없음 | 미구현 |
| 계단/steps 페널티 | 보행망 `highway`에 `steps` edge는 있으나 비용 미사용 | 미구현 |
| 고령자별 기상 민감도 | S4 rank 후보에 고령인구 가중치만 있음 | 미구현 |

따라서 현재 M0-M3는 **연령공통 general walking access cost**로 명명해야 한다. 고령자 논문 claim을 열려면 별도 **M4-senior** 층이 필요하다.

## 팀별 결론

### Lane A. Repo Audit

코드 감사 결과:
- `src/sl_accessibility/accessibility/costs.py`는 `length_m`, `grade_abs_percent`, `rain_mm`, `snow_cm`만 받아 M0-M3를 만든다.
- `configs/model_params.yaml`의 `walking_speed_m_per_min: 67`은 전역 속도이며 고령자 profile이 아니다.
- `src/sl_accessibility/population/hex_features.py`는 고령 인구와 POI를 demand side에 넣는다.
- `data/walking_network_edges_with_slope_google.csv`에는 `highway`가 `steps`인 edge 단서가 있다. PowerShell 실측: 전체 467,556 edge 중 `steps` 포함 5,632 edge.

판정: 수요·노출에는 고령성이 있으나, 비용함수에는 고령자 전용 임피던스가 없다.

### Lane B. Architecture

권장 구조는 4층 분리다.

```text
1. demand_pressure_base
2. senior_exposure
3. age-common access_cost_m0..m3
4. senior_access_cost_m4
```

`registered_senior_population`을 demand에도 넣고 결과 집계에도 쓰면 고령성이 강화되어 보일 수 있지만, 이것은 비용 임피던스가 아니라 노출 가중이다. 따라서 `V_elderly`는 최소한 `senior_exposure_norm × senior_access_cost_m4_norm`를 포함해야 한다.

### Lane C. Literature

문헌·공식 지침은 M4-senior 방향을 지지한다.

- FHWA older pedestrian 자료는 고령자 보행속도가 일반 성인 설계값보다 낮을 수 있음을 보여준다.
- MUTCD 11th Edition은 기본 보행자 신호 속도 외에 느린 보행자가 많은 경우 더 낮은 속도 고려를 요구한다.
- ADA accessible route 지침은 경사·횡단경사·표면 상태를 접근성 요건으로 분리한다.
- transit access 지침과 TCRP 153은 정류장 접근을 원형 buffer가 아니라 실제 보행망, crossing, directness, 안전, 개인 특성으로 본다.
- 고령자 walkability 연구들은 일반 walkability index가 고령자 안전·지형·휴게시설·계단을 놓칠 수 있다고 지적한다.
- 눈·비는 고령자의 neighborhood walkability 효과를 수정할 수 있다.

참고:
- FHWA Older Drivers and Pedestrians Handbook: https://www.fhwa.dot.gov/publications/research/safety/humanfac/01103/ch1.cfm
- MUTCD 11th Edition Part 4: https://mutcd.fhwa.dot.gov/pdfs/11th_Edition/part4.pdf
- ADA Accessible Routes: https://www.access-board.gov/ada/guides/chapter-4-accessible-routes/
- FHWA Transit Agencies Pedestrian Safety Guide: https://highways.dot.gov/safety/pedestrian-bicyclist/pedestrian-safety-guide-transit-agencies/chapter-4-actions-increase
- TCRP Report 153: https://nacto.org/wp-content/uploads/1-4_Coffell-et-al_Guidelines-for-Providing-Access-to-Public-Transportation-Stations_TCRP-153_2012.pdf
- Akinci et al. 2022: https://link.springer.com/article/10.1186/s12877-022-03233-x
- Edwards & Dulai 2018: https://link.springer.com/article/10.1186/s12889-018-5945-0
- Clarke et al. 2017: https://pmc.ncbi.nlm.nih.gov/articles/PMC5423849/

### Lane D. Verification/Risk

위험 문장은 다음처럼 수정해야 한다.

- 기존의 모호한 고령인구 가중 표현 → "등록고령인구로 가중 집계한 연령공통 접근비용 감소"
- "계단 때문에 취약" → "현장검토상 계단 가능성이 있으나, 현재 산식에는 계단 페널티가 없다"
- "M3가 고령자 접근성" → "M3는 연령공통 baseline, M4-senior가 고령자 접근성"

## M4-senior 제안

최소 공식:

```text
edge_time_senior =
  length_m / senior_speed_m_per_s
  × grade_factor_senior(grade_abs_percent)
  × weather_factor(weather_scenario)
  × step_factor(highway contains steps)
```

필수 산출물:
- `access_cost_m4_senior`
- `senior_speed_m_per_s`
- `senior_grade_alpha` 또는 grade factor label
- `step_factor`
- `weather_scenario`
- `step_edge_count_on_path`
- `path_research_run = true`

검증:
- M0/M3/M4 Spearman
- top-K Jaccard와 hidden 후보 교체율
- 계단 edge 포함 경로 비중
- M4 경로 재탐색 전/후 차이
- 현장검토와 원인분류 일치율

## 연구 실패 여부

실패라기보다 **현재 모델의 정직한 범위가 드러난 상태**다. M3가 M0와 Spearman 0.9947이면, 현재 경사·기상 항은 순수거리 순위를 거의 재정렬하지 못한다. 이것은 "경사·기상 연구가 불가능하다"가 아니라 "지금 계수·데이터·연령공통 구조로는 고령자 체감 접근성을 충분히 분리하지 못한다"는 진단이다.

따라서 다음 단계는 M3를 버리는 것이 아니라, M3를 baseline으로 고정하고 M4-senior가 실제로 순위를 재정렬하는지 검증하는 것이다.

## 적용 결과

계획 문서에 다음을 반영했다.

- §0-ter 추가: 현재 M0-M3의 범위와 M4-senior 필요성
- §1, §7, §8-1, §9.1 표현 수정: 연령공통 비용과 고령자 전용 비용 구분
- §10 #16 추가: M4-senior 설계·비교표
- §11 2-bis 추가: M4-senior 구현 여부 결정 단계
- §12.5 한계 5 추가: 고령자 전용 임피던스 미구현
- §13.4 추가: 고령자 보행속도·경사·계단·기상 근거
