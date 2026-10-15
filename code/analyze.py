"""채점 결과 요약: 표(CSV)와 results/summary.md.

- 모델×조건 정답률·환각률·기권률 (정답률 95% Wilson 신뢰구간)
- 영역별, 정보 성격(변하는 정보/고정 정보)별 비교
- 모델별 C0 대 C2 McNemar 정확 검정 (같은 문항·같은 반복 회차끼리 짝지음)
- C2 실패 유형, 평균 소요 시간·토큰·도구 호출 수
"""
import csv
import math
from collections import Counter, defaultdict

from common import RESULTS, read_jsonl

OUTCOMES = ["correct", "incorrect", "abstain", "unparsed", "error"]


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def table(rows, keys):
    g = defaultdict(Counter)
    for r in rows:
        g[tuple(r[k] for k in keys)][r["outcome"]] += 1
    out = []
    for key in sorted(g):
        c = g[key]
        n = sum(c.values())
        lo, hi = wilson(c["correct"], n)
        out.append({**dict(zip(keys, key)), "n": n,
                    **{f"{o}_pct": round(100 * c[o] / n, 1) for o in OUTCOMES},
                    "correct_ci95": f"{100*lo:.1f}–{100*hi:.1f}"})
    return out


def write_csv(name, rows):
    if not rows:
        return
    with (RESULTS / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def md(rows, cols):
    if not rows:
        return "(자료 없음)\n"
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    return head + "".join("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |\n" for r in rows)


def main():
    rows = read_jsonl(RESULTS / "scored.jsonl")
    if not rows:
        raise SystemExit("results/scored.jsonl 이 없습니다. 먼저 score.py를 실행하세요.")
    t1 = table(rows, ["model", "condition"])
    t2 = table(rows, ["domain", "condition"])
    t3 = table(rows, ["model", "domain", "condition"])
    t4 = table(rows, ["volatility", "condition"])
    tests = []
    by = defaultdict(dict)
    for r in rows:
        by[(r["model"], r["id"], r["run"])][r["condition"]] = r["outcome"] == "correct"
    for model in sorted({r["model"] for r in rows}):
        b = c = n = 0
        for (m, _, _), v in by.items():
            if m != model or "C0" not in v or "C2" not in v:
                continue
            n += 1
            b += v["C0"] and not v["C2"]
            c += v["C2"] and not v["C0"]
        tests.append({"model": model, "pairs": n, "C0_only_correct": b, "C2_only_correct": c,
                      "mcnemar_p": f"{mcnemar_exact(b, c):.2g}"})
    fails = Counter((r["model"], r["failure"]) for r in rows if r["condition"] == "C2" and r["failure"])
    t5 = [{"model": m, "failure": f, "count": k} for (m, f), k in sorted(fails.items())]
    eff = defaultdict(list)
    for r in rows:
        eff[(r["model"], r["condition"])].append(r)
    t6 = []
    for (m, cnd), rs in sorted(eff.items()):
        avg = lambda k: round(sum((x.get(k) or 0) for x in rs) / len(rs), 1)
        t6.append({"model": m, "condition": cnd, "n": len(rs), "avg_seconds": avg("seconds"),
                   "avg_tokens_in": avg("tokens_in"), "avg_tokens_out": avg("tokens_out"), "avg_tool_calls": avg("n_tool_calls")})
    for name, t in [("t1_model_condition.csv", t1), ("t2_domain_condition.csv", t2), ("t3_model_domain_condition.csv", t3),
                    ("t4_volatility_condition.csv", t4), ("t5_c2_failures.csv", t5), ("t6_efficiency.csv", t6),
                    ("t7_mcnemar.csv", tests)]:
        write_csv(name, t)
    cols = ["n", "correct_pct", "correct_ci95", "incorrect_pct", "abstain_pct", "unparsed_pct", "error_pct"]
    text = "# 결과 요약 (자동 생성)\n\n환각 = 답했으나 틀린 응답(incorrect).\n\n"
    text += "## 모델 × 조건\n\n" + md(t1, ["model", "condition"] + cols)
    text += "\n## 영역 × 조건 (모델 합산)\n\n" + md(t2, ["domain", "condition"] + cols)
    text += "\n## 정보 성격 × 조건\n\n" + md(t4, ["volatility", "condition"] + cols)
    text += "\n## C0 대 C2 McNemar 정확 검정\n\n" + md(tests, ["model", "pairs", "C0_only_correct", "C2_only_correct", "mcnemar_p"])
    text += "\n## C2 실패 유형\n\n" + md(t5, ["model", "failure", "count"])
    text += "\n## 효율\n\n" + md(t6, ["model", "condition", "n", "avg_seconds", "avg_tokens_in", "avg_tokens_out", "avg_tool_calls"])
    (RESULTS / "summary.md").write_text(text, encoding="utf-8")
    print(f"요약 → {RESULTS / 'summary.md'}")


if __name__ == "__main__":
    main()
