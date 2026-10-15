# KGT Hallucination Evaluation

Code, questions, gold-answer snapshots, raw model responses and scoring results for the study
**"Selective Abstention of Local Large Language Models and the Effect of a Public-Data Verification Tool on Korea-Specific Factual Questions"**
(한국 고유 사실 질의에서 로컬 대규모 언어모델의 선택적 기권과 공공데이터 검증 도구의 효과).

The study compares three locally run open-weight models with and without the
Korea Ground-Truth (KGT) verification tools on 200 Korea-specific factual questions
(5 domains × 40), three runs each (3,600 responses). All scoring is rule-based.

| Model (Ollama tag) | C0 no tool: correct / incorrect | C2 with KGT: correct / incorrect |
|---|---|---|
| qwen3.8:27b | 8.7% / 46.2% | 95.7% / 1.8% |
| gemma4:26b | 11.7% / 47.7% | 95.7% / 2.7% |
| gemma4:12b | 8.7% / 50.5% | 92.0% / 3.5% |

## 구성

| 경로 | 내용 |
|---|---|
| `PREREG.md` | 사전 등록 문서와 수정 기록(실험 전·중·후 변경 사항 전부) |
| `PREREG.sha256`, `PREREG_v1_20261014_1131.sha256` | 고정 시점의 파일 해시(수정 후 / 수정 전) |
| `RUN.md` | 실행 순서 |
| `code/` | 문항 생성(`build_items.py`), 실행(`run_experiment.py`), 채점(`score.py`), 분석(`analyze.py`), 사후·민감도 분석(`analyze_extra.py`), 기권 분석(`analyze_abstention.py`) |
| `seeds/` | 영역별 시드 목록 |
| `data/items.jsonl` | 200문항과 정답 |
| `data/snapshots/` | 정답을 만들 때 받은 공식 API 원본 응답 |
| `data/snapshots_goldfix/` | 실험 중 정답을 고친 문항의 근거 응답 |
| `data/snapshots_recheck/`, `data/recheck.csv` | 실험 후 정답 재조회 결과(바뀐 문항 없음) |
| `data/tool_schemas.json` | 실험에 쓴 KGT 도구 정의 |
| `results/runs/` | 모델·조건·회차별 원본 응답과 도구 호출 기록 |
| `results/scored.jsonl`, `results/t*.csv`, `results/summary.md` | 사전 등록 채점·분석 결과 |
| `results/extra.*` | 사후 민감도 분석(엄격 채점, 수정 문항 제외, 문항 단위 부트스트랩) |
| `history/pre_fix_20261014/` | 본 실험 중 수정하기 전의 문항·채점 코드 (PREREG.md의 `_to_delete/pre_fix_20261014/`) |

## 재현

`RUN.md`를 따른다. 파이썬 표준 라이브러리만 사용한다. 실행에는 Ollama와 KGT API 키가 필요하지만,
채점과 분석은 이 저장소의 파일만으로 다시 할 수 있다.

```bash
python3 code/score.py && python3 code/analyze.py && python3 code/analyze_extra.py && python3 code/analyze_abstention.py
```

## 비공개 처리

법제처 국가법령정보 API의 인증값(OC)이 KGT 응답의 상세 링크에 들어 있어, 모든 파일에서 `OC=REDACTED`로 바꾸었다.
이 값은 해시 대상 파일(`code/`, `seeds/`, `data/items.jsonl`, `data/tool_schemas.json`)에는 없으므로 `sha256sum -c PREREG.sha256`은 그대로 통과한다.

## 데이터 출처

국세청 사업자등록정보(공공데이터포털), 행정안전부 도로명주소, 금융감독원 OPEN DART, 국토교통부 아파트 매매 실거래가(공공데이터포털),
법제처 국가법령정보. 원천 데이터의 권리와 이용 조건은 각 기관을 따른다. 사업자 상태 문항은 DART에 등록된 법인만 사용했으며 개인사업자는 포함하지 않았다.

## 이해상충

연구자는 KGT의 개발·운영자이다. 이를 고려해 설계와 채점 규칙을 실험 전에 고정하고, 모든 변경을 `PREREG.md`에 기록했으며, 원본 응답 전체를 공개한다.

## 라이선스

코드는 MIT License(`LICENSE`), 문항·응답·결과 데이터는 CC BY 4.0을 따른다. 원천 공공데이터는 위 각 기관의 이용 조건을 따른다.
