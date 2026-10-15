# 맥미니 실행 방법

이 작업 공간에서는 공공데이터 API, KGT 서버, Ollama에 접속할 수 없어서 실제 실행은 맥미니 터미널에서 합니다.
코드는 파이썬 표준 라이브러리만 써서 따로 설치할 패키지가 없습니다.

## 0. 준비 (한 번만)

1. 이 `kgt-paper` 폴더를 통째로 맥미니에 복사합니다(AirDrop, 외장 드라이브, 비공개 git 저장소 중 편한 방법).
2. KGT 실험용 계정과 API 키를 만듭니다.
   - 이메일을 `...@example.com`으로 만들면 KGT 운영 지표(metrics_report)에서 자동으로 빠집니다.
   - 필요한 크레딧(추정): 문항 생성 약 1,300 + 실험 C2 약 3,000~5,000. 넉넉하게 8,000 정도 충전해 두세요.
3. 모델을 내려받습니다. 태그 이름은 `ollama.com`에서 확인한 뒤 맞게 바꾸세요.
   ```bash
   ollama pull qwen3.8:27b
   ollama pull gemma4:26b
   ollama pull gemma4:12b
   ollama list
   ```

## 1. 환경변수

```bash
cd ~/kgt-paper            # 복사한 위치
export KGT_API_KEY="kgt_live_..."      # 실험용 키
# 기본값: KGT_BASE=https://kr-groundtruth-mcp.vercel.app, OLLAMA_URL=http://localhost:11434
```

## 2. 문항과 정답 스냅샷 만들기 (약 10~20분)

```bash
python3 code/build_items.py
```

- 결과: `data/items.jsonl`(문항), `data/snapshots/`(공공데이터 원본 응답), `data/review_queue.csv`(확인 필요 목록)
- `review_queue.csv`의 항목을 확인하고, 이상한 시드는 `seeds/*.json`에서 고친 뒤 그 영역만 다시 만듭니다.
  ```bash
  python3 code/build_items.py --only corp
  ```
- 문항이 확정되면 `PREREG.md`의 체크리스트를 채우고 날짜를 적습니다. 그 뒤로는 문항과 채점 규칙을 바꾸지 않습니다.

## 3. 시험 실행 (모델마다 5문항, 1회)

```bash
python3 code/run_experiment.py --models gemma4:12b --conds C0,C2 --runs 1 --limit 5
python3 code/score.py && python3 code/analyze.py && cat results/summary.md
```

- 도구 호출이 되는지, 마지막 줄 JSON이 나오는지 확인합니다.
- 시험 실행 결과는 본 실험 전에 지웁니다: `results/runs/` 안의 해당 모델 폴더를 휴지통으로.

## 4. 본 실험 (3,600회, 하루~이틀)

```bash
caffeinate -i python3 code/run_experiment.py --models qwen3.8:27b,gemma4:26b,gemma4:12b --conds C0,C2 --runs 3 2>&1 | tee results/run.log
```

- `caffeinate -i`는 실행 중 맥이 잠들지 않게 합니다.
- 중간에 끊겨도 같은 명령을 다시 실행하면 남은 문항부터 이어서 돕니다.
- 크레딧이 떨어지면(402) 자동으로 멈춥니다. 충전 후 다시 실행하면 됩니다.

## 5. 채점·분석·정답 재확인

```bash
python3 code/score.py
python3 code/analyze.py
python3 code/build_items.py --recheck     # 실험 중 바뀐 정답 확인
```

- 결과: `results/summary.md`, `results/t1~t7_*.csv`, `data/recheck.csv`
- 끝나면 `results/`와 `data/` 폴더를 맥북의 `dev/kgt-paper`로 다시 복사해 주세요. 그다음 분석과 원고 작업을 이어 갑니다.
