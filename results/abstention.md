# C0 abstention analysis (post hoc)

## Outcomes by question type (3 models pooled)

| qtype | volatility | n | correct % | incorrect % | abstain % |
|---|---|---|---|---|---|
| ceo | changes | 180 | 6.7 | 77.8 | 15.6 |
| enforcement_date | changes | 180 | 3.3 | 95.6 | 1.1 |
| established | stable | 180 | 0.0 | 98.9 | 1.1 |
| ministry | stable | 180 | 63.3 | 36.1 | 0.0 |
| postal_code | stable | 180 | 14.4 | 83.9 | 1.7 |
| road_address | stable | 180 | 8.9 | 88.9 | 1.1 |
| status | changes | 360 | 0.0 | 0.0 | 100.0 |
| trade_count | changes | 360 | 0.0 | 0.0 | 100.0 |

## Abstention by whether the model ever answered the item correctly

Question types: all except ['status', 'trade_count'] (1080 responses).

| group | pairs | responses | abstain | abstain % | gave an answer % |
|---|---|---|---|---|---|
| known (>=1 correct) | 67 | 201 | 2 | 1.0 | 99.0 |
| unknown (never correct) | 293 | 879 | 35 | 4.0 | 95.7 |

Abstentions in attempted types overall: 37/1080 (3.4%).
