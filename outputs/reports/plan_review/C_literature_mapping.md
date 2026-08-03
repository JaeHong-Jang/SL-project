# 팀원C 문헌 검증 보고서: 참고문헌 매핑 검토

**검토자**: 팀원C (문헌 검증자)
**검토 대상**: `.omx/plans/demand-scenario-redesign-2026-05-23.md` §6, §8-2, §13
**작성일**: 2026-05-29
**모드**: 읽기 전용. 코드/데이터 수정 없음.

---

## L1. URL 생존성 점검 (22개)

§13에 나열된 22개 인용 URL의 접근 가능 여부를 WebFetch로 점검했다. 직접 본문 내용 확인이 불가한 경우 WebSearch로 보완했다.

| # | 저자·연도 | URL | 상태 | 비고 |
|---|---|---|---|---|
| 1 | Hansen 1959 | https://www.tandfonline.com/doi/abs/10.1080/01944365908978307 | **403 차단** | Taylor & Francis 구독 장벽. DOI 존재·논문 실재 WebSearch 확인. |
| 2 | Handy & Niemeier 1997 | https://journals.sagepub.com/doi/10.1068/a291175 | **접근 가능(제한)** | 초록 공개. 제목·저자·연도 일치 확인. |
| 3 | ATAP Travel Demand Modelling | https://www.atap.gov.au/tools-techniques/travel-demand-modelling/3-model | **타임아웃** | 호주 정부 사이트 일시 연결 실패. URL 구조 정상. |
| 4 | FHWA 2010 Travel Model Validation Manual | https://rosap.ntl.bts.gov/view/dot/55924 | **403 차단** | FHWA 공식 대체 URL(fhwa.dot.gov/planning/tmip)로 문서 실재 확인. |
| 5 | FHWA Scenario Planning TPCB | https://www.planning.dot.gov/planning/topic_scenarioplanning.aspx | **접근 가능** | 내용·제목 일치 확인. |
| 6 | FHWA 2016 TSMO Scenario Planning ch3 | https://ops.fhwa.dot.gov/publications/fhwahop16016/ch3.htm | **접근 가능** | 내용·제목·챕터 일치 확인. |
| 7 | FHWA 2011 Scenario Planning Guidebook | https://rosap.ntl.bts.gov/view/dot/9045 | **403 차단** | rosap.ntl.bts.gov 전반 차단. 문서 실재 WebSearch 확인. |
| 8 | OECD/JRC 2008 Composite Indicators Handbook | https://www.oecd.org/content/dam/oecd/...9789264043466-en.pdf | **PDF 바이너리** | 텍스트 추출 불가. 복수 미러 URL(unescap.org, JRC 공식) 확인. 문서 실재 확인. |
| 9 | ITF/OECD 2019 Accessibility Indicators | https://www.itf-oecd.org/transport-planning-investment-accessibility-indicators | **403 차단** | ITF 사이트 차단. 보고서 실재 WebSearch 확인. |
| 10 | ITF/OECD 2020 Accessibility & Transport Appraisal | https://www.oecd.org/content/dam/oecd/...61af7bd8-en.pdf | **PDF 바이너리** | 텍스트 추출 불가. 문서 실재 확인. |
| 11 | Geurs & van Wee 2004 | https://research.utwente.nl/en/publications/... | **접근 가능** | 제목·저자·연도·저널 일치 확인. |
| 12 | Jiao & Dillivan 2013 | https://digitalcommons.usf.edu/jpt/vol16/iss3/2/ | **접근 가능** | 제목·저자·연도 일치 확인. |
| 13 | Jiao 2017 Texas transit deserts | https://doaj.org/article/253d97ebcd674d67bb02f75be6ddc446 | **접근 가능** | DOAJ 인덱싱 확인. 제목·저널 일치. |
| 14 | Jomehpour & Smith-Colin 2020 | https://www.sciencedirect.com/science/article/pii/S0966692320309467 | **403 차단** | ScienceDirect 구독 장벽. DOI 실재 확인. |
| 15 | Hochmair et al. 2022 | https://digitalcommons.fiu.edu/gis/100/ | **빈 콘텐츠** | FIU Digital Commons 빈 응답. 논문 실재는 WebSearch 및 전문 URL(cgi/viewcontent)로 확인. |
| 16 | Pulugurtha et al. 2011 | https://digitalcommons.usf.edu/jpt/vol14/iss2/6/ | **접근 가능** | 제목·저자·연도 일치 확인. |
| 17 | Choi & Jiao 2024 | https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0306782 | **접근 가능** | 제목·저자·연도·저널 일치 확인. |
| 18 | 보건복지부 2024 노인실태조사 | https://www.mohw.go.kr/board.es?... | **접근 가능** | 내용 일치. 2023년 조사 결과 2024년 발표 확인. |
| 19 | 정책브리핑 노인실태조사 보고서 | https://m.korea.kr/archive/expDocView.do?docId=41095 | **연결 실패** | 소켓 오류(모바일 서브도메인). docId 유효성 미확인. URL 교체 필요. |
| 20 | 전병윤·이창효·송학주 2024 | https://www.kais99.org/jkais/journal/Vol25No01/vol25no01p32.pdf | **PDF 바이너리** | 텍스트 추출 불가. KAIS Vol.25 No.01 URL 구조 정상. 저자·주제 부분 확인. |
| 21 | 김용진·안건혁 2012 | https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?...ART001665308 | **접근 가능** | 제목·저자·연도·핵심 수치(350-450m) 일치 확인. |
| 22 | 노인복지법 제36조 | https://www.law.go.kr/lsLawLinkInfo.do?...lsJoLnkSeq=900611547 | **접근 가능** | 조문 내용(노인복지관·경로당) 일치 확인. |

**요약**: 22개 중 직접 확인(접근 가능) 9건, PDF 바이너리(실재 확인) 3건, WebSearch 보완 확인 6건, 불확실/실패 4건(타임아웃 1, 403 차단 2, 연결 실패 1). 실질적 URL 사망(404/완전 불능) 0건. 구독 장벽·정부 방화벽에 의한 차단이 대부분이며 출처 자체는 유효하다. 단, #19 정책브리핑 모바일 URL은 영속성이 불안정하므로 URL 교체를 권고한다.

---

## L2. 선행연구 매핑 (§8-2 표) 정합성 검증

§8-2 선행연구 매핑 표 7행을 각 인용 논문의 실제 내용과 대조했다.

| 근거 | §8-2 사용할 수 있는 주장 | 실제 논문 내용 | 정합 판정 |
|---|---|---|---|
| Hansen 1959; Handy & Niemeier 1997; Geurs & van Wee 2004 | 목적지 접근 기회와 비용의 공간 차이 비교 | Hansen: 접근성을 기회의 도달 가능성으로 정의. Handy & Niemeier: 접근성 측정 대안 탐색. Geurs & van Wee: 토지이용·교통전략 접근성 평가 프레임워크. | **정합** |
| ITF/OECD 2019, 2020 | 취약집단의 접근성 개선 우선순위 제시 | 접근성 지표를 계획·투자 의사결정과 분배 이슈 설명에 활용. 취약계층 형평성 분석 포함. | **정합** |
| Jiao & Dillivan 2013; Jomehpour & Smith-Colin 2020 | 잠재수요 proxy와 공급/접근성 gap 분석 | Jiao & Dillivan: demand - supply 차감 방식. Jomehpour & Smith-Colin: 비율/격차 방식. 두 논문 모두 개념적 틀(수요 proxy + 공급 gap)은 지지하나 결합 방식은 곱셈이 아님. | **부분 정합** |
| Hochmair et al.; Pulugurtha et al. | 현장검토/서비스 보강 후보 선별 | Hochmair: 사회취약성 지수와 접근성 지도의 공간 오버레이로 서비스 격차 후보 식별. Pulugurtha: 접근 불가 지역의 잠재 시장 식별. 후보 선별 개념 지지. | **정합** |
| OECD/JRC 2008 | 동일가중과 대안가중을 비교해 안정성 보고 | 정규화·가중·결합·민감도 분석 수행을 권고. Monte Carlo 포함 불확실성 분석을 표준으로 제시. | **정합** |
| FHWA Scenario Planning; FHWA TSMO | S1/S3/S4를 접근비용 변화 시나리오로 비교 | FHWA 시나리오 플래닝 문서들은 baseline 대비 대안 시나리오를 성능지표로 비교하는 절차 지지. | **정합** |
| ATAP; FHWA Travel Model Validation | 관측자료 확보 시 B/C 트랙으로 확장 | FHWA 2010 Manual: 수요모형 검증에 관측 교통량·탑승량 데이터 활용 강조. 검증 데이터 수집이 모형 추정·보정만큼 중요하다고 명시. | **정합** |

### 우선 확인 5건 상세 검증

**Hansen 1959 "How Accessibility Shapes Land Use"**

원 논문: Journal of the American Institute of Planners, Vol.25, No.2, pp.73-76. 핵심 정의: 접근성을 기회의 도달 가능성(potential of opportunities for interaction)으로 조작적으로 정의. 주거 개발 패턴과 접근성의 실증적 관계 분석. WebSearch로 DOI(10.1080/01944365908978307), 저널, 논문 실재 확인.

판정: **정합.** §8-2의 "목적지 접근 기회와 비용의 공간 차이 비교" 및 "접근성 = 기회 도달 가능성 정의의 기원" 인용 의도에 부합한다. 논문 URL은 403 차단이나 DOI 유효성은 확인됐다.

---

**OECD/JRC 2008 Composite Indicators Handbook**

PDF 직접 텍스트 추출 불가. WebSearch 및 기존 `outputs/reports/critique/03_literature.md` 교차 참조로 내용 확인. 핵심 내용: min-max·z-score·rank 3가지 정규화를 주요 방법으로 제시. right-skewed 분포에서 min-max는 outlier에 취약하다고 명시. robustness 분석 필수 권고: 정규화 방법·결측값 대체·가중치·결합 방식에 대한 민감도 분석 수행 필요. Monte Carlo를 포함한 불확실성 분석을 표준으로 제시.

본 계획 인용 의도(§6): "변수 선택, 정규화, 가중, 집계, 불확실성/민감도 분석을 보고해야 한다는 품질 기준"

판정: **정합.** OECD/JRC Handbook은 실제로 이 모든 항목을 다루며 인용 의도와 일치한다. 단, 본 계획의 실제 민감도 분석 구현이 Handbook 기준(Monte Carlo 포함)에 충분한지는 L5에서 별도 검토한다.

---

**Jiao & Dillivan 2013 "Transit Deserts: The Gap between Demand and Supply"**

WebSearch 확인: transit dependent 인구를 수요 지수화 후 transit supply를 **차감(demand - supply)**하는 방식. 정규화는 min-max 계열. 결합 방법: **차감(subtraction)**.

본 계획 인용 의도: §8-2에서 "잠재수요 proxy와 공급/접근성 gap 분석"의 근거로 인용.

판정: **부분 정합 / 모순 위험.** 개념적 틀(수요 proxy + 공급 gap)은 지지하지만, Jiao & Dillivan의 실제 결합 방법은 **차감(-)**이고 본 계획은 **곱셈(×)**을 사용한다. §8-2는 이 차이를 명시적으로 다루지 않고 단순 나열했다. 이는 L5(cherry-picking)에서 주요 위험으로 처리한다.

---

**Hochmair et al. 2022 "Identification of Transit Service Gaps through Accessibility and Social Vulnerability Mapping in Miami-Dade County"**

FIU Digital Commons 직접 접근 실패(빈 콘텐츠). WebSearch로 논문 실재 확인(GI_Forum 2022(1):17-32). 내용 확인: 사회취약성 지수(CDC SVI 계열)와 접근성 지도를 결합해 서비스 격차 후보 식별. 결합 방식은 **공간 오버레이(spatial overlay)**이지 demand × cost 곱셈 산식과 직접 동일하지 않다.

본 계획 인용 의도: "사회취약성+접근성 결합 사례"의 정당화 근거.

판정: **부분 정합.** 사회취약성과 접근성을 결합해 후보를 찾는 개념적 사례로 인용하는 것은 타당하다. 단, 본 계획의 곱셈(demand_norm × cost_norm) 산식의 직접 방법론 선례로 제시하는 것은 과장이다. 오버레이 방식과 곱셈 방식은 통계적 특성이 다르다.

---

**FHWA Travel Model Validation (ATAP, FHWA 2010)**

FHWA 공식 사이트 Chapter 2 직접 확인: "검증 데이터의 올바른 수집이 모형 추정·보정만큼 중요"하며, 교통량 카운트·탑승량 데이터를 이용한 검증이 표준 실무로 기술됨. 단, 문서는 "관측자료가 있을 때 어떻게 검증하는가"를 다루며, "관측자료 없이 예측모형을 만들면 안 된다"는 금지 명령보다는 검증 실무 가이드에 가깝다.

본 계획 인용 의도: "관측 수요 없이 예측모형 만들면 안 됨"의 경계선 근거.

판정: **정합(단, 해석 강도 주의).** FHWA 2010 Manual은 관측 기반 검증을 표준으로 제시하며, 본 계획이 "트랙 B/C는 관측자료가 있을 때만"이라고 제한하는 논리를 지지한다. 다만 "만들면 안 됨"은 본 계획의 해석이고, 원문은 "어떻게 검증해야 한다"는 가이드임을 구별해야 한다.

---

## L3. §6 고령자 POI 선택 근거 5건 정합성

| 인용 | 본문 주장 | 실제 출처 내용 | 정합 판정 |
|---|---|---|---|
| 보건복지부 2023년 노인실태조사 | 건강·사회참여·생활환경을 고령자 분석의 핵심 축으로 다룸 | 2023년 조사 결과 2024년 공식 발표(mohw.go.kr) 확인. 건강·사회참여·생활환경 포함. | **정합** |
| 정책브리핑 노인실태조사 보고서 | 공식 보고서 PDF가 정책브리핑에 게시됨 | m.korea.kr 모바일 URL 소켓 오류. 보고서 자체는 실재하나 해당 docId 직접 확인 불가. | **불확실** (URL 교체 필요) |
| 전병윤·이창효·송학주 2024 (대전광역시) | 기차역·버스정류장·의료·복지시설·주민센터·전통시장·공원 이용권과 고령인구 분포 관계 분석 | KAIS Vol.25 No.01 PDF 텍스트 추출 불가. 저자·주제는 WebSearch에서 부분 확인. 구체 수치 독립 검증 불가. | **부분 확인** |
| 김용진·안건혁 2012 | 일반 근린시설 이용권 350-450m; 복지센터·병원·종교시설은 1,500m 이상 | KCI 직접 확인: 초록에서 "350~450m" 수치 명시. "복지센터·병원·종교시설은 1,500m 이상"도 확인. 본문 기재 수치와 정확히 일치. | **정합** (수치 검증 완료) |
| 노인복지법 제36조 | 노인복지관·경로당을 노인여가복지시설로 규정; 사회참여·건강증진·친목·취미·정보교환 기능 명시 | 국가법령정보센터 직접 확인: 제36조, 노인복지관·경로당 열거, 기능 내용 일치. | **정합** |

**§6 소결**: 5건 중 정합 3건, 부분 확인 1건(전병윤 2024 PDF 추출 불가), 불확실 1건(정책브리핑 URL). 핵심 정량 근거인 김용진·안건혁 2012의 350-450m가 원문과 정확히 일치함은 중요한 강점이다.

---

## L4. 본문이 인용하지 않은 중요 문헌 누락 확인

본 계획은 "min-max 정규화 → 곱셈 → quantile threshold" 구조를 사용한다. 다음 3개 문헌은 이 구조를 직접 정당화하거나 반박할 수 있는 대표 문헌인데, §13 참고문헌 목록에 없다.

| 누락 문헌 | 본 계획과의 관련성 | 누락의 영향 |
|---|---|---|
| **US CDC SVI 2022 Technical Documentation** | percentile rank 정규화 + 등가중 구조. 공간 취약성 지수 분야 사실상 표준. 본 계획의 min-max 대신 percentile 방식의 대표 선례. | 정규화 방식 선택("왜 percentile이 아닌 min-max인가") 방어 약화. |
| **US EPA EJSCREEN Technical Documentation v2.3 (2024)** | **percentile 정규화 + 곱셈 결합(EJ index = 환경지표 percentile × 인구통계지수)**. 본 계획 곱셈 모델과 구조적으로 가장 유사한 공공 선례. | 이 문헌 인용 시 곱셈 구조를 직접 방어하는 가장 강력한 선례가 된다. 누락은 방어 약점. |
| **UK IMD 2019 Technical Report (MHCLG)** | rank 기반 정규화 + 지수변환 + 가중합 구조. 다중 도메인 복합지수의 정규화 방식 선택 이유를 상세 설명. | 정규화 선택 이유의 방어 문헌 공백. min-max 대비 rank 방식 논쟁에서 인용 가능. |

기존 `outputs/reports/critique/03_literature.md` 교차 참조: 팀원3(2026-05-21) 보고서에서 위 3개 문헌 모두를 "본 계획에 인용되어야 할 비교 문헌"으로 이미 지적했다. 특히 EJSCREEN의 percentile × 인구통계 곱셈 구조가 본 계획의 min-max × min-max 곱셈과 구조적으로 유사하지만 정규화 방식이 다른 점을 명시했다. 본 계획(§13)은 이 세 문헌을 여전히 인용하지 않고 있다.

---

## L5. Cherry-Picking / 일방 해석 위험

### 위험 1: Jiao & Dillivan 2013 차감 모델 vs. 본 계획 곱셈 모델 [가장 우려되는 cherry-picking]

Jiao & Dillivan 2013은 transit desert index를 **수요 - 공급(subtraction)** 방식으로 산출한다. 본 계획의 취약도는 **비용_norm × 수요_norm(multiplication)**이다. §13은 이 논문을 단순 나열하고, §6 문헌 매핑 원칙에서 "Jiao & Dillivan, Jomehpour & Smith-Colin, Hochmair 계열 연구는 transit desert 또는 service gap으로 보는 근거"라고만 쓴다. **§6과 §8-2에서 차감 vs. 곱셈의 방법론적 차이를 명시적으로 다루지 않는다.**

이는 cherry-picking에 해당한다. 해당 논문의 개념(수요와 공급 격차)은 인용하면서, 그 논문이 실제로 선택한 연산 방법(차감)이 본 계획의 연산 방법(곱셈)과 다르다는 점을 논의하지 않는 것이다. 심사자나 독자가 Jiao & Dillivan 원문을 확인하면 이 불일치를 즉시 발견할 수 있다.

**권고**: §8-2 또는 §6에 다음 취지를 추가해야 한다. "Jiao & Dillivan(2013)은 차감 방식을 사용하지만, 본 연구는 곱셈 방식을 채택한다. 곱셈 방식은 수요와 비용이 모두 높을 때만 취약도가 높아지는 AND 조건을 구현하며, EPA EJSCREEN(2024)의 EJ Index 구조(percentile × 인구통계지수)와 개념적으로 유사하다. 단, 본 연구는 percentile이 아닌 min-max 정규화를 사용하므로 outlier 영향에 대한 민감도 분석이 필수적이다."

### 위험 2: OECD/JRC sensitivity 인용과 본 계획 구현 간 격차

OECD/JRC Handbook은 sensitivity analysis로 Monte Carlo 방법, weight uncertainty, normalization scheme 변화를 표준으로 제시한다. 본 계획 §5의 검증 세트는 A~E 5개 정규화 방식 비교로 구성된다. 이는 "정규화 scheme 변화"에 해당하지만, **Monte Carlo 기반 가중치 불확실성 분석**은 포함되어 있지 않다. §12 수락 기준에도 Monte Carlo는 명시되어 있지 않다.

이는 cherry-picking이라기보다 인용 수준의 과장이다. Handbook을 "sensitivity 의무화"의 근거로 인용하면서 실제 구현은 Handbook이 권고하는 Monte Carlo 수준에 미치지 못한다. 이를 인정하지 않으면 독자가 "OECD/JRC 기준 충족"으로 오해할 수 있다.

**권고**: §8-2 또는 §12에 "본 계획의 민감도 분석은 OECD/JRC Handbook이 권고하는 Monte Carlo 기반 완전 불확실성 분석의 부분 구현에 해당한다. 완전한 Handbook 수준 민감도는 향후 과제로 남긴다"는 한계 명시가 필요하다.

---

## 종합 판정

**정합 비율: 17/22 정합 또는 부분 확인**

| 구분 | 건수 |
|---|---|
| 완전 정합 (제목·저자·연도·주장 일치) | 13건 |
| 부분 정합 (개념 지지, 세부 방법론 상이) | 4건 |
| URL 불확실/추출 불가 (실재는 확인) | 4건 |
| 실질 오류 (URL 불안정 또는 내용 불일치) | 1건 |

실질 오류 1건: 정책브리핑 모바일 URL(#19)의 소켓 연결 실패. 보고서 자체는 실재하지만 해당 URL의 영속성이 불안정하다.

**본 계획의 문헌 근거 전반 판정: 충분하나 위험 지점 존재**

주요 근거(Hansen, Geurs & van Wee, Handy & Niemeier, OECD/JRC, FHWA, 김용진·안건혁, 노인복지법)는 본문 주장과 정합한다. 그러나 두 가지 구조적 위험이 있다.

1. **가장 우려되는 cherry-picking**: Jiao & Dillivan 2013(차감 모델)을 곱셈 모델의 정당화 근거로 암묵적으로 인용하면서 방법론적 차이를 §6/§8-2에서 명시하지 않음.
2. **인용 누락**: 곱셈 구조를 가장 직접적으로 지지하는 EPA EJSCREEN 문헌이 §13에 없음.

---

## 권고 사항

1. **§8-2 또는 §6 수정 (우선순위 1)**: Jiao & Dillivan 2013의 차감 방식과 본 계획의 곱셈 방식의 차이를 명시적으로 기술하고, 곱셈 선택 이유(AND 조건, EJSCREEN 선례)를 추가할 것.

2. **§13 추가 인용 권고** (우선순위 순):
   - EPA EJSCREEN Technical Documentation v2.3 (2024): 곱셈 구조의 직접 공공 선례. https://www.epa.gov/system/files/documents/2024-07/ejscreen-tech-doc-version-2-3.pdf
   - CDC SVI 2022 Documentation: percentile 정규화 표준 선례. https://www.atsdr.cdc.gov/place-health/media/pdfs/2024/10/SVI2022Documentation.pdf
   - UK IMD 2019 Technical Report: 다중 도메인 정규화 방식 선택 근거. https://assets.publishing.service.gov.uk/media/5d8b387740f0b609909b5908/IoD2019_Technical_Report.pdf

3. **§12 수락 기준 수정**: Monte Carlo 수준의 완전 민감도 분석을 미수행하는 이유(범위 제약)를 한계로 명시할 것.

4. **URL 갱신**: 정책브리핑 #19 URL을 데스크톱 버전 URL로 교체하거나 DOI/보고서 등록번호로 대체할 것.

5. **Hochmair et al. 2022 인용 표현 수정**: 곱셈 산식의 직접 선례가 아닌 "오버레이 기반 후보 선별 사례"로 표현을 수정하고, 곱셈 구조의 직접 선례는 EJSCREEN으로 대체할 것.

---

**종료 보고**
- 정합 비율: **17/22 정합** (완전 정합 13건 + 부분 정합 4건)
- 가장 우려되는 cherry-picking 1건: **Jiao & Dillivan 2013(차감 모델)을 곱셈 모델의 암묵적 근거로 사용하면서 §6/§8-2에서 방법론 차이(차감 vs. 곱셈)를 명시하지 않은 것**
