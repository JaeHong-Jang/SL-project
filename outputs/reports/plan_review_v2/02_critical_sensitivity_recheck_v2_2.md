# v2.2 Critical Sensitivity Recheck

Date: 2026-05-31

Target: `.omx/plans/demand-scenario-redesign-v2-2026-05-29.md`

## Lead Verdict

v2 채택은 맞다. 다만 사용자가 제기한 의견은 대부분 타당하며, v2.1보다 한 단계 더 강한 보강이 필요했다. 핵심은 "계수 몇 개의 근거"보다 정규화, 결합 방식, 고령 수요축, threshold가 결과를 더 크게 움직인다는 점이다.

따라서 v2.2에서는 log/rank/winsorize/additive/demand-axis/threshold robustness와 사분면 분류를 선택 부록이 아니라 필수 수락 기준으로 격상했다.

## 4+1 Team Result

| Lane | 판정 | 핵심 근거 |
|---|---|---|
| A 방법론/데이터 | 부분 통과 | alpha/beta 민감도는 안정적이나, log/rank/additive/demand-axis가 취약 집합을 크게 바꿈. `snow_weight` 단독 민감도 artifact는 아직 없음. |
| B 시나리오 구조 | 수정 필요 | `FrozenBaseline` 설계는 타당하지만 `evaluate_scenario`가 실제 CLI/run pipeline에 연결되어 있지 않다. 현재 S4는 효과 추정이 아니라 후보 우선순위표다. |
| C 문헌/claim scope | 통과 | 접근성 스크리닝은 수요예측 없이 형평성 우선순위를 말할 수 있다. 단, 실제 수요 분산·증가·감소는 금지. |
| D 산출물 QA | 부분 통과 | v2 plan 자체는 final 632를 쓰지만 README/current audit 등은 prelim 732와 오래된 test count를 유지한다. 현재 pytest는 71 passed. |
| Lead 통합 | v2.2 보강 | v2 유지, 정규화/결합/수요축/threshold/시나리오 효과 라벨을 수락 기준으로 잠금. |

## Direct Recalculation Evidence

Source: `data/derived/hex_vulnerability_final.parquet`, universe-B = 4,383 valid hex.

| 항목 | 값 |
|---|---:|
| baseline vulnerable / hidden | 877 / 632 |
| M0-M3 Spearman rank correlation | 0.9947 |
| M0-M3 Pearson correlation | 0.9919 |
| `access_cost_m3` skew / max | 4.614 / 4,126m |
| median `cost_m3_norm_final` / `demand_norm_final` | 0.041 / 0.402 |
| hidden 평균 slope / weather / interaction increment | +27.2m / +18.1m / +1.8m |
| high-cost + high-demand among vulnerable | 98 / 877 = 11.2% |
| registered-pop vs senior-pop norm correlation | 0.8599 |

Sensitivity replacement rates:

| Variant | Vulnerable replacement | Hidden replacement |
|---|---:|---:|
| cost winsorize 1/99 | 0.9% | 0.6% |
| cost rank percentile | 30.0% | 23.8% |
| cost log1p | 60.4% | 57.6% |
| demand 3-axis, senior count removed | 25.3% | 29.2% |
| multiplicative -> additive | 68.6% | 69.0% |
| threshold 10/20/30% | hidden 252 / 632 / 1,040 | n/a |

Note: Lane A initially mixed up `demand_index_final` and `demand_norm_final`. Direct recalculation confirms the critique's 0.402 value is the median of `demand_norm_final`; raw `demand_index_final` median is 0.2176.

## User Questions

### 1. Are the weights defensible?

Partly. The visible cost coefficients should be described as scenario defaults, not calibrated or literature-derived weights. They are relatively stable under existing sensitivity checks, but that stability is partly because M3 barely reorders M0 distance.

The hidden choices are not defensible unless robustness is reported: normalization, multiplication vs addition, senior double-counting, and top-20 threshold move the result materially.

### 2. Was Monte Carlo used, and is the simulation valid?

Monte Carlo was not used. The current sensitivity work is deterministic variant / one-at-a-time checking.

The `FrozenBaseline` design is logically sound: fit baseline normalization and threshold once, then evaluate scenario cost against the same baseline. But current scenario artifacts are not all proven counterfactual effects. S4 is a diagnostic Top20. S1 has an upper-bound delta map in `qgis/S1_delta_vulnerability_map.gpkg`, but it still needs runner provenance, manifest, and path re-search evidence before being treated as final effect evidence.

### 3. Do we need a demand prediction model?

No for Track A. The defensible claim is accessibility burden redistribution and priority screening, not realized demand dispersion. Actual ridership increase/decrease or user redistribution requires observed demand data and a calibrated model.

## v2.2 Plan Changes Applied

- Added a claim-scope paragraph distinguishing burden redistribution from demand dispersion.
- Elevated log/rank/winsorize/additive/demand-axis/threshold checks to mandatory robustness gates.
- Added direct sensitivity evidence table to §5.
- Added senior double-counting/correlation gate to §6.1.
- Added product-vs-quadrant caveat: only 98/877 vulnerable hex are both cost and demand top 20%.
- Reframed S1 as placement/access-connection diagnosis unless runner + manifest + path re-search prove counterfactual effects.
- Reframed S4 as weather-response priority diagnosis; ASOS single-station and small interaction contribution must be stated.
- Expanded manifest conditional fields for effect claims: scenario cost hash, path re-search flag, threshold hash, and output label.

## Document Sync Risks

- `README.md` and `docs/current_status_audit_2026-05-13.md` still reference prelim 732 and older 46 passed state.
- `docs/working_plan.md`, `docs/분석_진행_정리.md`, and `docs/COLLABORATION_GUIDE.md` contain stale test counts.
- Final QA supports hidden 632; D lane verified current test run as 71 passed.
- `docs/분석_진행_정리.md` M3 formula includes beta, but the M3 parameter cell should list both `beta = 0.03` and `gamma = 0.08`.

## External Basis

- Hansen 1959 accessibility concept: https://www.tandfonline.com/doi/abs/10.1080/01944365908978307
- Geurs & van Wee 2004 accessibility review: https://projectwaalbrug.pbworks.com/f/Transp%2BAccessib%2B-%2BGeurs%2Band%2BVan%2BWee%2B%282004%29.pdf
- OECD/JRC composite indicator handbook: https://www.oecd.org/content/dam/oecd/en/publications/reports/2008/08/handbook-on-constructing-composite-indicators-methodology-and-user-guide_g1gh9301/9789264043466-en.pdf
- OECD/ITF accessibility framework: https://www.oecd.org/en/publications/transport-bridging-divides_55ae1fd8-en/full-report/component-5.html
- EPA EJSCREEN screening caution: https://www.epa.gov/sites/default/files/2016-07/documents/ejscreen_fact_sheet.pdf
- CDC/ATSDR SVI: https://www.atsdr.cdc.gov/place-health/php/svi/index.html
- UK IMD 2019 release: https://assets.publishing.service.gov.uk/media/5d8e26f6ed915d5570c6cc55/IoD2019_Statistical_Release.pdf
