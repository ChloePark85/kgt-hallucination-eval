# 결과 요약 (자동 생성)

환각 = 답했으나 틀린 응답(incorrect).

## 모델 × 조건

| model | condition | n | correct_pct | correct_ci95 | incorrect_pct | abstain_pct | unparsed_pct | error_pct |
|---|---|---|---|---|---|---|---|---|
| gemma4:12b | C0 | 600 | 8.7 | 6.7–11.2 | 50.5 | 40.5 | 0.3 | 0.0 |
| gemma4:12b | C2 | 600 | 92.0 | 89.6–93.9 | 3.5 | 3.3 | 0.8 | 0.3 |
| gemma4:26b | C0 | 600 | 11.7 | 9.3–14.5 | 47.7 | 40.7 | 0.0 | 0.0 |
| gemma4:26b | C2 | 600 | 95.7 | 93.7–97.0 | 2.7 | 0.8 | 0.8 | 0.0 |
| qwen3.8:27b | C0 | 600 | 8.7 | 6.7–11.2 | 46.2 | 45.0 | 0.2 | 0.0 |
| qwen3.8:27b | C2 | 600 | 95.7 | 93.7–97.0 | 1.8 | 0.3 | 2.2 | 0.0 |

## 영역 × 조건 (모델 합산)

| domain | condition | n | correct_pct | correct_ci95 | incorrect_pct | abstain_pct | unparsed_pct | error_pct |
|---|---|---|---|---|---|---|---|---|
| apt | C0 | 360 | 0.0 | 0.0–1.1 | 0.0 | 100.0 | 0.0 | 0.0 |
| apt | C2 | 360 | 99.4 | 98.0–99.8 | 0.0 | 0.3 | 0.3 | 0.0 |
| biz | C0 | 360 | 0.0 | 0.0–1.1 | 0.0 | 100.0 | 0.0 | 0.0 |
| biz | C2 | 360 | 96.1 | 93.6–97.7 | 0.0 | 3.9 | 0.0 | 0.0 |
| corp | C0 | 360 | 3.3 | 1.9–5.7 | 88.3 | 8.3 | 0.0 | 0.0 |
| corp | C2 | 360 | 90.6 | 87.1–93.2 | 3.3 | 2.8 | 3.3 | 0.0 |
| juso | C0 | 360 | 11.7 | 8.7–15.4 | 86.4 | 1.4 | 0.6 | 0.0 |
| juso | C2 | 360 | 86.7 | 82.8–89.8 | 10.0 | 0.6 | 2.8 | 0.0 |
| law | C0 | 360 | 33.3 | 28.7–38.4 | 65.8 | 0.6 | 0.3 | 0.0 |
| law | C2 | 360 | 99.4 | 98.0–99.8 | 0.0 | 0.0 | 0.0 | 0.6 |

## 정보 성격 × 조건

| volatility | condition | n | correct_pct | correct_ci95 | incorrect_pct | abstain_pct | unparsed_pct | error_pct |
|---|---|---|---|---|---|---|---|---|
| changes | C0 | 1080 | 1.7 | 1.1–2.6 | 28.9 | 69.4 | 0.0 | 0.0 |
| changes | C2 | 1080 | 96.5 | 95.2–97.4 | 0.6 | 1.8 | 1.1 | 0.0 |
| stable | C0 | 720 | 21.7 | 18.8–24.8 | 76.9 | 1.0 | 0.4 | 0.0 |
| stable | C2 | 720 | 91.4 | 89.1–93.2 | 5.7 | 1.1 | 1.5 | 0.3 |

## C0 대 C2 McNemar 정확 검정

| model | pairs | C0_only_correct | C2_only_correct | mcnemar_p |
|---|---|---|---|---|
| gemma4:12b | 600 | 1 | 501 | 7.7e-149 |
| gemma4:26b | 600 | 3 | 507 | 1.3e-146 |
| qwen3.8:27b | 600 | 3 | 525 | 5.6e-152 |

## C2 실패 유형

| model | failure | count |
|---|---|---|
| gemma4:12b | misread | 9 |
| gemma4:12b | no_tool_call | 2 |
| gemma4:12b | retrieval_miss | 28 |
| gemma4:12b | tool_error | 9 |
| gemma4:26b | misread | 11 |
| gemma4:26b | retrieval_miss | 10 |
| gemma4:26b | tool_error | 5 |
| qwen3.8:27b | misread | 15 |
| qwen3.8:27b | retrieval_miss | 11 |

## 효율

| model | condition | n | avg_seconds | avg_tokens_in | avg_tokens_out | avg_tool_calls |
|---|---|---|---|---|---|---|
| gemma4:12b | C0 | 600 | 4.4 | 155.7 | 67.7 | 0.0 |
| gemma4:12b | C2 | 600 | 29.6 | 6381.4 | 95.0 | 1.7 |
| gemma4:26b | C0 | 600 | 3.8 | 155.7 | 72.8 | 0.0 |
| gemma4:26b | C2 | 600 | 14.8 | 6580.7 | 85.7 | 1.6 |
| qwen3.8:27b | C0 | 600 | 14.6 | 146.9 | 113.7 | 0.0 |
| qwen3.8:27b | C2 | 600 | 54.4 | 7195.4 | 173.6 | 1.9 |
