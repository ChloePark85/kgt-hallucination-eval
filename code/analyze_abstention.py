"""Post-hoc analysis: does C0 abstention track what the model knows?

Reads results/scored.jsonl and writes results/abstention.md.

1. C0 outcome distribution by question type.
2. For the question types the models attempted (all except business status and
   monthly trade count), split model-item pairs into those answered correctly in
   at least one of three runs ("known") and those never answered correctly
   ("unknown"), and compare abstention rates.

Not part of the preregistered analysis.
"""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rows = [json.loads(l) for l in (ROOT / "results" / "scored.jsonl").open(encoding="utf-8")]
c0 = [r for r in rows if r["condition"] == "C0"]
ALWAYS_ABSTAINED = {"status", "trade_count"}


def pct(n, d):
    return f"{100 * n / d:.1f}" if d else "-"


out = ["# C0 abstention analysis (post hoc)", "", "## Outcomes by question type (3 models pooled)", "",
       "| qtype | volatility | n | correct % | incorrect % | abstain % |", "|---|---|---|---|---|---|"]
by_q = collections.defaultdict(list)
for r in c0:
    by_q[(r["qtype"], r["volatility"])].append(r)
for (q, v), rs in sorted(by_q.items()):
    c = collections.Counter(r["outcome"] for r in rs)
    out.append(f"| {q} | {v} | {len(rs)} | {pct(c['correct'], len(rs))} | {pct(c['incorrect'], len(rs))} | {pct(c['abstain'], len(rs))} |")

attempted = [r for r in c0 if r["qtype"] not in ALWAYS_ABSTAINED]
pairs = collections.defaultdict(list)
for r in attempted:
    pairs[(r["model"], r["id"])].append(r)
out += ["", "## Abstention by whether the model ever answered the item correctly", "",
        f"Question types: all except {sorted(ALWAYS_ABSTAINED)} ({len(attempted)} responses).", "",
        "| group | pairs | responses | abstain | abstain % | gave an answer % |", "|---|---|---|---|---|---|"]
for name, known in (("known (>=1 correct)", True), ("unknown (never correct)", False)):
    grp = [rs for rs in pairs.values() if any(r["outcome"] == "correct" for r in rs) == known]
    resp = [r for rs in grp for r in rs]
    c = collections.Counter(r["outcome"] for r in resp)
    answered = c["correct"] + c["incorrect"]
    out.append(f"| {name} | {len(grp)} | {len(resp)} | {c['abstain']} | {pct(c['abstain'], len(resp))} | {pct(answered, len(resp))} |")
total_abstain = sum(r["outcome"] == "abstain" for r in attempted)
out += ["", f"Abstentions in attempted types overall: {total_abstain}/{len(attempted)} ({pct(total_abstain, len(attempted))}%)."]

(ROOT / "results" / "abstention.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
