"""질문 세트와 정답 스냅샷 생성.

KGT REST로 공공데이터 원천을 조회해 200문항(5영역 × 40)을 만들고,
모든 원본 응답을 data/snapshots/에 저장한다. 사람이 확인할 문항은 data/review_queue.csv에 남긴다.

실행: python3 code/build_items.py            (전체)
      python3 code/build_items.py --only law (한 영역만)
"""
import argparse
import csv
import hashlib
import json
import random
import re
import sys

from common import DATA, SEEDS, kgt_call, now_iso, write_json

SNAP = DATA / "snapshots"
REVIEW = []


def snap(tool, args):
    """도구 호출 결과를 저장하고 data 부분을 돌려준다. 실패하면 None."""
    status, body = kgt_call(tool, args)
    key = hashlib.sha1(json.dumps([tool, args], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]
    path = SNAP / f"{tool}_{key}.json"
    write_json(path, {"tool": tool, "args": args, "http_status": status, "fetched_at": now_iso(), "response": body})
    if status != 200 or not isinstance(body, dict) or not body.get("ok"):
        print(f"  ! {tool} {args} -> HTTP {status}: {str(body)[:200]}", file=sys.stderr)
        return None, path.name
    return body["data"], path.name


def norm(s):
    return re.sub(r"\(주\)|주식회사|㈜|\s", "", s or "").lower()


def review(item_id, reason, detail=""):
    REVIEW.append({"id": item_id, "reason": reason, "detail": detail})


def item(i, domain, qtype, question, answer_type, fmt, gold, sources, volatility):
    return {
        "id": f"{domain}-{i:02d}",
        "domain": domain,
        "qtype": qtype,
        "volatility": volatility,
        "question": question,
        "answer_type": answer_type,
        "answer_format": fmt,
        "gold": gold,
        "sources": sources,
        "built_at": now_iso(),
    }


# ---------------------------------------------------------------- corp
def build_corp():
    seeds = json.loads((SEEDS / "companies.json").read_text(encoding="utf-8"))
    names = seeds["kospi"] + seeds["kosdaq"] + seeds["unlisted"]
    items = []
    for i, name in enumerate(names):
        found, s1 = snap("search_corporation", {"name": name, "limit": 10})
        if not found or not found.get("results"):
            review(f"corp-{i:02d}", "법인 검색 실패", name)
            continue
        exact = [r for r in found["results"] if norm(r["corp_name"]) == norm(name)]
        pick = exact[0] if exact else found["results"][0]
        if not exact:
            review(f"corp-{i:02d}", "법인명 불일치(첫 결과 사용)", f"{name} -> {pick['corp_name']}")
        info, s2 = snap("lookup_corporation", {"corp_code": pick["corp_code"]})
        if not info:
            review(f"corp-{i:02d}", "기업개황 조회 실패", name)
            continue
        cname = info["corp_name"]
        if i % 2 == 0:
            items.append(item(i, "corp", "ceo",
                f"금융감독원 전자공시(DART) 기업개황 기준으로, '{cname}'의 현재 대표자 이름은 누구입니까? 대표자가 여러 명이면 모두 적으세요.",
                "person_names", "이름 (여러 명이면 쉼표로 구분)",
                {"value": info["ceo_name"]}, [s1, s2], "changes"))
        else:
            items.append(item(i, "corp", "established",
                f"금융감독원 전자공시(DART) 기업개황 기준으로, '{cname}'의 설립일은 언제입니까?",
                "date", "YYYY-MM-DD",
                {"value": info["established_date"]}, [s1, s2], "stable"))
    return items


# ---------------------------------------------------------------- biz
STATUS_KO = {"active": "계속사업자", "suspended": "휴업자", "closed": "폐업자", "not_registered": "미등록"}


def build_biz():
    cfg = json.loads((SEEDS / "business_pool.json").read_text(encoding="utf-8"))
    pool = {}
    for term in cfg["search_terms"]:
        found, _ = snap("search_corporation", {"name": term, "limit": cfg["per_term_limit"]})
        for r in (found or {}).get("results", []):
            pool[r["corp_code"]] = r
    print(f"  biz: 후보 법인 {len(pool)}개", file=sys.stderr)
    bizr = {}
    for code in sorted(pool):
        info, s = snap("lookup_corporation", {"corp_code": code})
        if info and re.fullmatch(r"\d{10}", (info.get("business_registration_number") or "").replace("-", "")):
            bizr[info["business_registration_number"].replace("-", "")] = (info["corp_name"], s)
    numbers = sorted(bizr)
    statuses = {}
    for k in range(0, len(numbers), 100):
        res, s = snap("verify_business_registration", {"business_numbers": numbers[k:k + 100]})
        for r in (res or {}).get("results", []):
            statuses[r["business_number"]] = (r, s)
    by = {}
    for bno, (r, s) in statuses.items():
        by.setdefault(r["status"], []).append(bno)
    print("  biz: 상태 분포 " + ", ".join(f"{k}={len(v)}" for k, v in sorted(by.items())), file=sys.stderr)
    rng = random.Random(cfg["random_seed"])
    chosen = []
    for st in ["closed", "suspended"]:
        cand = sorted(by.get(st, []))
        rng.shuffle(cand)
        chosen += cand[: cfg["strata"][st]]
    cand = sorted(by.get("active", []))
    rng.shuffle(cand)
    chosen += cand[: 40 - len(chosen)]
    rng.shuffle(chosen)
    items = []
    for i, bno in enumerate(chosen):
        r, s_status = statuses[bno]
        cname, s_corp = bizr[bno]
        pretty = f"{bno[:3]}-{bno[3:5]}-{bno[5:]}"
        items.append(item(i, "biz", "status",
            f"국세청 사업자등록 상태 기준으로, 사업자등록번호 {pretty}의 현재 상태는 무엇입니까? "
            f"(계속사업자, 휴업자, 폐업자, 미등록 중 하나)",
            "biz_status", "계속사업자 | 휴업자 | 폐업자 | 미등록",
            {"value": r["status"], "label_ko": STATUS_KO.get(r["status"]), "corp_name_hidden": cname},
            [s_corp, s_status], "changes"))
    if len(items) < 40:
        review("biz", "문항 부족", f"{len(items)}개만 생성됨 — search_terms를 늘리세요")
    return items


# ---------------------------------------------------------------- apt
def lawd_for(d):
    """구청·시청을 주소 검색해 시군구 법정동코드 5자리를 얻는다. 시·도와 시군구가 일치하는 결과만 인정한다."""
    found, s = snap("search_address", {"keyword": d["office"], "per_page": 10})
    res = (found or {}).get("results", [])
    hit = [r for r in res if norm(f"{r.get('sido', '')}{r.get('sigungu', '')}") == norm(d["name"])]
    pick = (hit or res or [None])[0]
    return (pick["lawd_code"] if pick else None), s, bool(hit)


def build_apt():
    cfg = json.loads((SEEDS / "districts.json").read_text(encoding="utf-8"))
    items, i = [], 0
    for d in cfg["districts"]:
        code, s_addr, matched = lawd_for(d)
        if not code:
            review(f"apt-{i:02d}", "법정동코드 확인 실패", d["name"])
            i += len(cfg["months"])
            continue
        if not matched:
            review(f"apt-{i:02d}", "시·도/시군구 불일치(첫 결과의 코드 사용)", f"{d['name']} -> {code}")
        for ym in cfg["months"]:
            res, s = snap("apartment_trade_prices", {"lawd_code": code, "deal_month": ym, "per_page": 1})
            if res is None:
                review(f"apt-{i:02d}", "실거래 조회 실패", f"{d['name']} {ym}")
                i += 1
                continue
            y, m = ym[:4], int(ym[4:])
            items.append(item(i, "apt", "trade_count",
                f"국토교통부 아파트 매매 실거래가 공개 자료 기준으로, {y}년 {m}월에 계약된 {d['name']} 아파트 매매 신고 건수는 "
                f"모두 몇 건입니까? (해제 신고된 거래 포함 전체 건수)",
                "int", "정수 (건)",
                {"value": res["total"], "lawd_code": code}, [s_addr, s], "changes"))
            i += 1
    return items


# ---------------------------------------------------------------- juso
def build_juso():
    places = json.loads((SEEDS / "places.json").read_text(encoding="utf-8"))["places"]
    items = []
    for i, place in enumerate(places):
        found, s = snap("search_address", {"keyword": place, "per_page": 10})
        res = (found or {}).get("results", [])
        if not res:
            review(f"juso-{i:02d}", "주소 검색 결과 없음", place)
            continue
        core = norm(place.split()[0])
        hit = [r for r in res if r.get("building_name") and (core in norm(r["building_name"]) or norm(r["building_name"]) in core)]
        pick = (hit or res)[0]
        if not hit:
            review(f"juso-{i:02d}", "건물명 불일치(첫 결과 사용)", f"{place} -> {pick.get('building_name')} / {pick['road_address']}")
        gold = {
            "postal_code": pick["postal_code"],
            "road_address": pick["road_address_main"],
            "sigungu": pick["sigungu"],
            "road_name": pick["road_name"],
            "building_no": pick["building_main_no"] + ("" if pick["building_sub_no"] in ("0", "", None) else f"-{pick['building_sub_no']}"),
        }
        if i % 2 == 0:
            gold["value"] = gold["postal_code"]
            items.append(item(i, "juso", "postal_code",
                f"행정안전부 도로명주소 기준으로, '{place}'의 우편번호(기초구역번호 5자리)는 무엇입니까?",
                "postal", "숫자 5자리", gold, [s], "stable"))
        else:
            gold["value"] = gold["road_address"]
            items.append(item(i, "juso", "road_address",
                f"행정안전부 도로명주소 기준으로, '{place}'의 도로명주소는 무엇입니까? (시·도부터 건물번호까지)",
                "road_address", "예: 서울특별시 중구 세종대로 110", gold, [s], "stable"))
    return items


# ---------------------------------------------------------------- law
def build_law():
    laws = json.loads((SEEDS / "laws.json").read_text(encoding="utf-8"))["laws"]
    items = []
    for i, name in enumerate(laws):
        found, s = snap("search_law", {"query": name, "per_page": 50})
        res = (found or {}).get("results", [])
        exact = [r for r in res if norm(r["name"]) == norm(name) and r.get("law_type") == "법률" and r.get("is_current", True)]
        if not exact:
            review(f"law-{i:02d}", "현행 법률 정확 일치 없음", f"{name}: {[r['name'] for r in res[:5]]}")
            continue
        r = exact[0]
        if i % 2 == 0:
            items.append(item(i, "law", "enforcement_date",
                f"국가법령정보센터 기준으로, 현행 「{name}」의 시행일자는 언제입니까?",
                "date", "YYYY-MM-DD",
                {"value": r["enforcement_date"], "promulgation_date": r["promulgation_date"]}, [s], "changes"))
        else:
            items.append(item(i, "law", "ministry",
                f"국가법령정보센터 기준으로, 「{name}」의 소관부처는 어디입니까? 여러 곳이면 모두 적으세요.",
                "ministry", "부처명 (여러 곳이면 쉼표로 구분)",
                {"value": r["ministry"]}, [s], "stable"))
    return items


def recheck():
    global SNAP
    SNAP = DATA / "snapshots_recheck"
    old = {}
    for line in (DATA / "items.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            old[r["id"]] = r
    changed = []
    for dom, fn in BUILDERS.items():
        if dom == "biz":
            # 사업자 문항은 같은 번호의 현재 상태만 다시 조회한다(표본 재추출 방지)
            ids = [k for k in old if k.startswith("biz-")]
            nums = [re.search(r"(\d{3})-(\d{2})-(\d{5})", old[k]["question"]).group(0).replace("-", "") for k in ids]
            res, _ = snap("verify_business_registration", {"business_numbers": nums})
            now = {r["business_number"]: r["status"] for r in (res or {}).get("results", [])}
            for k, n in zip(ids, nums):
                if now.get(n) != old[k]["gold"]["value"]:
                    changed.append({"id": k, "before": old[k]["gold"]["value"], "after": now.get(n)})
            continue
        for it in fn():
            o = old.get(it["id"])
            if o and o.get("gold_fix") and o["sources"][-1].startswith("../snapshots_goldfix/"):
                # 2026-10-14 수기로 고친 정답: 고칠 때 쓴 검색어로 다시 조회해 같은 주소·우편번호가 있는지 본다
                kw = json.loads((DATA / "snapshots" / o["sources"][-1]).read_text(encoding="utf-8"))["args"]["keyword"]
                found, _ = snap("search_address", {"keyword": kw, "per_page": 10})
                same = [r for r in (found or {}).get("results", [])
                        if r["road_address_main"] == o["gold"]["road_address"] and r["postal_code"] == o["gold"]["postal_code"]]
                if not same:
                    changed.append({"id": it["id"], "before": o["gold"]["value"], "after": "재조회 불일치(수기 확인 필요)"})
                continue
            if o and str(o["gold"]["value"]) != str(it["gold"]["value"]):
                changed.append({"id": it["id"], "before": o["gold"]["value"], "after": it["gold"]["value"]})
    with (DATA / "recheck.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "before", "after"])
        w.writeheader()
        w.writerows(changed)
    print(f"정답이 바뀐 문항 {len(changed)}개 → data/recheck.csv (분석에서 제외하거나 따로 보고)", file=sys.stderr)


BUILDERS = {"corp": build_corp, "biz": build_biz, "apt": build_apt, "juso": build_juso, "law": build_law}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(BUILDERS))
    ap.add_argument("--recheck", action="store_true", help="실험 후 정답을 다시 조회해 바뀐 문항만 data/recheck.csv에 기록(items.jsonl은 그대로)")
    a = ap.parse_args()
    if a.recheck:
        return recheck()
    out = DATA / "items.jsonl"
    existing = {}
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                existing[r["id"]] = r
    for dom, fn in BUILDERS.items():
        if a.only and dom != a.only:
            continue
        print(f"[{dom}] 생성 중...", file=sys.stderr)
        for k in [k for k in existing if k.startswith(dom + "-")]:
            del existing[k]
        for it in fn():
            existing[it["id"]] = it
    rows = [existing[k] for k in sorted(existing)]
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    with (DATA / "review_queue.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "reason", "detail"])
        w.writeheader()
        w.writerows(REVIEW)
    counts = {}
    for r in rows:
        counts[r["domain"]] = counts.get(r["domain"], 0) + 1
    print(f"문항 {len(rows)}개: {counts}. 확인 필요 {len(REVIEW)}건 → data/review_queue.csv", file=sys.stderr)


if __name__ == "__main__":
    main()
