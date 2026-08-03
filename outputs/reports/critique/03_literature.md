# 03 문헌·사례 조사: 정규화 방법론 외부 근거

**작성자**: 팀원3 (문헌·사례 조사자)  
**작성일**: 2026-05-21  
**목적**: 본 연구의 min-max 정규화 + 곱셈 취약도 모델을 외부 문헌·사례와 비교하여 정당화 또는 반박 근거 제시

---

## 1. 보행접근성·교통형평성 분야의 취약도 지수 정규화 관행

### 1.1 Transit Deserts 연구 계보

**Jiao & Dillivan (2013)** 은 Transit Desert 개념을 공식화한 선구 논문이다. 4개 미국 도시(Charlotte, Chicago, Cincinnati, Portland)를 대상으로 대중교통 수요(transit demand)와 공급(transit supply)을 각각 지수화한 뒤, **수요 점수를 도시 전체에 걸쳐 정규화(normalized across the city)** 하고 공급을 차감하는 방식(demand - supply)으로 transit desert index를 산출했다. 정규화 방식은 min-max 계열이며, 결합 방법은 **차감(subtraction)** 이다.

- 출처: Jiao, J. & Dillivan, M. (2013). Transit Deserts: The Gap between Demand and Supply. *Journal of Public Transportation*, 16(3).
  URL: https://digitalcommons.usf.edu/jpt/vol16/iss3/2/

**Jomehpour Chahar Aman & Smith-Colin (2020)** 은 달라스(Dallas)를 대상으로 CPTA(Comprehensive Public Transit Accessibility) 점수를 제안했다. 수요·공급 격차를 비율(ratio) 또는 차이(gap) 방식으로 비교하는 접근을 사용하며, 취약 계층 형평성 렌즈를 명시적으로 도입했다.

- 출처: Jomehpour Chahar Aman, J. & Smith-Colin, J. (2020). Transit Deserts: Equity analysis of public transit accessibility. *Journal of Transport Geography*, 89.
  URL: https://www.sciencedirect.com/science/article/abs/pii/S0966692320309467

**함의**: 두 연구 모두 수요와 공급(또는 비용)을 **별도 정규화 후 결합**하는 패턴을 따른다. 단, 결합 방법은 본 연구의 곱셈(x)과 달리 차감(-) 또는 비율(÷)이다.

### 1.2 형평성 점수 산출의 정규화 선택 논쟁

Justice40 오픈소스 커뮤니티(미국 연방 환경정의 이니셔티브)는 percentile vs. min-max 정규화 비교를 공개 토론했다. 결론:

- **min-max**: 지역 맥락(local context) 보존, 상대적 위치 이해에 유리 → 동일 지역 내 격자 비교에 적합
- **percentile**: 설명이 쉽고 outlier에 robust → 다지역 비교·정책 커뮤니케이션에 유리

출처: Justice40 Open Source Community discussion (2021).
URL: https://groups.google.com/g/justice40-open-source/c/_TgP7B5hObc

---

## 2. 공간 취약성 지수(Spatial Vulnerability Index) 주요 사례

### 2.1 미국 CDC/ATSDR Social Vulnerability Index (SVI)

CDC SVI는 미국의 가장 권위 있는 공간 취약성 지수이다. **정규화 방법: percentile rank (0~1)**. 16개 인구통계 변수 각각에 대해 전국 센서스 트랙을 순위화하고, 4개 테마별로 percentile 합산 후 재순위화한다. 최종값이 높을수록 취약도가 높다.

> "A percentile ranking represents the proportion of tracts that are equal to or lower than a tract of interest in terms of social vulnerability."

- **선택 이유**: 극단값(outlier)에 robust하고, 비전문가에게 직관적이며, 임계값 설정(예: 상위 20%)이 용이함.
- **등가중치(equal weighting)** 적용: 모든 변수와 4개 테마 동등.

출처: CDC/ATSDR SVI FAQ.
URL: https://www.atsdr.cdc.gov/place-health/php/svi/svi-frequently-asked-questions-faqs.html
Documentation PDF: https://www.atsdr.cdc.gov/place-health/media/pdfs/2024/10/SVI2022Documentation.pdf

### 2.2 미국 EPA EJSCREEN

EJSCREEN은 환경정의 스크리닝 도구로, **percentile (0~100)** 기반 정규화를 사용한다. 환경지표 국가 percentile에 인구통계 지수(DI)를 **곱(multiplication)** 하여 EJ Index를 산출한다.

> "Each Demographic Index is then multiplied to the national percentile for a specific environmental indicator to calculate each of the EJ and Supplemental EJ indexes."

- EPA는 EJ index **80th percentile 이상** 지역을 환경정의 우선 분석 대상으로 지정.
- **주목**: EJSCREEN은 percentile 정규화 후 곱셈 결합을 사용한다는 점에서 본 연구의 곱셈 모델과 구조적으로 유사하나, 정규화 단계에서 min-max 대신 percentile을 택했다.

출처: EJSCREEN Technical Documentation v2.3 (2024).
URL: https://www.epa.gov/system/files/documents/2024-07/ejscreen-tech-doc-version-2-3.pdf

### 2.3 영국 IMD (Indices of Multiple Deprivation) 2019

영국 IMD는 **rank 기반 정규화 + 지수 변환(exponential transformation)** 을 사용한다. 핵심 설계 원칙:

1. 각 도메인 지표를 순위화(rank-based).
2. 지수 변환으로 **가장 취약한 끝단을 더 강하게 늘림** — "stretches out the deprived end of the distribution, inflating the deprivation scores at the most deprived end to ensure greater variation."
3. 도메인 간 합산 전 동일 분포로 표준화.

- **rank + exponential 변환 선택 이유**: 서로 다른 척도의 도메인들을 결합할 때 각 도메인 점수 분포가 가중치 설계를 왜곡하지 않도록 하기 위해.
- 결합 방법: **가중합(weighted sum)** (7개 도메인, 각기 다른 가중치).

출처: English Indices of Deprivation 2019 Technical Report (MHCLG, 2019).
URL: https://assets.publishing.service.gov.uk/media/5d8b387740f0b609909b5908/IoD2019_Technical_Report.pdf
Statistical Release: https://assets.publishing.service.gov.uk/media/5d8e26f6ed915d5570c6cc55/IoD2019_Statistical_Release.pdf

---

## 3. Right-Skewed 비용/이동시간 데이터의 표준 처리 관행

### 3.1 이동시간 분포의 right-skew는 교통 연구의 정형화된 사실

교통 연구에서 이동시간(travel time) 분포가 right-skewed이고 long tail을 갖는다는 것은 반복 확인된 사실이다.

> "Empirical evidence verifies the existence of highly-skewed travel time distributions with long/fat tails."

출처: Frontiers in Built Environment — "Review on Statistical Modeling of Travel Time Variability for Road-Based Public Transport" (2020).
URL: https://www.frontiersin.org/journals/built-environment/articles/10.3389/fbuil.2020.00070/full

### 3.2 Log 변환의 권고

Feng et al. (2022), "Best practice in statistics: The use of log transformation" (*Annals of Clinical Biochemistry*, PMC9036143)은 log 변환 권고 조건을 명시한다:

- "값이 양수 또는 0이고, 오른쪽으로 long tail이 존재할 때"
- 변환 후 "합리적으로 대칭인 분포"를 목표로 함
- 0 포함 데이터는 log(x + c) (c는 작은 상수, 일반적으로 1) 사용

**본 연구 데이터와의 관련성**: access_cost_m3의 max/median ≈ 24배, mean/median = 1.25로 강한 right-skew 확인. log(1+x) 변환이 통계적으로 권고되는 상황에 정확히 해당한다.

출처: PMC9036143.
URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC9036143/

### 3.3 Lognormal 분포의 우세

이동시간 분포 모델링 문헌에서 log-normal 분포가 "the most recommended and applied time distribution due to its good fit and relative simplicity"로 평가된다. log 변환이 통계적 편의를 넘어 실제 이동 비용의 인지적 특성(Weber-Fechner 법칙)을 반영함을 시사한다.

출처: Buechel, B. & Corman, F. (2018). Modelling Probability Distributions of Public Transport Travel Time. STRC 2018.
URL: https://www.strc.ch/2018/Buechel_Corman.pdf

---

## 4. 곱셈 vs 가중합 취약도 복합 지수 논의

### 4.1 OECD/JRC Composite Indicators Handbook (2008)

OECD와 유럽 JRC가 공동 발간한 복합지수 구성 표준 지침서. 핵심 내용:

- 정규화(normalization)는 "극단값이 이후 단계에 영향을 미치므로 주의 필요"
- **min-max, z-score, rank** 세 가지를 주요 방법으로 제시
- Right-skewed 분포에서 min-max는 outlier에 취약하다고 명시
- **Robustness 분석 필수 권고**: 정규화 방법, 결측값 대체, 가중치, 결합 방식 등에 대한 민감도 분석(sensitivity analysis) 수행 필요

출처: OECD/JRC (2008). Handbook on Constructing Composite Indicators.
URL: https://www.oecd.org/content/dam/oecd/en/publications/reports/2008/08/handbook-on-constructing-composite-indicators-methodology-and-user-guide_g1gh9301/9789264043466-en.pdf
Mirror: https://www.unescap.org/sites/default/files/JRC-OECD_Handbook%20Composite%20Indicators.pdf

### 4.2 가중합 vs 곱셈: Reckien (2018)의 실증 비교

Reckien, D. (2018). "What is in an index? Construction method, data metric, and weighting scheme determine the outcome of composite social vulnerability indices in New York City." *Regional Environmental Change*. DOI: 10.1007/s10113-017-1273-7.

핵심 발견:
- 가산(additive) vs. PCA 방법 간 "profound differences" 존재 — 방법론 선택이 공간 결과를 크게 바꾼다.
- 면적 기반 지표가 인구 비율 지표보다 방법 간 robust.
- 가산 방법은 취약 요인의 기여도가 알려진 경우 우선.
- 가중치 적용이 취약지역 수를 줄이고 노인·빈곤층을 핵심 요인으로 부각.

출처: PMC6448355.
URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC6448355/

### 4.3 UNDP HDI의 곱셈 전환 사례

UNDP는 인간개발지수(HDI)를 원래의 **가산 구조에서 곱셈(multiplicative) 구조로 개정**했다. 이유: 가산 모델은 지표 간 완전 대체(perfect substitutability)를 허용하여, 한 차원의 매우 높은 값이 다른 차원의 낮은 값을 상쇄할 수 있다는 문제. 곱셈 모델은 **약한 보완성(imperfect substitutability)** 을 구현한다.

출처: Assessment of Aggregation Frameworks for Composite Indicators in Measuring Flood Vulnerability (Scientific Reports, 2019).
URL: https://www.nature.com/articles/s41598-019-55994-y

**본 연구와의 관련성**: `취약도 = 비용_norm × 수요_norm` 곱셈 모델은 UNDP HDI 개정 논리와 동일하다. 비용이 낮거나(접근 쉬움) 수요가 낮으면 취약도가 낮고, 두 값이 모두 높을 때만 고취약으로 분류된다. 이는 "접근하기 어렵고 AND 접근이 필요한 사람이 많은" 지역만 고취약으로 분류하는 정책 직관에 부합한다.

---

## 5. 한국·서울 사례

### 5.1 조대헌 (2014) — KCI 등재 논문

조대헌. (2014). 서울의 고령일인가구 분포와 대중교통 접근성. *한국도시지리학회지*, 17(2), 119-136.

서울을 대상으로 고령 1인 가구 집중도와 대중교통 접근성의 **공간적 불일치(spatial mismatch)** 를 국지적 공간 통계(LISA)로 분석. "집중도는 높으나 접근성은 낮은 지역들이 국지적으로 산재"한다는 결론은 본 연구의 hidden vulnerable 개념과 직접적으로 대응한다. 구체적 정규화 방법은 초록에서 미명시이며, 접근성과 인구 분포를 별도 분석 후 공간 결합하는 방식 채택.

출처: KCI ART001903289.
URL: https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART001903289

### 5.2 서울시 보행밀도 취약지역 분석 (서울연구원, 2023)

"서울시 보행밀도 취약지역 분석을 통한 보행안전 관리 연구" (서울연구원, 소규모 연구 보고서 2023-12)는 서울시 보행 취약지역을 행정동 단위로 식별했다.

출처: 서울연구원.
URL: https://www.si.re.kr/sites/default/files/smallresearch/small-23-12.pdf

### 5.3 서울시 교통약자 서울동행맵

서울시는 교통약자를 위한 맞춤형 교통서비스 "서울동행맵"을 운영 중이며, GIS 기반 보행 취약지역 식별을 정책에 적용하고 있다.

출처: 서울시 스마트도시 포털.
URL: https://smart.seoul.go.kr/board/1/22520/board_view.do

### 5.4 국내 Min-Max 적용 사례

경기도 기후변화대응연구소의 생태계서비스 스코어 작성 방법에서 **정규화(Min-Max Scaling) → 지표별 가중치 적용 → 서비스별 점수 합산** 순서의 표준 워크플로가 확인된다. 국내 공공 지표 개발에서 min-max + 가중합 조합이 사실상의 표준 절차임을 보여준다.

출처: 경기도 기후변화대응연구소 데이터 작성방법 문서.
URL: https://climate.gg.go.kr/ips/data/pdf/데이터_작성방법_생태계서비스_스코어.pdf

---

## 6. 결론: 본 연구 방법론의 문헌 위치 및 권고 보완책

### 6.1 정규화 방법 비교표

| 방법 | Outlier 강건성 | 직관성 | 분포 왜도 처리 | 주요 사용 사례 |
|------|--------------|--------|--------------|--------------|
| Min-max | 낮음 | 높음 | 미처리 | 국내 지자체 지표, 일부 transit 연구 |
| Percentile/rank | 높음 | 높음 | 균등화 | CDC SVI, EJSCREEN, UK IMD |
| Z-score | 중간 | 중간 | 정규화 가정 | 학술 연구 일반 |
| Log(1+x) + min-max | 높음 | 중간 | 왜도 감소 | 이동시간 분포 연구 권고 |

### 6.2 핵심 판단

**본 연구의 곱셈 모델은 문헌상 정당화 가능하다.** EPA EJSCREEN이 percentile × 인구통계지수 구조를 사용하고, UNDP HDI 개정이 가산에서 곱셈으로 전환한 것은 직접적 선례이다.

**그러나 min-max 정규화는 본 연구 비용 분포(max/median ≈ 24배)에 부적합하다.** OECD/JRC 핸드북이 명시하는 "outlier가 척도를 지배하는" 상황이며, CDC SVI·EJSCREEN·UK IMD 등 3개 대표 공공 지수가 모두 percentile/rank 방식을 선택한 것은 강력한 반증이다. 현재 비용 정규화 후 90% hex가 [0, 0.1] 구간에 압축되는 현상은 이 우려의 직접적 실현이다.

### 6.3 문헌에서 가장 자주 함께 보고되는 Robust 보완책 (우선순위 순)

1. **Log(1+x) 변환 후 min-max** — 비용 데이터에 직접 적용 가능한 가장 간단한 개선. 교통 이동시간 right-skew에 대한 표준 권고 (Feng et al. 2022; Buechel & Corman 2018).
2. **Percentile rank 정규화** — CDC SVI·EJSCREEN·UK IMD 공통 선택. Outlier 영향 완전 제거, 균등 분포 보장. 시나리오 비교 시 "baseline 대비 percentile 개선폭"으로 직접 표현 가능.
3. **민감도 분석(sensitivity analysis)** — OECD/JRC 핸드북 핵심 권고. 정규화 방법 변경 시 취약 hex 877개 중 얼마나 바뀌는지 확인해 결론의 robustness를 실증.

---

## 참고문헌

1. Jiao, J. & Dillivan, M. (2013). Transit Deserts: The Gap between Demand and Supply. *Journal of Public Transportation*, 16(3). https://digitalcommons.usf.edu/jpt/vol16/iss3/2/

2. Jomehpour Chahar Aman, J. & Smith-Colin, J. (2020). Transit Deserts: Equity analysis of public transit accessibility. *Journal of Transport Geography*, 89. https://www.sciencedirect.com/science/article/abs/pii/S0966692320309467

3. CDC/ATSDR. (2022). SVI 2022 Documentation. https://www.atsdr.cdc.gov/place-health/media/pdfs/2024/10/SVI2022Documentation.pdf

4. CDC/ATSDR. SVI Frequently Asked Questions (FAQs). https://www.atsdr.cdc.gov/place-health/php/svi/svi-frequently-asked-questions-faqs.html

5. Wolkin, A. et al. (2022). Comparison of National Vulnerability Indices Used by the CDC for the COVID-19 Response. *Public Health Reports*. DOI: 10.1177/00333549221090262. https://pmc.ncbi.nlm.nih.gov/articles/PMC9257512/

6. EPA. (2024). EJSCREEN Technical Documentation Version 2.3. https://www.epa.gov/system/files/documents/2024-07/ejscreen-tech-doc-version-2-3.pdf

7. MHCLG. (2019). English Indices of Deprivation 2019 Technical Report. https://assets.publishing.service.gov.uk/media/5d8b387740f0b609909b5908/IoD2019_Technical_Report.pdf

8. MHCLG. (2019). English Indices of Deprivation 2019 Statistical Release. https://assets.publishing.service.gov.uk/media/5d8e26f6ed915d5570c6cc55/IoD2019_Statistical_Release.pdf

9. Reckien, D. (2018). What is in an index? *Regional Environmental Change*. DOI: 10.1007/s10113-017-1273-7. https://pmc.ncbi.nlm.nih.gov/articles/PMC6448355/

10. OECD/JRC. (2008). Handbook on Constructing Composite Indicators. https://www.oecd.org/content/dam/oecd/en/publications/reports/2008/08/handbook-on-constructing-composite-indicators-methodology-and-user-guide_g1gh9301/9789264043466-en.pdf

11. Scientific Reports. (2019). Assessment of Aggregation Frameworks for Composite Indicators in Measuring Flood Vulnerability. https://www.nature.com/articles/s41598-019-55994-y

12. Feng, C. et al. (2022). Best practice in statistics: The use of log transformation. *Annals of Clinical Biochemistry*. https://pmc.ncbi.nlm.nih.gov/articles/PMC9036143/

13. Frontiers in Built Environment. (2020). Review on Statistical Modeling of Travel Time Variability for Road-Based Public Transport. https://www.frontiersin.org/journals/built-environment/articles/10.3389/fbuil.2020.00070/full

14. Buechel, B. & Corman, F. (2018). Modelling Probability Distributions of Public Transport Travel Time. STRC 2018. https://www.strc.ch/2018/Buechel_Corman.pdf

15. 조대헌. (2014). 서울의 고령일인가구 분포와 대중교통 접근성. *한국도시지리학회지*, 17(2), 119-136. https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART001903289

16. Justice40 Open Source Community. (2021). Re-scaling options: Percentiles, min-max normalization, etc. https://groups.google.com/g/justice40-open-source/c/_TgP7B5hObc

17. 서울연구원. (2023). 서울시 보행밀도 취약지역 분석을 통한 보행안전 관리 연구. https://www.si.re.kr/sites/default/files/smallresearch/small-23-12.pdf
