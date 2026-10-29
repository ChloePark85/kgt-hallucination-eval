"""사후 분석: EXAONE 3.5 32B, 도구 없는 조건(C0)만 (1차 심사 후 추가, PREREG 수정 기록 3).

사전 등록 결과(results/scored.jsonl)를 바꾸지 않도록 응답은 results/runs_posthoc/에 두고,
같은 채점 규칙(code/score.py의 classify)으로 따로 채점한다.
출력: results/exaone_scored.jsonl, results/exaone.md
"""
import collections
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
from analyze import wilson  # noqa: E402
from score import classify  # noqa: E402

RUNS = ROOT / "results" / "runs_posthoc" / "exaone3.5_32b" / "C0"
items = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "data" / "items.jsonl", encoding="utf-8")}
ALWAYS = {"status", "trade_count"}


def score_runs():
    out = []
    for f in sorted(RUNS.glob("run*.jsonl")):
        latest = {}
        for l in open(f, encoding="utf-8"):
            r = json.loads(l)
            latest[r["id"]] = r
        for r in latest.values():
            it = items[r["id"]]
            c = classify(it, r)
            out.append({"id": r["id"], "domain": r["domain"], "qtype": it["qtype"], "volatility": it["volatility"],
                        "model": r["model"], "condition": "C0", "run": r["run"], **c,
                        "tokens_in": r.get("tokens_in"), "tokens_out": r.get("tokens_out"), "seconds": r.get("seconds")})
    return out


def pct(n, d):
    return f"{100 * n / d:.1f}" if d else "-"


def block(rows):
    c = collections.Counter(r["outcome"] for r in rows)
    n = len(rows)
    lo, hi = wilson(c["correct"], n)
    att = c["correct"] + c["incorrect"]
    return c, n, f"{pct(c['correct'], n)} [{100*lo:.1f}–{100*hi:.1f}]", pct(c["incorrect"], att)


def main():
    ex = score_runs()
    (ROOT / "results" / "exaone_scored.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in ex), encoding="utf-8")
    base = [json.loads(l) for l in open(ROOT / "results" / "scored.jsonl", encoding="utf-8")]
    base_c0 = [r for r in base if r["condition"] == "C0"]
    L = ["# EXAONE 3.5 32B, C0 (사후 분석)", "", "## 1. 응답 분포 (%)", "",
         "| model | n | correct [95% CI] | incorrect | abstain | unparsed/error | 시도 중 오답 |", "|---|---|---|---|---|---|---|"]
    for m in ["exaone3.5:32b", "qwen3.8:27b", "gemma4:26b", "gemma4:12b"]:
        rows = ex if m.startswith("exaone") else [r for r in base_c0 if r["model"] == m]
        c, n, cc, att = block(rows)
        L.append(f"| {m} | {n} | {cc} | {pct(c['incorrect'], n)} | {pct(c['abstain'], n)} | {pct(c['unparsed'] + c['error'], n)} | {att} |")
    L += ["", "## 2. 문항 유형별 (EXAONE)", "", "| qtype | n | correct | incorrect | abstain |", "|---|---|---|---|---|"]
    byq = collections.defaultdict(list)
    for r in ex:
        byq[r["qtype"]].append(r)
    for q, rs in sorted(byq.items()):
        c = collections.Counter(r["outcome"] for r in rs)
        L.append(f"| {q} | {len(rs)} | {pct(c['correct'], len(rs))} | {pct(c['incorrect'], len(rs))} | {pct(c['abstain'], len(rs))} |")
    att = [r for r in ex if r["qtype"] not in ALWAYS]
    alw = [r for r in ex if r["qtype"] in ALWAYS]
    a_ab = sum(r["outcome"] == "abstain" for r in alw)
    t_ab = sum(r["outcome"] == "abstain" for r in att)
    L += ["", f"- 식별번호·월간 건수 2유형 기권: {a_ab}/{len(alw)} ({pct(a_ab, len(alw))}%)",
          f"- 나머지 6유형 기권: {t_ab}/{len(att)} ({pct(t_ab, len(att))}%)"]
    pairs = collections.defaultdict(list)
    for r in att:
        pairs[r["id"]].append(r)
    L += ["", "## 3. 정답을 한 번이라도 맞힌 문항 vs 한 번도 못 맞힌 문항 (6유형)", "",
          "| group | items | responses | abstain % | answered % |", "|---|---|---|---|---|"]
    for name, known in (("known", True), ("unknown", False)):
        grp = [rs for rs in pairs.values() if any(r["outcome"] == "correct" for r in rs) == known]
        resp = [r for rs in grp for r in rs]
        c = collections.Counter(r["outcome"] for r in resp)
        L.append(f"| {name} | {len(grp)} | {len(resp)} | {pct(c['abstain'], len(resp))} | {pct(c['correct'] + c['incorrect'], len(resp))} |")
    secs = [r["seconds"] for r in ex if r.get("seconds")]
    L += ["", f"- 응답 시간 중앙값 {statistics.median(secs):.1f}초, 평균 입력 토큰 {statistics.mean(r['tokens_in'] for r in ex if r.get('tokens_in')):.0f}"]
    (ROOT / "results" / "exaone.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
