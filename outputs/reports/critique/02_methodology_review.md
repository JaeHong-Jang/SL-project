# 02. 방법론 타당성 검토 (팀원2 · 방법론 검토자)

> 입장: 본 보고서는 현재 방법론(`vulnerability_m3_final = cost_m3_norm × demand_norm`, BaselineNormalizer min-max, 0.8 quantile threshold)의 **수학적·통계적·공간분석적 타당성**을 비판한다. 분석 의도(팀원1)와 외부 문헌(팀원3)은 별도. 본 보고서는 "이 방법이 데이터 분포 가정·시나리오 평가 요구와 일치하는가"에만 집중.

---

## 1. right-skewed 분포에서 min-max 정규화의 통계적 부적합성

### 1.1 분포의 비정상성 정량 평가
실측 (`outputs/reports/critique/_T1_norm_distribution.csv`):

| 변수 | median | mean | p90 | max | skewness | kurtosis(excess) |
|---|---:|---:|---:|---:|---:|---:|
| `access_cost_m3` (m) | 169.8 | 212.3 | 420.8 | 4126.2 | **4.61** | **49.4** |
| `cost_m3_norm_final` | 0.041 | 0.051 | 0.102 | 1.000 | 4.61 | 49.4 |

- skewness ≈ 4.6, excess kurtosis ≈ 49 → **표준 정규(skew=0, kurt=0)와 극단적으로 거리가 멈**.
- min-max는 **선형 단조변환**이므로 skewness/kurtosis를 그대로 보존. 정규화 후에도 모양은 변하지 않음.
- 직관적 진단: p90(0.102)이 max(1.0)의 10.2%에 불과. **단 한 hex(4126m)가 max 분모를 정의**하므로 robust한 척도가 못 됨.

### 1.2 압축 메커니즘
min-max 식 `(x - min)/(max - min)`에서 분모는 baseline의 `max - min`. 이 값이 outlier 한 점에 의해 결정되면, 분자 대부분이 작아짐:
- 분모 = 4126 − 0 = 4126
- 90%의 분자 ≤ 421 → 90%의 정규화 ≤ 0.102
- 결과: hex 4,383개 중 약 3,945개가 **[0, 0.10]의 좁은 띠**에 몰림 (Fig 2, ECDF Fig 5b)

이는 다음 세 가지 부작용을 초래:
1. **threshold 안정성 저하**: 0.8분위가 0.0288 부근. hex score 분포가 이 컷 근처에 빽빽이 몰려, ε 수준 변동에도 vulnerable/non 경계가 흔들림. 시나리오 적용 시 cost 5m 차이가 분류를 뒤집을 수 있음.
2. **곱셈 모델의 영향력 비대칭화**: cost_norm median 0.04 vs demand_norm median 0.40 → 약 **10배 차이**. 곱에서는 cost가 작아 demand가 사실상 점수 변동을 주도. 가장 cost가 큰 hex(p99 이상)에서만 cost가 demand를 압도 → 분류가 **양극화**됨.
3. **시나리오 효과 측정 왜곡**: 정책 개입으로 cost가 200m → 150m로 줄면(25% 감소), cost_norm은 0.048 → 0.036으로 변화. demand_norm × 변화 = ΔV ≈ 0.005 수준 → 0.0288 threshold 대비 의미 있는 시그널 안 됨. **개선 효과가 압축돼 보이지 않음**.

### 1.3 정량 사례
시뮬레이션: 전체 분석 유효 hex의 cost를 일률 20% 감소시키면:
- 현재 방식: max 분모 그대로 → 모든 cost_norm이 80%로 축소 → vulnerability 80% 축소 → threshold 0.0288 미달로 떨어지는 hex만 vulnerable에서 빠짐. 하지만 cost·demand 모두 0.8 quantile 기준이라 vulnerable 카운트(877)는 거의 동일 → **개선 효과가 "더 이상 누가 vulnerable인가"로만 표현되고 "얼마나 좋아졌는가"로는 표현 안 됨**.

---

## 2. 대안 정규화 5가지 비교

기준: outlier robust, 시나리오 일관성(baseline-fit 가능 여부), 격자 차등화(median 위치), 정책 해석 직관성.

| 방법 | 수식 | outlier robust | 시나리오 일관성 | 격자 차등화 | 정책 해석 | 권고 등급 |
|---|---|---|---|---|---|---|
| **현재 min-max** | (x−min)/(max−min) | ✗ (1점이 분모 결정) | ◯ (baseline 고정 가능) | ✗ (median 0.04) | ◯ (절대 0~1) | **하** |
| **log(1+x) → min-max** | minmax(log(1+x)) | ◯ (분포 종형화) | ◯ (baseline log·min·max 모두 고정 가능) | ◎ (median 0.62) | △ (해석 시 log 인식 필요) | **상** |
| **rank (percentile)** | rank(x)/N | ◎ (단조 robust) | ✗ (시나리오에서 분포가 바뀌면 rank 재정의됨, 절대 비교 불가) | ◎ (정의상 균등) | ◎ (직관) | **중** (보조 지표 한정) |
| **winsorize(p1,p99) + min-max** | minmax(clip(x, p1, p99)) | ◯ (cap) | ◯ (cap 경계 고정 가능) | △ (median 0.16, 일부 개선) | ◯ | **상-중** |
| **z-score** | (x−mean)/std | ✗ (mean·std가 outlier에 민감) | △ (baseline mean·std 고정 가능) | ◯ (정규형 가정) | ✗ (음수 발생 → 곱셈 무의미) | **하** |

**해석**:
- **log+min-max가 통계적·정책적으로 가장 균형 잡힌 선택**. raw가 종형에 가까운 분포가 되어 격자 차등 신호가 살아남. baseline의 log min/max를 고정하면 시나리오 비교도 가능.
- **rank는 robustness는 최강이지만 절대 비교가 불가능** → 시나리오 평가 목적과 충돌. 그러나 정책 커뮤니케이션 보조(예: "이 hex는 상위 5% 보행접근비용")로는 우수.
- **winsorize는 보수적 절충안**. 변경 폭이 작고(현재 vulnerable과 Jaccard 0.99), 기존 결과의 큰 흐름을 유지하면서 극단 outlier 영향만 통제.
- **z-score는 곱셈 모델과 부적합** (음수). 가중합 모델에서만 고려.

---

## 3. 곱셈 vs 가중합 vs 사분면 분류

| 결합 방식 | 식 | 의미 | 본 연구 적합성 |
|---|---|---|---|
| **곱셈(현재)** | cost_norm × demand_norm | 두 조건의 교집합("AND") | ◯ (cost·demand 둘 다 높은 hex가 진짜 우선순위) |
| **가중합** | α·cost + β·demand | 가중 평균 ("OR" 또는 합산) | △ (한쪽이 0이어도 점수 발생 → 정책 의의 약함) |
| **사분면 분류** | (cost_norm ≥ 중위, demand_norm ≥ 중위) 등 4그룹 | 유형별 차등 대응 | ◎ (정책 시나리오와 1:1 매핑 가능) |

**평가**:
- 곱셈은 본 연구의 정의("취약=고비용·고수요")에 가장 충실. 다만 cost가 압축돼 있으면 곱셈의 의미가 demand 단독으로 환원되는 위험(§1.2).
- **사분면 분류**는 추가 산출물로 강하게 권장. 곱셈 점수 단일 ranking 대신:
  - Q1 (high cost, high demand) = 정책 1순위 (정류장 신설)
  - Q2 (high cost, low demand) = 시설 유치 또는 자율차 등 보완책
  - Q3 (low cost, high demand) = 기존 정류장 강화·신호개선
  - Q4 (low cost, low demand) = 모니터링 대상
- 이 매핑은 시나리오 lever별 ROI 추정을 가능하게 함.

---

## 4. baseline-fit 정규화의 시나리오 함의

### 4.1 baseline 고정의 의도된 장점
- baseline의 min/max를 잠그면 시나리오 결과의 0.05와 baseline의 0.05가 **같은 절대 척도**로 해석됨 → "개선 폭"이 정량 비교 가능.
- threshold(0.8q) 자체도 baseline에서 정의되므로 시나리오 적용 시 "vulnerable에서 빠진 hex 수"가 일관된 의미를 가짐.

### 4.2 잠재 위험
시뮬레이션 시나리오: 강서구 일부 hex 50개에 정류장 신설로 cost가 평균 40% 감소.
- baseline max(4126m)는 이 시나리오에서도 그대로 분모 → 개선된 50 hex의 cost_norm이 0.10 → 0.06으로 줄지만, **전체 분포에서는 여전히 [0, 0.10] 좁은 구간 안에 머묾**.
- demand_norm × 변화 ≈ 0.4 × 0.04 = 0.016. 이는 threshold 0.0288 대비 -55% 변동. **계량적으로는 큼**.
- 하지만 절대 vulnerability 점수는 0.040 → 0.024로 변화. 시각화 차원에서는 거의 비슷해 보임 → **개선이 정책 보고서에서 잘 드러나지 않는 시각적 압박** 발생.

### 4.3 완화책
- **log 도입**: 분모 영향력 감소. log(1+4126) ≈ 8.32 vs log(1+200) ≈ 5.30 → 비율 1.57. 현재 min-max(4126/200=20.6)의 1/13 수준으로 outlier 영향 완화.
- **이중 보고**: baseline-fit min-max(현재) + log-based 또는 percentile 보조 컬럼 동시 제공.
- **시나리오 효과 측정은 ΔV(절대) + Δrank(상대) 둘 다 보고**: 절대 변화는 작아도 rank 이동은 클 수 있음.

---

## 5. 권고 (Action items)

### 권고 1 ⭐ — log(1+x) + min-max로 cost 정규화 전환 (또는 보조 컬럼 추가)
- **왜**: 강한 right-skew(skew=4.61)에 대한 통계 표준 처리. 격자 차등화 신호 회복(median 0.04 → 0.62). Jaccard 0.40(§T2)에서 보이듯 **vulnerable 집합의 60%가 교체**되어, 현재 분류가 outlier-driven임을 강하게 시사.
- **기대효과**: 정책 보고서에서 격자별 차등 신호 회복, 시나리오 개선 효과 측정의 sensitivity 향상.
- **구현 부담**: `BaselineNormalizer`에 `log_transform: bool` 옵션 추가 + 호출부에 적용. 단위 테스트 추가(1~2시간).
- **위험**: 정책 해석자에게 "log 정규화" 설명 필요. 절대 비교 의미가 "log 척도에서의 비교"로 바뀜 → 보고서 작성 시 변환 명시.

### 권고 2 ⭐ — robustness 분석 의무화 (Jaccard, threshold sensitivity)
- **왜**: OECD JRC Composite Indicators Handbook(팀원3 §3)이 명시 권고. 본 연구 결과 Jaccard(현재 vs 대안)가 0.40~0.99로 크게 변동 → 단일 정규화 선택이 정책 권고를 좌우.
- **기대효과**: 권고의 신뢰성 입증, reviewer 비판 선제 대응.
- **구현 부담**: 본 보고서의 T1/T2 산출 코드를 패키지에 내장해 `make robustness` 형태로 재현 가능하게 (반나절).
- **위험**: 거의 없음. 보조 분석.

### 권고 3 — 사분면 분류 보조 산출
- **왜**: 시나리오 lever별 타깃을 단일 score ranking이 아니라 type별로 구분 (§3).
- **기대효과**: 정책 제안의 구체성·차별성 향상 (정류장 신설 vs 경사 우회로 vs 시설 유치 구분).
- **구현 부담**: cost_norm·demand_norm 중위값 기준 2x2 라벨 컬럼 추가 (수십 줄).
- **위험**: 추가 컬럼이 보고서 복잡도 증가 → 메인 한 컬럼 + 부록 한 컬럼으로 분리 권장.

### Trade-off 명시
- 권고 1을 채택하면 현재 베이스라인(877 vulnerable hex 중 60% 교체)와 큰 불연속이 생김. **과거 분석 결과와의 연속성** vs **통계적 적정성** 사이의 선택.
- 가장 보수적 합의는: **현재 min-max 유지 + log/winsorize/rank 3가지 보조 컬럼 동시 보고** → 분류 자체는 안 바뀌지만 reviewer가 sensitivity를 검증할 수 있게 함.
- 보다 권고되는 선택은: **log+min-max로 전환 + Jaccard 보고서로 변동 설명**. 통계적 표준에 부합하며, EJSCREEN·IMD 같은 국제 사례와 정렬됨(팀원3 §2).

---

## 핵심 권고 3행 요약

1. **log(1+x) + min-max로 cost 정규화 전환** — skew 4.61 분포에 대한 통계 표준 처리. vulnerable 60% 교체 위험은 robustness 보고로 통제.
2. **Robustness 의무화** — 4가지 정규화 결과를 동시 산출해 Jaccard·threshold sensitivity 보고. OECD JRC handbook 표준 권고.
3. **사분면 분류 보조 산출** — 곱셈 점수 단일 ranking 외에 (cost,demand) 2x2 유형 분류로 정책 lever별 타깃 차별화.
