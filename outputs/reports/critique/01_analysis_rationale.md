# 01. 분석 방법론 정당화 (팀원1 · 데이터 분석가)

> 입장: 본 보고서는 현재 방법론(H3 res9 격자 · `access_cost_m3` · `demand_index_final` · BaselineNormalizer min-max · 곱셈 모델 · 0.8분위 threshold)이 **왜 그렇게 설계되었는지**를 변호한다. 다만 옹호만 하지 않고, 자체 검증으로 드러난 한계도 같은 자리에서 인정한다.
> 표기: **코드상 사실**(파일·줄 인용 또는 직접 산출한 수치)과 **해석**(설계 의도·정책 함의)을 구분한다.

---

## 1. 데이터 선택과 전처리 근거

### 1.1 왜 H3 res9 (≈174m) 인가

- **코드상 사실**: 분석 격자는 `data/derived/hex_vulnerability_final.parquet` 기준 총 4,551 hex, 분석 유효 4,383 hex. H3 res9의 평균 변(edge) 길이는 약 174m, 평균 면적 ≈ 0.105 km² 다.
- **해석**:
  1. **보행 분석에 적합한 공간 단위**. 도시 보행 통근 평균 4–5분 거리(약 300–400m)는 res9 셀의 2–3개 이내에 들어온다. 셀 자체가 "한 정류장 도보권"과 비슷한 스케일이라, hex 단위로 취약·hidden을 표지(label)하면 정책 단위(정류장 신설·경사 우회로 1개)와 1:1로 대응시킬 수 있다.
  2. **행정동(평균 1–2 km²) 대비 30~50배 미세**. 행정동 평균으로 보면 가려지는 microscale 불평등(같은 동 안의 경사지/주거단지 끝)을 잡아낼 수 있다. 동시에 res8(평균 변 ≈ 460m)에 비해 너무 거칠지도, res10(≈66m)처럼 보행 노이즈가 과도하지도 않다.
  3. **균등 면적·균등 인접**이라 거리·면적 보정 없이 산술 연산이 가능. min-max·rank·quantile 같은 분포 통계가 셀 단위에서 직접 의미를 갖는다 (사각 grid는 인접 6/4 비대칭, 행정동은 면적 편차가 100배 이상).

### 1.2 왜 M3가 메인 비용인가

- **코드상 사실**: `vulnerability.py:50, 73, 77`에서 `m3_cost_col = "access_cost_m3"`를 cost normalizer의 입력으로 고정. 정의는 M0(직선 보행거리) → M1=M0+경사 → M2=M1+기상 → M3=M2+경사×기상 상호작용. `audit_vulnerability_table`은 `m0 ≤ m1 ≤ m2 ≤ m3` 단조성을 점검한다(vulnerability.py:253–257).
- **해석**:
  1. **연구 문제 자체가 "경사·기상이 반영된 접근성"**. M0만 쓰면 공식 400m 기준과 같아져서 연구의 부가가치가 사라진다. M1/M2도 환경 영향의 일부만 누적할 뿐, 상호작용(예: "급경사 + 비"의 비선형 가중)은 빠진다.
  2. **policy lever와 정렬**. 시나리오는 "정류장 신설"뿐 아니라 "경사 우회로", "겨울철 제설 우선구역" 같이 환경 요인을 직접 건드리는 것이 핵심이다. M3는 이 세 lever 모두에 반응하는 유일한 cost 변수.
  3. **단조성 보장으로 해석 안정성**: m1≥m0, m2≥m1, m3≥m2가 코드에서 강제·점검되므로 "환경 페널티가 더해질수록 cost가 단조로 커진다"는 약속이 데이터로 검증된 상태. → M3는 항상 worst-case 환경 비용으로 읽힌다.

### 1.3 왜 `demand_index_final`이 (등록인구 + 등록고령인구 + 생활인구 + POI)/4 인가

- **코드상 사실**(`src/sl_accessibility/population/hex_features.py:308–317`): final 단계에서
  ```
  demand_index_final = (registered_population_norm + registered_senior_population_norm
                        + living_population_norm + poi_total_norm) / 4
  ```
  prelim 단계(`hex_features.py:258–263`)는 (생활인구 + 고령생활인구 + POI)/3.
- **해석 — 각 구성요소의 역할**:
  - **등록인구(`registered_population`)** — *노출(exposure)* 차원. 그 hex에 거주하며 정류장 접근을 매일 필요로 하는 모집단.
  - **등록고령인구(`registered_senior_population`)** — *취약성(vulnerability proper)* 차원. 동일한 cost라도 보행 부담이 큰 인구를 추가 가중. 의도적인 over-weight: 한 인구 단위가 일반·고령 양쪽 합에 동시에 잡혀, 고령 비율이 높은 hex가 demand에서 +α를 받는다.
  - **생활인구(`living_population`)** — *주야간 보정*. 등록인구는 야간 거주지에 치우치고, 도심·역세권은 주간 유입이 더 큰 수요다. 생활인구를 평균으로 섞어 24h 평균 노출을 근사.
  - **POI 총합(`poi_total_count`)** — *목적지(destination) 측면 수요*. 정류장이 필요한 이유는 "사람 → 어디로 가야 하기 때문"이며, POI는 그 어딘가의 밀도를 나타낸다.
- 네 요소를 모두 min-max 정규화 후 단순 평균하는 것은 **각 차원의 동등 우선순위를 명시적으로 표명**하는 디자인이다. 가중치를 임의로 매기지 않음으로써 "왜 인구 0.4, POI 0.2인가?" 같은 자의성을 차단한다. (가중치 sensitivity는 향후 robustness 분석으로 보강 가능.)

---

## 2. 정규화 방식 선택 근거 — min-max + BaselineNormalizer

### 2.1 왜 min-max인가

- **코드상 사실**(`metrics.py:111–134`): `BaselineNormalizer.transform`은 `(x - minimum)/(maximum - minimum)`. z-score·rank·log 변환 없음.
- **해석 — 다른 선택지 대비 장점**:
  1. **단위 통일과 가독성**. cost(m)와 demand(0~1 가중합) 처럼 척도가 다른 두 차원을 곱하려면 `[0,1]`로 맞추는 것이 가장 직관적. z-score는 음수가 나와 곱 모델에 부적합(부호 뒤집힘, 큰 값×큰 값이 또 큰 값이 안 됨).
  2. **상위·하위 끝 의미 보존**. 정책 관점에서 "최악 hex"는 "max를 받은 hex"로 명확히 매핑된다. rank/percentile은 모든 셀이 균등 분포가 되어 "이 hex가 절대 기준으로 얼마나 나쁜가"를 잃는다 (예: 서울 전체가 좋아져도 rank top 20%는 항상 877개).
  3. **시나리오 비교의 일관성**. min/max가 baseline에서 고정되면 시나리오 적용 후의 0.05는 baseline의 0.05와 같은 의미. log·rank는 시나리오에서 분포가 바뀌면 재정의돼야 하고, 그러면 "개선 폭"이 정의되지 않는다.

### 2.2 왜 BaselineNormalizer(min/max 고정)인가

- **코드상 사실**(`metrics.py:118–122`): `fit`은 baseline 입력의 nanmin/nanmax를 잠금. 동일 인스턴스의 `transform`을 시나리오 데이터에 적용해도 분모가 변하지 않는다.
- **해석 — 시나리오 평가 관점**:
  1. **개선 폭의 수치적 의미 부여**. 시나리오로 cost가 줄어도 baseline의 min/max가 분모이므로, `Δcost_norm`은 "baseline 스케일에서 본 절대 변화"로 해석된다. 매 시나리오마다 min/max를 새로 잡으면 절대 비교가 깨진다.
  2. **취약 threshold 안정성**. baseline 0.8분위(=0.0288, 본인 검증 직접 산출)가 시나리오 평가에 그대로 쓰일 수 있다. threshold가 데이터에 따라 떠다니면 "시나리오로 877개 → 720개로 줄었다"는 종축 비교가 불가능.

### 2.3 한계 인정 — right-skewed 압축 효과

- **본인 직접 검증 결과**(전체 4,383 valid hex):

  | 변수 | min | p25 | p50 | p75 | p90 | p99 | max | skew | kurt |
  |---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
  | `access_cost_m3` (m) | 0.0 | 85.9 | 169.8 | 279.8 | 420.8 | 1031.3 | **4126.2** | 4.61 | 49.35 |
  | `cost_m3_norm_final` | 0.0 | 0.021 | 0.041 | 0.068 | 0.102 | 0.250 | 1.0 | 4.61 | 49.35 |
  | `demand_norm_final` | 0.0 | 0.299 | 0.402 | 0.492 | 0.576 | 0.740 | 1.0 | 0.08 | -0.08 |
  | `vulnerability_m3_final` | 0.0 | 0.007 | 0.015 | 0.026 | 0.038 | 0.071 | **0.445** | 5.02 | 88.88 |

- **사실**: cost raw의 mean/median = 1.25, max/median ≈ 24, **skew=4.61, 첨도 49.4** → 강한 right-skew. 정규화 후에도 분포의 모양(왜도)은 그대로 유지된다. 4,126m hex 한두 개가 max를 정의하므로 **90%의 hex가 [0, 0.10] 구간에 압축**된다.
- **수용 가능한 가정**:
  1. **outlier도 정책 신호**라는 가정. cost=4126m hex는 실제로 정류장 접근이 사실상 불가능한 hex일 가능성이 높고, 시나리오 평가의 "타깃 1순위". 압축은 부작용이지만, top-end의 의미를 유지하는 것이 정책 관점에서 더 중요.
  2. **취약 판정은 0.8분위 ordinal rule이므로 압축 자체가 분류를 망가뜨리지는 않는다**. min-max는 단조변환이라 vulnerability_m3_final의 순서를 바꾸지 않음. threshold도 quantile 기반이라 분포 모양에 robust.
- **그러나 인정해야 할 부분**:
  - 대안 정규화 시뮬레이션(본인 산출):

    | cost 정규화 방식 | median | mean | p90 |
    |---|---:|---:|---:|
    | min-max(현재) | 0.041 | 0.051 | 0.102 |
    | log1p + minmax | **0.617** | 0.559 | 0.726 |
    | winsorize(p99) + minmax | 0.165 | 0.201 | 0.408 |
    | rank(pct) | 0.500 | 0.500 | 0.900 |

  - log1p나 rank로 가면 분포가 평탄해진다는 점은 객관적 사실. 정책 보고용 **시각화/등급 매핑**에서는 cost_m3_norm을 표시하기보다 **percentile 또는 분위 등급(예: quintile)을 보조 컬럼으로 함께 제공**할 필요가 있다.

---

## 3. 곱셈 모델 (cost × demand) 선택 근거

### 3.1 왜 곱셈인가

- **코드상 사실**(`vulnerability.py:77`): `vulnerability_m3 = cost_m3_norm × demand_norm`.
- **해석 — 가중합 대비 장점**:
  1. **보완재(complement) 모델**. "접근비용도 높고 수요도 높은" **두 조건의 교집합**을 식별하는 것이 정책 우선순위. 가중합은 하나가 0이어도 다른 하나가 크면 score가 올라간다 — "사람이 거의 없지만 cost는 최악" 또는 "cost는 평범하지만 인구만 많은" hex가 같은 점수를 받는다. 정책적으로는 둘 다 만족해야 "우선 개입"이다.
  2. **AND 의미의 정량화**. 곱셈은 logical-AND의 연속 확장. demand=0 → vulnerability=0, cost=0 → vulnerability=0. 이는 "수요 없으면 취약 정의 자체가 의미 없음"과 정확히 일치하는 디자인 의도다.
  3. **국제 사례와 정렬**. UNDP HDI(과거 기하평균 전환 전 산술평균 사용으로 트레이드오프를 보상한다는 비판을 받음), Oxford MPI(곱셈/교집합), UK IMD의 multidimensional approach — 모두 "AND 의미"가 필요한 곳에선 곱이나 기하평균을 선택한다.

### 3.2 곱이 작아지는 문제와 정책 해석상 함의

- **사실**: cost_norm median 0.041 × demand_norm median 0.402 ≈ 0.0165, 곧 vulnerability median 0.015와 일치 — 정의대로 작동.
- **본인 직접 검증한 변동 분해**(log decomposition, nonzero n=3,932):

  | 항 | 값 |
  |---|---:|
  | std(log c) | 0.79 |
  | std(log d) | 0.43 |
  | cov(log c, log v) / var(log v) | **0.84** |
  | cov(log d, log v) / var(log v) | 0.16 |
  | Spearman(v, cost_norm) | **0.87** |
  | Spearman(v, demand_norm) | 0.24 |

- **해석**: 브리프의 우려("곱셈이 작아 곱 점수가 demand에 가까워질 위험")와 **정반대 결과**가 데이터에서 나왔다. cost_norm이 right-skew로 분산이 크기 때문에 — `var(log c) ≈ 3.4×var(log d)` — **곱 vulnerability의 변동을 cost가 약 84% 설명**한다. 즉 vulnerability_m3_final은 사실상 cost-driven 지표.
  - **변호 측면**: 이는 좋은 일이다. 연구 목적이 "환경 부담이 큰 접근성"인 만큼, vulnerability가 cost dominant가 되는 것이 의도와 일치.
  - **반론으로서의 한계**: 단, 이 결과는 demand_index가 4개 차원 평균으로 분산이 작아진 결과이기도 하다. demand 자체의 분리력이 약하다는 신호. demand 구성요소 중 어느 하나만으로(또는 다른 가중) 했을 때 어떻게 바뀌는지의 robustness check가 필요.

- **곱셈 vs 가중합 분류 일치도**(top 20% 기준, 본인 산출):
  - overlap = 419, only_mul = 458, only_alt = 458, **Jaccard = 0.31**.
  - 즉 두 모델은 절반 이상 다른 hex를 vulnerable로 지목한다. 곱셈 선택이 결과에 결정적이라는 뜻이며, 그 선택은 "AND 의미"라는 사전 정책 기준으로 정당화돼야 한다.

### 3.3 Threshold 0.8 분위 선택 근거

- **코드상 사실**(`vulnerability.py:36, 79–81`): `vulnerable_quantile=0.8`이 기본값, threshold = quantile(vulnerability, 0.8). 본인 검증: threshold=0.0288, vulnerable hex 877개(=4,383의 20.0%), hidden 632개.
- **해석**:
  1. **상위 20%는 우선순위 정책 디자인의 관행**. UK IMD 상위 20% Most Deprived Areas, EPA EJSCREEN의 80th percentile flag 등 다수 사회불평등 지표가 동일 컷.
  2. **분포 압축에도 분류는 안정적**. 0.8분위는 ordinal 기준이라 cost의 right-skew 압축이 분류 자체를 흔들지 않는다.
  3. **운영 가능성**. 4,383 × 0.2 ≈ 877 hex는 시나리오 평가에서 다룰 만한 단위 수(예: 정류장 신설 후보 수십~수백 개 매핑 가능).
- **민감도 검증**(본인 산출):

  | threshold v ≥ | hex count |
  |---:|---:|
  | 0.025 | 1,157 |
  | 0.028 (= 0.8q) | 928 |
  | 0.029 | 867 |
  | 0.030 | 809 |
  | 0.035 | 551 |

  - 사실: 0.025 → 0.030 구간(threshold ±10%)에서 vulnerable count가 348개(40%) 변동. **boundary가 압축된 분포 위에 놓여 있어 quantile 컷이 약간만 흔들려도 분류가 크게 흔들린다**. 이는 한계로 명시 인정한다. 완화책: hidden_vulnerable 판정에 official_400m_ok AND quantile 두 조건을 함께 쓰는 현재 설계(`vulnerability.py:82–83`)는 이 boundary 노이즈를 부분적으로 흡수한다.

---

## 4. 연구 목적 정합성 — 취약지역 탐지 → 시나리오 평가 → 정책

### 4.1 BaselineNormalizer가 시나리오 평가에 주는 일관성 이득

- **사실**: `BaselineNormalizer.fit`은 baseline에서 한 번만 호출되고, 같은 인스턴스의 `transform`이 모든 시나리오에 적용된다(`metrics.py:118–130`). threshold 역시 `vulnerability_threshold_final` 컬럼으로 hex별로 박혀 있다(`vulnerability.py:79–80`).
- **해석 — 정합성 이득**:
  1. **종축 비교가 가능**. baseline의 정상 hex(v=0.01)는 시나리오에서도 0.01 근처이며, baseline의 취약 hex(v=0.10)가 시나리오에서 0.05로 떨어졌다면 "취약도가 절반으로 줄었다"라고 그대로 읽힌다. 시나리오마다 min/max를 새로 잡았다면 이 문장은 성립하지 않는다.
  2. **취약/non-vulnerable 변화 카운트가 의미**. baseline에서 vulnerable 877 hex 중 시나리오에서 vulnerable이 아닌 hex 수가 그대로 정책 효과 지표가 된다(`metrics.py:95–108`의 `vulnerable_population_reduction`은 이를 인구 가중까지 합쳐 정량화).
  3. **다중 시나리오 비교 가능**. 시나리오 A·B·C 모두 같은 baseline min/max/threshold를 쓰므로 v_A − v_B 같은 직접 차감이 가능.

### 4.2 솔직한 자기평가 — right-skewed 데이터에서 정책 권고에 충분한가

- **충분한 부분**:
  - 우선순위 표시(쇼트리스트): 877개 vulnerable과 그 안의 632개 hidden은 분포 형태와 무관하게 *순위 기반*으로 정해진다. 정책 1차 후보 명단으로서는 본 방법론으로 충분.
  - 시나리오 평가의 **방향성**(개선/악화)과 **상대 크기**는 일관 척도 아래서 유효.

- **부족한 부분 — 명시적으로 인정**:
  1. **시각화·소통**: cost_m3_norm의 median이 0.041, p90가 0.10에 머무는 분포는 일반 청중에게 "거의 다 0"으로 보인다. 보고서 그림은 raw cost를 분위 등급(예: quintile)으로 보여주거나, log1p·percentile을 보조 축에 병기할 필요가 있음.
  2. **개선 폭의 체감 크기**: cost가 baseline 500m → 시나리오 300m으로 줄어도 cost_m3_norm으로 보면 0.121 → 0.073 (max=4126m이 분모) 으로 변화량 0.048 — 정책 보고서에 "5% 좋아졌다"로 잘못 전달될 위험. 시나리오 보고서에서는 **raw cost 변화량과 norm 변화량을 병기**하는 운영 규칙으로 보완해야 한다.
  3. **threshold boundary 민감도**(앞서 0.028~0.030에서 348 hex 흔들림): 시나리오 효과가 작을 때 — 예컨대 vulnerable hex의 v가 0.030에서 0.028로만 떨어진 경우 — "취약 → 비취약 전환"으로 카운트되지만 실질 개선은 미미할 수 있다. 보조 지표로 **continuous v의 변화량**과 **boundary buffer flag**(예: 0.024~0.034 사이 hex 별도 표시)를 권고.
  4. **곱셈의 cost-dominance**: 본 분석으로 vulnerability의 변동을 cost가 84%, demand가 16%만 설명함을 확인했다. demand 구성요소 가중치를 흔드는 robustness check 또는 demand 차원 분산을 명시적으로 확장(예: 등록고령인구 가중 ↑)하는 후속 분석이 필요.

- **종합 입장**: 현재 방법론은 "**상위 20% 취약 hex 탐지 + 시나리오 일관 평가**"라는 본 연구 목적에는 정합적이며, BaselineNormalizer·곱셈·0.8분위 컷은 각각 분명한 이유로 선택되었다. 다만 right-skewed cost 분포는 보고/소통 단계에서 보조 변환(percentile, log1p) 병기와 boundary buffer 표시를 통해 보완해야 한다. 위 보완은 핵심 모델을 바꾸지 않고도 적용 가능하다.

---

## 부록 A. 본 보고서가 인용한 코드 위치
- `src/sl_accessibility/accessibility/vulnerability.py:29-87` — `build_vulnerability`, 곱셈 정의·threshold·hidden 판정
- `src/sl_accessibility/accessibility/metrics.py:111-134` — `BaselineNormalizer` (fit/transform/threshold)
- `src/sl_accessibility/population/hex_features.py:258-263, 308-317` — `demand_index_prelim/final` 정의
- 데이터: `data/derived/hex_vulnerability_final.parquet` (n=4,551 / valid=4,383, 본인 직접 로드 및 분포 산출)

## 부록 B. 본 보고서에서 직접 산출한 핵심 수치
- threshold(0.8 quantile) = 0.0288, vulnerable=877, hidden=632
- skew(access_cost_m3)=4.61, kurt=49.35
- vulnerability 변동 분해: cost가 var(log v)의 84%, demand가 16% 설명
- Spearman(v, cost_norm)=0.87 vs Spearman(v, demand_norm)=0.24
- 곱 vs 가중합 top20% Jaccard = 0.31
- threshold ±10% 변동 시 vulnerable hex 카운트는 928 → 809로 119개(약 13%) 변동
