"""규칙 기반 자동 채점. 사람 개입 없음.

각 응답을 correct / incorrect(환각) / abstain(기권) / unparsed 로 분류하고,
C2 응답에는 실패 유형(도구 미호출, 도구 오류, 결과 오독, 검색 실패)을 붙인다.
출력: results/scored.jsonl
"""
import json
import re
import unicodedata
from pathlib import Path

from common import DATA, RESULTS, read_jsonl

SIDO = {
    "서울시": "서울특별시", "서울": "서울특별시", "부산시": "부산광역시", "대구시": "대구광역시", "인천시": "인천광역시",
    "광주시": "광주광역시", "대전시": "대전광역시", "울산시": "울산광역시", "세종시": "세종특별자치시",
    "강원도": "강원특별자치도", "전라북도": "전북특별자치도", "전북": "전북특별자치도", "제주도": "제주특별자치도",
}
ABSTAIN_WORDS = ["모르", "모름", "알 수 없", "확인할 수 없", "확인 불가", "정보가 없", "제공할 수 없", "unknown"]


def nfc(s):
    return unicodedata.normalize("NFC", str(s or ""))


def squash(s):
    return re.sub(r"[\s\(\)\[\]·,.\-_'\"]", "", nfc(s)).lower()


def parse_final(text):
    """마지막 줄 JSON을 찾는다. 실패하면 (None, None)."""
    if not text:
        return None, None
    for m in reversed(list(re.finditer(r"\{[^{}]*\"answer\"[^{}]*\}", nfc(text), re.S))):
        try:
            obj = json.loads(m.group(0))
            return obj.get("answer"), obj.get("status")
        except ValueError:
            continue
    return None, None


def to_date(s):
    s = nfc(s)
    m = re.search(r"(\d{4})\D{0,3}(\d{1,2})\D{0,3}(\d{1,2})", s)
    if m:
        return f"{m.group(1)}{int(m.group(2)):02d}{int(m.group(3)):02d}"
    d = re.sub(r"\D", "", s)
    return d if len(d) == 8 else None


def to_int(s):
    d = re.sub(r"[^\d]", "", nfc(s).split(".")[0])
    return int(d) if d else None


def biz_label(s):
    s = nfc(s)
    if "휴업" in s:
        return "suspended"
    if "폐업" in s:
        return "closed"
    if "미등록" in s or "등록되지" in s:
        return "not_registered"
    if "계속" in s or "정상" in s or "영업" in s:
        return "active"
    return None


def split_names(s):
    return [p for p in re.split(r"[,/·、\s]+|및|외", nfc(s)) if len(p) >= 2]


def norm_addr(s):
    s = nfc(s)
    for short, full in SIDO.items():
        s = re.sub(rf"^{short}(?=\s)", full, s.strip())
    s = re.sub(r"\(.*?\)", "", s)
    return squash(s)


def judge(item, answer):
    """정답 여부(True/False). 답 형식을 읽을 수 없으면 None."""
    g, t = item["gold"], item["answer_type"]
    if t == "date":
        a = to_date(answer)
        return None if a is None else a == re.sub(r"\D", "", str(g["value"]))
    if t == "int":
        a = to_int(answer)
        return None if a is None else a == int(g["value"])
    if t == "postal":
        m = re.search(r"\b(\d{5})\b", nfc(answer))
        return None if not m else m.group(1) == g["value"]
    if t == "biz_status":
        a = biz_label(answer)
        return None if a is None else a == g["value"]
    if t == "person_names":
        names = split_names(g["value"])
        return all(squash(n) in squash(answer) for n in names) if names else None
    if t == "ministry":
        parts = [p for p in re.split(r"[,·/]", nfc(g["value"])) if p.strip()]
        return all(squash(p) in squash(answer) for p in parts)
    if t == "road_address":
        a = norm_addr(answer)
        need = [squash(g["sigungu"]), squash(f"{g['road_name']}{g['building_no']}")]
        return all(n in a for n in need)
    raise ValueError(t)


def gold_in_tools(item, calls):
    """정답 값이 도구 결과 안에 나타났는지(오독과 검색 실패를 가르는 기준)."""
    blob = squash(" ".join(c.get("result", "") for c in calls))
    g = item["gold"]
    if item["answer_type"] == "road_address":
        return squash(f"{g['road_name']}") in blob and squash(g["building_no"]) in blob
    if item["answer_type"] == "biz_status":
        return f'"status":"{g["value"]}"'.replace('"', "") in blob.replace('"', "")
    if item["answer_type"] == "int":
        return re.search(rf'total:?{int(g["value"])}(?!\d)', blob) is not None
    v = squash(g["value"])
    return bool(v) and v in blob


def classify(item, row):
    if "error" in row:
        return {"outcome": "error"}
    answer, status = parse_final(row.get("final_text"))
    text_tail = nfc(row.get("final_text") or "")[-300:]
    if answer is None and status is None:
        # JSON이 없으면 본문 끝부분으로 기권 여부만 판단하고, 나머지는 판독 불가로 둔다
        if any(w in text_tail for w in ABSTAIN_WORDS):
            return {"outcome": "abstain", "answer": None, "parsed_json": False}
        return {"outcome": "unparsed", "answer": None, "parsed_json": False}
    if status == "unknown" or answer in (None, "", "null") or any(w in nfc(answer).lower() for w in ABSTAIN_WORDS):
        return {"outcome": "abstain", "answer": answer, "parsed_json": True}
    ok = judge(item, answer)
    if ok is None:
        # 답했다고 했지만 요구 형식으로 읽을 수 없는 답은 오답으로 집계하고 형식 오류를 표시한다
        return {"outcome": "incorrect", "answer": answer, "parsed_json": True, "format_error": True}
    return {"outcome": "correct" if ok else "incorrect", "answer": answer, "parsed_json": True, "format_error": False}


def failure_type(item, row, outcome):
    if row.get("condition") != "C2" or outcome == "correct":
        return None
    calls = row.get("tool_calls") or []
    if not calls:
        return "no_tool_call"
    if all(c.get("http_status") != 200 for c in calls):
        return "tool_error"
    return "misread" if gold_in_tools(item, calls) else "retrieval_miss"


def main():
    items = {i["id"]: i for i in read_jsonl(DATA / "items.jsonl")}
    out = []
    for f in sorted((RESULTS / "runs").glob("*/*/run*.jsonl")):
        latest = {}
        for r in read_jsonl(f):
            latest[r["id"]] = r  # 같은 문항이 여러 번 있으면 마지막 것
        for r in latest.values():
            it = items.get(r["id"])
            if not it:
                continue
            c = classify(it, r)
            out.append({
                "id": r["id"], "domain": r["domain"], "qtype": it["qtype"], "volatility": it["volatility"],
                "model": r["model"], "condition": r["condition"], "run": r["run"], **c,
                "failure": failure_type(it, r, c["outcome"]),
                "n_tool_calls": len(r.get("tool_calls") or []),
                "tokens_in": r.get("tokens_in"), "tokens_out": r.get("tokens_out"), "seconds": r.get("seconds"),
            })
    path = RESULTS / "scored.jsonl"
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8")
    print(f"채점 {len(out)}건 → {path}")


if __name__ == "__main__":
    main()
