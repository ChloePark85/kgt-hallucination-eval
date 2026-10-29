# 심사의견 대응 분석 (사후)

## 1. 수정 전 채점과 최종 채점의 정답률(%)

| model | cond | 최종 | 수정 전 | 결과가 바뀐 응답 |
|---|---|---|---|---|
| gemma4:12b | C0 | 8.7 | 8.2 | 3 |
| gemma4:12b | C2 | 92.0 | 87.2 | 35 |
| gemma4:26b | C0 | 11.7 | 10.8 | 7 |
| gemma4:26b | C2 | 95.7 | 91.3 | 32 |
| qwen3.8:27b | C0 | 8.7 | 8.8 | 1 |
| qwen3.8:27b | C2 | 95.7 | 90.8 | 31 |

결과가 바뀐 문항: corp-02(9), corp-10(9), corp-12(5), corp-20(9), corp-32(9), juso-09(15), juso-15(9), juso-25(2), juso-28(8), juso-30(6), juso-31(9), juso-32(5), juso-33(5), juso-34(9)

## 2. C2 실패 유형 × 영역

| failure | corp | biz | apt | juso | law | 합계 |
|---|---|---|---|---|---|---|
| misread | 8 | 0 | 1 | 26 | 0 | 35 |
| no_tool_call | 0 | 0 | 0 | 0 | 2 | 2 |
| retrieval_miss | 26 | 0 | 1 | 22 | 0 | 49 |
| tool_error | 0 | 14 | 0 | 0 | 0 | 14 |

## 3. 실패 유형별 최종 응답(모델별)

| model | failure | outcome | n |
|---|---|---|---|
| gemma4:12b | misread | incorrect | 9 |
| gemma4:12b | no_tool_call | error | 2 |
| gemma4:12b | retrieval_miss | abstain | 11 |
| gemma4:12b | retrieval_miss | incorrect | 12 |
| gemma4:12b | retrieval_miss | unparsed | 5 |
| gemma4:12b | tool_error | abstain | 9 |
| gemma4:26b | misread | incorrect | 9 |
| gemma4:26b | misread | unparsed | 2 |
| gemma4:26b | retrieval_miss | incorrect | 7 |
| gemma4:26b | retrieval_miss | unparsed | 3 |
| gemma4:26b | tool_error | abstain | 5 |
| qwen3.8:27b | misread | abstain | 1 |
| qwen3.8:27b | misread | incorrect | 9 |
| qwen3.8:27b | misread | unparsed | 5 |
| qwen3.8:27b | retrieval_miss | abstain | 1 |
| qwen3.8:27b | retrieval_miss | incorrect | 2 |
| qwen3.8:27b | retrieval_miss | unparsed | 8 |
