# 로또 6/45 번호 추천 프로젝트

1회차부터 최신 회차까지 당첨번호를 수집하고, 다양한 패턴으로 통계를 내고
번호를 추천하는 프로그램입니다. (최종 목표: 무료 안드로이드 앱 + 광고 수익)

> ⚠️ **중요**: 로또는 매 회차 완전한 무작위 추첨입니다. 어떤 통계·패턴도 실제
> 당첨 확률을 높이지 못합니다. 이 프로그램의 추천은 **재미/참고용**이며, 앱에도
> 반드시 이 안내를 표시해야 합니다. ("확률을 높여준다"는 문구는 과대광고로
> 법적 문제가 될 수 있습니다.)

## 폴더 구조

```
lotto_project/
├─ requirements.txt          필요한 라이브러리 목록
├─ collector/
│   └─ collect_lotto.py       당첨번호 수집기 (동행복권 → DB/JSON)
├─ analysis/
│   ├─ analyze.py             패턴 통계 리포트 → data/stats.json
│   ├─ recommend.py           패턴별 번호 추천
│   └─ evaluate.py            예측 기록·채점·성공률 + 백테스트
├─ saju/
│   ├─ saju_core.py           사주팔자(년/월/일/시주) 계산 엔진
│   ├─ solar_terms.py         절기(태양황경) 정밀 계산
│   ├─ lunar.py               음력↔양력 변환
│   └─ recommend_saju.py      명리학(사주) 기반 번호 추천
├─ web/                        ⭐ 웹 서비스
│   ├─ app.py                 Flask 서버 (모든 기능을 웹으로)
│   ├─ templates/             화면(HTML)
│   └─ static/style.css       디자인
└─ data/                       (자동 생성)
    ├─ lotto.db                SQLite DB (회차 + 당첨판매점)
    ├─ lotto.json              전체 회차 JSON (앱에서 사용)
    └─ stats.json              통계 결과 JSON (앱에서 사용)
```

## 처음 준비 (한 번만)

```powershell
pip install -r requirements.txt
```

## ⭐⭐ 가장 쉬운 사용법 — 파일 더블클릭

`web_static/lotto.html` 파일을 **더블클릭**하면 브라우저에서 바로 열립니다.
(파이썬 서버 불필요. 모든 기능이 파일 하나에 들어있는 자기포함 HTML.)

## 🔄 데이터 업데이트 (매주 새 회차 반영)

- **원클릭**: `update.bat` **더블클릭** → 수집 + `lotto.html` 재생성까지 한 번에
- **자동**: 윈도우 작업 스케줄러 `LottoWeeklyUpdate` 가 **매주 토요일 21:30** 자동 실행
  (추첨 직후 번호 갱신. PC가 꺼져 있었으면 다음 부팅 때 실행. 로그: `data/update_log.txt`)
  - 자동실행 끄기:  `Unregister-ScheduledTask -TaskName LottoWeeklyUpdate -Confirm:$false`
  - 지금 바로 실행: `Start-ScheduledTask -TaskName LottoWeeklyUpdate`

> 참고: 1등 판매점 데이터는 추첨 며칠 뒤 확정되므로, 새 회차 판매점은 다음 주 갱신 때 채워집니다.
> 완전 자동(PC와 무관)을 원하면 웹 배포 후 GitHub Actions 주간 크론으로 전환하세요.

수동으로 개별 실행:
```powershell
python collector/collect_lotto.py   # 회차 수집
python web_static/build_data.py     # DB -> data.json
python web_static/build_html.py     # data.json + 템플릿 -> lotto.html
```

## ⭐ 웹 서비스 실행 (Flask — 동적 버전)

```powershell
python collector/collect_lotto.py      # 1) 회차 데이터 수집
python collector/collect_stores.py     # 2) 당첨 판매점 수집 (10~15분)
python web/app.py                       # 3) 웹 서버 실행
```
실행 후 브라우저에서 **http://127.0.0.1:5000** 접속. 페이지 구성:
- **홈** 최신 당첨번호·통계 요약
- **통계** 빈도·미출현·홀짝·구간·궁합수
- **패턴추천** 5가지 전략 번호 (버튼으로 여러 세트)
- **사주추천** 생년월일시(양력/음력·시간 선택) → 명리학 번호
- **당첨판매점** 명당 랭킹 + 회차별 1·2등 배출점 조회
- **예측성공률** 전략별 백테스트

> 아래는 각 기능을 터미널에서 개별 실행하는 방법입니다(개발/디버깅용).

## 사용법

### 1) 당첨번호 수집 / 업데이트
```powershell
python collector/collect_lotto.py
```
- 처음 실행하면 1회차부터 전체를 받습니다.
- 다음부터는 **새로 추가된 회차만** 이어받습니다(빠름).
- 매주 토요일 추첨 후(밤) 다시 실행하면 최신 회차가 추가됩니다.

### 2) 통계 리포트 보기
```powershell
python analysis/analyze.py
```
번호별 빈도, 미출현 기간, 홀짝/구간 분포, 연속번호, 합계, 궁합수 등을
화면에 출력하고 `data/stats.json` 으로 저장합니다.

### 3) 번호 추천 받기
```powershell
python analysis/recommend.py              # 전략별 1세트씩
python analysis/recommend.py balanced 5   # balanced 전략 5세트
```
전략: `hot`(핫넘버) · `cold`(미출현) · `balanced`(균형) ·
`companion`(궁합수) · `random`(무작위)

### 4) 예측 성공률 보기
```powershell
python analysis/evaluate.py predict          # 다음 회차 예측을 전략별로 저장
python analysis/evaluate.py score            # 추첨 끝난 예측 채점 + 전략별 누적 성공률
python analysis/evaluate.py backtest 300     # 최근 300회로 전략 성능 즉시 검증
```
- `predict` → 다음 회차 예측을 DB에 기록해 둡니다.
- 토요일 추첨 후 `collect_lotto.py` 로 최신 회차를 받은 뒤 `score` 를 실행하면
  자동 채점되고 전략별 누적 성공률(평균 맞춘 개수, 등수 분포)이 나옵니다.
- `backtest` 는 과거 데이터로 "그때 그 전략을 썼다면?"을 계산해 **몇 주 안 기다리고
  바로** 성능을 보여줍니다. (참고: 모든 전략이 무작위와 비슷하게 나오는 게 정상입니다.)

### 5) 명리학(사주) 기반 추천
```powershell
python saju/recommend_saju.py 1990-05-15 07:30        # 생년월일 + 태어난 시각
python saju/recommend_saju.py 1990-05-15              # 시간 모르면 생략 가능
python saju/recommend_saju.py 1990-05-15 07:30 2026-07-11   # 추첨일 지정
```
- 생년월일시 → 사주팔자(년/월/일/시주) 계산 → 오행 분포 분석.
- 부족한 오행을 보완하고 **추첨일의 일진(그날 기운)**을 반영해 번호를 뽑습니다.
- 같은 사람·같은 추첨일이면 **항상 같은 번호**가 나옵니다(사주는 정해진 기운).
- ⚠️ 입력은 **양력(솔라)** 기준입니다. 음력 생일만 아는 사용자를 위해 앱에서는
  음력→양력 변환 입력을 넣어야 합니다. (절기 경계 태생은 만세력과 하루 차이 가능)

## 데이터 출처 참고 (개발자용)

동행복권이 2026년 사이트를 개편하면서 예전 `common.do?method=getLottoNumber`
JSON API가 폐기되었습니다. 현재는 결과 페이지(`/lt645/result`)가 내부적으로
호출하는 아래 엔드포인트를 사용합니다.

```
GET https://www.dhlottery.co.kr/lt645/selectPstLt645InfoNew.do
    ?srchDir=center|older|latest
    &srchLtEpsd=<회차>          (center)
    &srchCursorLtEpsd=<커서>    (older/latest, 10회차씩 반환)
```
사이트 구조가 또 바뀌면 `collector/collect_lotto.py` 의 이 부분을 수정해야 합니다.

## 진행 상황

- [x] 1~최신 회차 당첨번호 수집
- [x] 패턴 통계 분석
- [x] 패턴별 번호 추천 (5전략)
- [x] 예측 성공률 · 백테스트
- [x] 명리학(사주) 기반 번호 추천
- [x] 정밀 절기(태양황경) + 음력→양력 변환
- [x] 당첨 판매점(1등/2등 배출점) 데이터 수집 + 명당 랭킹
- [x] 웹 서비스(Flask) — 모든 기능 통합
- [ ] 실서버 배포 (외부 접속 가능하게)
- [ ] 안드로이드 앱(Flutter) + 광고(AdMob)
- [ ] 데이터 자동 업데이트(매주 토요일) 파이프라인
- [ ] 광고/플레이스토어 정책 검증
