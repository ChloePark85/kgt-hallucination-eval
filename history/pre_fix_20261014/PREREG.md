# 사전 등록 (실험 전 고정 사항)

작성: 2026-10-13. 문항 확정 후, 본 실험 시작 전에 아래 체크리스트를 채우고 날짜를 적는다.
이 문서와 `code/`, `seeds/`, `data/items.jsonl`, `data/tool_schemas.json`의 해시를 함께 기록해 실험 중 바뀌지 않았음을 보인다.

## 연구문제

- RQ1. 한국 고유 사실 질의에서 로컬 오픈 모델 단독 응답의 정답률·환각률·기권률은 어떠한가?
- RQ2. 공공데이터 검증 도구(KGT)를 쓰면 정답률과 환각률이 얼마나 달라지는가?
- RQ3. 효과는 영역(corp, biz, apt, juso, law)과 정보 성격(changes, stable)에 따라 어떻게 다른가?
- RQ4. 도구가 있어도 생기는 실패는 어떤 유형인가? (no_tool_call, tool_error, misread, retrieval_miss)

## 설계

- 문항: 5영역 × 40 = 200. 시드와 생성 규칙은 `seeds/`, `code/build_items.py`
- 조건: C0 모델 단독 / C2 KGT 도구 6종. 두 조건의 시스템 지시문은 도구 안내 한 문장만 다르다.
- 모델: Ollama 로컬 모델 3종 (확정 태그와 digest는 `results/runs/*/model_info.json`)
- 반복: 조건마다 3회. temperature 0.7, seed는 문항 ID와 회차로 결정, num_ctx 16384, think=false(지원 모델)
- 도구 결과: 목록은 앞 20개만 남기고 잘린 개수를 표시, 문자열 500자·전체 16,000자 상한
- 도구 호출은 한 문항당 최대 8라운드

## 채점 (`code/score.py`, 사람 개입 없음)

- 마지막 줄 JSON `{"answer", "status"}`를 읽는다. JSON이 없으면 unparsed(본문 끝에 모른다는 표현이 있으면 abstain).
- status가 unknown이거나 답이 비었거나 모른다는 표현이면 abstain.
- 답했지만 요구 형식으로 읽을 수 없으면 incorrect(format_error 표시).
- 유형별 판정
  - date: 연월일 8자리 일치
  - int: 정수 일치
  - postal: 5자리 일치
  - biz_status: 계속/휴업/폐업/미등록 범주 일치
  - person_names: 정답의 모든 이름이 답에 포함
  - ministry: 정답의 모든 부처가 답에 포함
  - road_address: 시군구와 '도로명+건물번호'가 답에 포함
- 환각 = incorrect.

## 분석 (`code/analyze.py`)

- 주 분석: 모델별 C0 대 C2 정답률 차이, McNemar 정확 검정(같은 문항·같은 회차끼리 짝)
- 보조 분석: 영역별·정보 성격별 비교, C2 실패 유형 빈도, 소요 시간·토큰
- 실험 뒤 `--recheck`로 정답이 바뀐 문항은 주 분석에서 제외하고 따로 보고한다.

## 이해상충

저자는 KGT의 개발·운영자다. 위 규칙을 실험 전에 고정하고, 코드·문항·원본 응답을 공개해 재현할 수 있게 한다.

## 확정 체크리스트

- [ ] review_queue.csv 확인 완료 (날짜: )
- [ ] 문항 200개 확정 (날짜: )
- [ ] 모델 태그·digest 기록 (날짜: )
- [ ] 해시 기록 (`shasum -a 256 code/*.py seeds/*.json data/items.jsonl data/tool_schemas.json > PREREG.sha256`)
