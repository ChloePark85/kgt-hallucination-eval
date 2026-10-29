"""심사의견 대응 분석(사후). 사전 등록 코드는 바꾸지 않는다.

1) 수정 전 채점: history/pre_fix_20261014/의 채점 규칙(score_before_fix.py)과 정답(items_before_gold_fix.jsonl)으로
   3,600건을 다시 채점해 최종 결과와 비교한다.
2) C2 실패 유형 × 영역, 검색 실패 뒤 응답(기권·오답·판독 불가) 분포.

실행: python3 code/analyze_revision.py   → results/revision.md
"""
import collections
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def rate(rows, outcome):
    return 100 * sum(r["outcome"] == outcome for r in rows) / len(rows)


def prefix_scores():
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        for d in ("code", "data", "results"):
            shutil.copytree(ROOT / d, t / d)
        shutil.copy(ROOT / "history/pre_fix_20261014/score_before_fix.py", t / "code/score.py")
        shutil.copy(ROOT / "history/pre_fix_20261014/items_before_gold_fix.jsonl", t / "data/items.jsonl")
        subprocess.run([sys.executable, str(t / "code/score.py")], check=True, cwd=t, capture_output=True)
        return load(t / "results/scored.jsonl")


def main():
    post = load(RES / "scored.jsonl")
    pre = prefix_scores()
    key = lambda r: (r["model"], r["condition"], r["id"], r["run"])
    P = {key(r): r for r in pre}
    L = ["# 심사의견 대응 분석 (사후)", "", "## 1. 수정 전 채점과 최종 채점의 정답률(%)", "",
         "| model | cond | 최종 | 수정 전 | 결과가 바뀐 응답 |", "|---|---|---|---|---|"]
    for m in sorted({r["model"] for r in post}):
        for c in ("C0", "C2"):
            q = [r for r in post if r["model"] == m and r["condition"] == c]
            p = [P[key(r)] for r in q]
            ch = sum(P[key(r)]["outcome"] != r["outcome"] for r in q)
            L.append(f"| {m} | {c} | {rate(q, 'correct'):.1f} | {rate(p, 'correct'):.1f} | {ch} |")
    changed = collections.Counter(r["id"] for r in post if P[key(r)]["outcome"] != r["outcome"])
    L += ["", "결과가 바뀐 문항: " + ", ".join(f"{k}({v})" for k, v in sorted(changed.items())), ""]

    c2 = [r for r in post if r["condition"] == "C2" and r["outcome"] != "correct"]
    doms = ["corp", "biz", "apt", "juso", "law"]
    L += ["## 2. C2 실패 유형 × 영역", "", "| failure | " + " | ".join(doms) + " | 합계 |", "|---" * (len(doms) + 2) + "|"]
    t = collections.Counter((r["failure"], r["domain"]) for r in c2)
    for f in sorted({r["failure"] for r in c2}, key=str):
        L.append(f"| {f} | " + " | ".join(str(t[(f, d)]) for d in doms) + f" | {sum(t[(f, d)] for d in doms)} |")
    L += ["", "## 3. 실패 유형별 최종 응답(모델별)", "", "| model | failure | outcome | n |", "|---|---|---|---|"]
    for k, v in sorted(collections.Counter((r["model"], r["failure"], r["outcome"]) for r in c2).items(), key=str):
        L.append(f"| {k[0]} | {k[1]} | {k[2]} | {v} |")
    (RES / "revision.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
