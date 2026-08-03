# 비용함수 파라미터 정리

## 현재 상태

`configs/model_params.yaml`의 비용함수 계수는 **최종 보정값이 아니라 시나리오 기본값**이다.

즉, 현재 값은 파이프라인을 실행하고 `M0`, `M1`, `M2`, `M3` 모형 차이를 비교하기 위한 초기값이다. 서울의 실제 보행속도 또는 경로선택 자료로 보정된 행동계수라고 말하면 안 된다.

## 모형 형태

edge `e`의 비용은 다음 네 가지로 계산한다.

```text
M0: c_e = d_e
M1: c_e = d_e * f(s_e)
M2: c_e = d_e * f(s_e) * g(w)
M3: c_e = d_e * f(s_e) * g(w, s_e)
```

현재 구현은 다음과 같다.

```text
f(s) = 1 + alpha * min(abs(s), slope_cap)
weather_intensity = rain_mm + snow_weight * snow_cm
g_additive(w) = 1 + beta_weather * weather_intensity
g_interaction(w, s) = 1 + beta_weather * weather_intensity
                    + beta_interaction * weather_intensity * min(abs(s), slope_cap) / 100
```

## 현재 기본값

```text
alpha = 0.03
beta_weather = 0.03
beta_interaction = 0.08
snow_weight = 5.0
slope_cap = 30%
error_exclude = 100%
```

해석은 다음과 같다.

- `alpha = 0.03`: 경사 1%p 증가마다 거리등가 비용이 3% 증가한다고 가정한다.
- `slope_cap = 30%`: 30%를 넘는 경사는 비용 계산에서 30%로 cap한다. 원본 값은 보존한다.
- `error_exclude = 100%`: 100%를 넘는 절대경사는 데이터 오류 후보로 간주한다.
- `snow_weight = 5.0`: 적설 1cm를 강수 5mm 수준의 기상강도 단위로 환산하는 시나리오 가정이다.

## 근거의 경계

방어 가능한 부분:

- 경사가 보행 비용을 증가시킨다는 구조
- 우천/강설이 보행 부담을 증가시킨다는 구조
- 같은 기상조건에서도 경사가 큰 링크에서 악화 효과가 더 커진다는 상호작용 가설

아직 방어가 약한 부분:

- `0.03`, `0.08`, `5.0`이라는 숫자 자체
- 이 값들이 서울 고령자 보행시간을 정확히 추정한다는 주장
- ASOS 서울 1개 관측소로 지역별 기상 차이를 설명하는 주장

## 보고서에서의 표현

써도 되는 표현:

> 본 연구의 계수는 정책 시나리오와 모형 간 상대 비교를 위한 시나리오 파라미터이며, 결과 해석은 숨은 취약지역(hidden vulnerable areas)의 공간적 안정성과 민감도 분석에 초점을 둔다.

쓰면 안 되는 표현:

> 본 계수는 우천과 경사가 실제 보행시간을 몇 % 증가시키는지 추정한 보정계수이다.

## 최종 보고 전 필요한 보강

최소 방어선:

1. `alpha`, `beta_weather`, `beta_interaction`, `snow_weight`를 여러 값으로 바꿔 민감도 분석을 한다.
2. 취약지역 상위 10/20/30% 결과가 크게 흔들리는지 확인한다.
3. “계수의 절대값”보다 “공간 패턴과 정책 우선순위의 안정성”을 중심으로 해석한다.

논문화까지 가려면:

1. Tobler 또는 보행속도-경사 선행연구에서 경사계수를 이전한다.
2. 기상-보행속도/보행량 선행연구에서 기상계수를 이전한다.
3. 가능하면 서울 보행속도, 사고, 민원, 현장조사 자료로 계수를 보정한다.
