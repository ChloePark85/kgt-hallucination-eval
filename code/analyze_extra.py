"""사후·민감도 분석 (사전 등록 외, 논문에 '탐색적'으로 명시).

1. 엄격 채점: 도로명주소 건물번호 경계 일치, 소관부처 집합 일치(과다 나열 불인정)
2. 정답 수정 문항(gold_fix 11개)과 다중 건물 문항(juso-08) 제외
3. 문항 단위 군집 부트스트랩: C2-C0 정답률 차이의 95% 신뢰구간(같은 문항 3회 반복의 비독립성 반영)
4. 시도한 답 중 오답 비율(정답+오답 기준), 도구 오류 시 응답 분포, 라운드 상한 도달
출력: results/extra.json, results/extra.md
"""
import json, random, re, sys, unicodedata
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import DATA, RESULTS, read_jsonl
from score import nfc, squash, norm_addr, parse_final, judge

items = {i["id"]: i for i in read_jsonl(DATA / "items.jsonl")}
rows = read_jsonl(RESULTS / "scored.jsonl")
raw = {}
for f in sorted((RESULTS / "runs").glob("*/*/run*.jsonl")):
    for r in read_jsonl(f):
        raw[(r["model"], r["condition"], r["run"], r["id"])] = r

def strict_ok(item, answer):
    g, t = item["gold"], item["answer_type"]
    if t == "road_address":
        a = norm_addr(answer)
        rn, bn = squash(g["road_name"]), squash(g["building_no"])
        return squash(g["sigungu"]) in a and re.search(re.escape(rn + bn) + r"(?![0-9])", a) is not None
    if t == "ministry":
        gold = {squash(p) for p in re.split(r"[,·/]", nfc(g["value"])) if p.strip()}
        ans = {squash(p) for p in re.split(r"[,·/]|및", nfc(answer)) if p.strip()}
        return gold == ans
    return judge(item, answer)

def outcome_strict(r):
    if r["outcome"] != "correct":
        return r["outcome"]
    return "correct" if strict_ok(items[r["id"]], r["answer"]) else "incorrect"

for r in rows:
    r["outcome_strict"] = outcome_strict(r)

EXCL = {i for i, it in items.items() if it.get("gold_fix")} | {"juso-08"}

def rate(rs, key="outcome"):
    c = Counter(r[key] for r in rs); n = len(rs)
    return {"n": n, **{k: round(100 * c[k] / n, 1) for k in ["correct", "incorrect", "abstain", "unparsed", "error"]}}

models = sorted({r["model"] for r in rows})
out = {"strict": {}, "excluded_items": sorted(EXCL), "excl": {}, "boot": {}, "attempted": {}, "changed_by_strict": {}}
for m in models:
    for c in ["C0", "C2"]:
        rs = [r for r in rows if r["model"] == m and r["condition"] == c]
        out["strict"][f"{m}|{c}"] = rate(rs, "outcome_strict")
        out["excl"][f"{m}|{c}"] = rate([r for r in rs if r["id"] not in EXCL])
        a = [r for r in rs if r["outcome"] in ("correct", "incorrect")]
        out["attempted"][f"{m}|{c}"] = {"attempted": len(a), "incorrect_among_attempted_pct": round(100 * sum(r["outcome"] == "incorrect" for r in a) / max(1, len(a)), 1)}
        out["changed_by_strict"][f"{m}|{c}"] = sum(r["outcome"] != r["outcome_strict"] for r in rs)
changed = [ (r["model"], r["condition"], r["id"], r["answer"]) for r in rows if r["outcome"] != r["outcome_strict"]]
out["changed_examples"] = changed[:40]

# 군집 부트스트랩 (문항 단위), 2000회
random.seed(20261015)
ids = sorted(items)
for m in models:
    per = defaultdict(lambda: {"C0": [], "C2": []})
    for r in rows:
        if r["model"] == m:
            per[r["id"]][r["condition"]].append(r["outcome"] == "correct")
    def diff(sample):
        c0 = [x for i in sample for x in per[i]["C0"]]; c2 = [x for i in sample for x in per[i]["C2"]]
        return 100 * (sum(c2) / len(c2) - sum(c0) / len(c0))
    est = diff(ids)
    bs = sorted(diff([random.choice(ids) for _ in ids]) for _ in range(2000))
    out["boot"][m] = {"diff_pp": round(est, 1), "ci95": [round(bs[49], 1), round(bs[1949], 1)]}

# 도구 오류·라운드 상한
te = [r for r in rows if r["condition"] == "C2" and r.get("failure") == "tool_error"]
out["tool_error_outcomes"] = dict(Counter(r["outcome"] for r in te))
out["round_limit"] = dict(Counter(f'{k[0]}' for k, v in raw.items() if k[1] == "C2" and v.get("hit_round_limit")))
# C0: 영역별 '답한 비율'(정답+오답) — 기권 경향
out["c0_attempt_by_qtype"] = {}
for q in sorted({r["qtype"] for r in rows}):
    rs = [r for r in rows if r["condition"] == "C0" and r["qtype"] == q]
    out["c0_attempt_by_qtype"][q] = rate(rs)
# C2 도구 호출 수 분포, 첫 호출 도구
out["c2_calls"] = {m: dict(Counter(min(r["n_tool_calls"], 5) for r in rows if r["model"] == m and r["condition"] == "C2")) for m in models}
(RESULTS / "extra.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

md = ["# 사후·민감도 분석 (탐색적)\n"]
md.append("## 엄격 채점 / 정답 수정·다중 건물 문항 제외 / 시도한 답 중 오답\n")
md.append("| model | cond | 사전등록 정답% | 엄격 정답% | 엄격 오답% | 바뀐 건수 | 제외 후 정답% (n) | 시도 중 오답% |\n|---|---|---|---|---|---|---|---|")
pre = {f'{r["model"]}|{r["condition"]}': None for r in rows}
for k in pre:
    m, c = k.split("|")
    base = rate([r for r in rows if r["model"] == m and r["condition"] == c])
    s, e, a = out["strict"][k], out["excl"][k], out["attempted"][k]
    md.append(f"| {m} | {c} | {base['correct']} | {s['correct']} | {s['incorrect']} | {out['changed_by_strict'][k]} | {e['correct']} ({e['n']}) | {a['incorrect_among_attempted_pct']} |")
md.append("\n## 문항 군집 부트스트랩 (C2−C0 정답률 차이, %p)\n")
for m, v in out["boot"].items():
    md.append(f"- {m}: {v['diff_pp']} [{v['ci95'][0]}, {v['ci95'][1]}]")
md.append(f"\n## 도구 오류 시 응답: {out['tool_error_outcomes']}\n\n## 라운드 상한 도달(C2): {out['round_limit']}\n")
md.append("## C0 문항 유형별\n\n| qtype | n | 정답 | 오답 | 기권 |\n|---|---|---|---|---|")
for q, v in out["c0_attempt_by_qtype"].items():
    md.append(f"| {q} | {v['n']} | {v['correct']} | {v['incorrect']} | {v['abstain']} |")
(RESULTS / "extra.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md)); print("\n바뀐 예:", changed[:25])
