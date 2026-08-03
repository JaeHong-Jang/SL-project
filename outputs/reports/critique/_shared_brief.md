# 팀 공유 브리프: 취약지역 분석 정규화 방법론 비판

## 연구 목적
서울시 보행환경(경사·기상) 반영 대중교통 접근성 분석.
- 4,551개 H3 res9 hex(≈174m) 격자, 분석 유효 4,383개.
- 목표 흐름: **취약지역 탐지 → 시나리오 설계(정류장 신설/경사대안경로 등) → 시나리오 대비 baseline 개선효과 측정 → 정책 제안.**

## 현재 방법론 (vulnerability.py, metrics.py 검증 완료)
```
취약도_i = cost_m3_norm_i × demand_norm_i

# 정규화: BaselineNormalizer (단순 min-max)
cost_m3_norm   = (access_cost_m3 - min) / (max - min)
demand_norm    = (demand_index   - min) / (max - min)
vulnerability  = cost_norm * demand_norm

# 취약 hex 정의: 정규화 취약도의 상위 20% 분위(quantile 0.8) 이상
threshold = quantile(vulnerability, 0.8)
vulnerable = vulnerability >= threshold

# hidden vulnerable: 공식 400m 직선거리 기준은 ok이지만, M3 기준 vulnerable
hidden = (access_cost_m0 <= 400m) AND vulnerable
```
- M0: 보행네트워크 직거리 비용(미터)
- M1 = M0 + 경사 페널티
- M2 = M1 + 기상 페널티
- M3 = M2 + 경사×기상 상호작용 페널티 (메인)
- `demand_index_final` = 등록인구·등록고령인구·POI 정규화 가중합

## 실측 분포 (분석 유효 4,383 hex)

### access_cost_m3 (raw, 단위 m) — 강한 right-skew
| n | min | p10 | p25 | median | mean | p75 | p90 | max | std |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4383 | 0.0 | 85.9 | 279.8 | 169.8 | 212.3 | 279.8 | 420.8 | **4126.2** | 216.6 |

- **mean/median = 1.25, max/median ≈ 24배** → 강한 right-skew (long upper tail)
- median 169m vs 일부 hex 4126m → 분포가 매우 비대칭

### cost_m3_norm_final (min-max 정규화 후)
| min | p10 | p25 | median | mean | p75 | p90 | max |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.0 | 0.0 | 0.021 | **0.041** | 0.051 | 0.068 | 0.102 | 1.0 |

- median이 max의 **4.1%**에 불과 → outlier 한두 개가 척도를 압도
- p90도 0.102 → 90% hex가 0.1 이하 좁은 구간에 압축

### demand_norm_final (min-max 정규화 후) — 비교적 평탄
| min | p10 | p25 | median | mean | p75 | p90 | max |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.0 | 0.207 | 0.299 | **0.402** | 0.398 | 0.492 | 0.576 | 1.0 |

### vulnerability_m3_final (cost_norm × demand_norm)
| min | p10 | p25 | median | mean | p75 | p90 | max |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.0 | 0.0 | 0.007 | **0.0154** | 0.0186 | 0.026 | 0.038 | **0.4454** |

- mean/median = 1.21, max/median ≈ **29배** → 비용 정규화의 압축을 그대로 상속
- threshold(0.8 quantile) = 0.0288 → vulnerable hex 877개

## 우려 사항(가설)
1. **압축 효과**: min-max는 outlier에 민감. 비용의 long-tail이 정규화 후 90% hex를 [0, 0.1] 좁은 구간에 몰아넣어, **격자 간 차등화 신호가 약함**.
2. **곱셈 모델의 비대칭성**: 비용 정규화가 작아 곱이 작아짐 → 수요 정규화 차이가 더 크게 반영됨. "취약도" 점수가 사실상 수요 점수에 가까워질 위험.
3. **시나리오 평가**: BaselineNormalizer는 baseline의 min/max를 고정해 시나리오에 적용. 좋은 점은 척도 안정성. 그러나 baseline outlier가 평가 스케일의 분모를 정의함. 시나리오로 일부 hex 비용이 줄어도 분모(max)가 안 변하면 개선 폭이 매우 작아 보일 수 있음.
4. **상위 20% threshold**: 분포가 압축되면 0.0288 근처에 점수가 몰려, 작은 정규화 노이즈로 vulnerable/not의 경계가 흔들릴 위험.

## 대안 후보 (검토 필요)
- 분위수(rank/percentile) 정규화: outlier-robust, 균등 분포
- log(1+x) 후 min-max: 비용 long-tail에 적합
- Winsorize(예: p99 cap) 후 min-max
- z-score (평균 0, 표준편차 1) → 곱이 아닌 가중합/지수 표준화
- 가중합(cost_norm + demand_norm) vs 곱셈 (HM index 같은 trade-off 모델)
- 별도 분리 평가: 취약도를 단일 점수가 아니라 (비용, 수요) 2D 사분면으로 분류

## 정책/시나리오 평가 측면 요구
- 시나리오 전후 격차가 정량적으로 비교 가능해야 함
- "개선이 어디서 가장 큰가"가 격자 단위로 해석 가능해야 함
- robust해야 함 (한두 hex outlier로 권고가 뒤집히면 안 됨)
- 외부 사례·지표(예: 미국 EJSCREEN, UK IMD, OECD vulnerability index, transit equity 문헌)와 비교 가능하면 좋음

## 산출 위치
- `outputs/reports/critique/01_analysis_rationale.md`  (팀원1)
- `outputs/reports/critique/02_methodology_review.md`  (팀원2)
- `outputs/reports/critique/03_literature.md`          (팀원3)
- `outputs/reports/critique/04_figures.md` + `outputs/figures/critique/*.png` (팀원4)
- `outputs/reports/critique/00_lead_critique.md`       (팀장, Wave 2)
