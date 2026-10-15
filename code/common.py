"""공통 설정과 HTTP 도우미 (표준 라이브러리만 사용)."""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SEEDS = ROOT / "seeds"
RESULTS = ROOT / "results"

KGT_BASE = os.environ.get("KGT_BASE", "https://kr-groundtruth-mcp.vercel.app").rstrip("/")
KGT_API_KEY = os.environ.get("KGT_API_KEY", "")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")

# 실험에 쓰는 KGT 도구 (계정·요금 도구는 제외)
EXPERIMENT_TOOLS = [
    "verify_business_registration",
    "search_address",
    "search_corporation",
    "lookup_corporation",
    "apartment_trade_prices",
    "search_law",
]


def http_json(method, url, body=None, headers=None, timeout=120, retries=3):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    h.update(headers or {})
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                payload = json.loads(raw)
            except ValueError:
                payload = {"raw": raw[:2000]}
            if e.code >= 500 and attempt < retries - 1:
                last = payload
                time.sleep(2 * (attempt + 1))
                continue
            return e.code, payload
        except (urllib.error.URLError, TimeoutError) as e:
            last = {"error": str(e)}
            time.sleep(2 * (attempt + 1))
    return 0, last


def kgt_call(tool, args):
    """KGT REST 호출. (HTTP 상태, 응답 JSON)을 돌려준다."""
    if not KGT_API_KEY:
        raise SystemExit("KGT_API_KEY 환경변수가 없습니다. RUN.md를 보세요.")
    return http_json(
        "POST",
        f"{KGT_BASE}/v1/tools/{tool}",
        body=args,
        headers={"Authorization": f"Bearer {KGT_API_KEY}"},
    )


def kgt_schema(tool):
    return http_json("GET", f"{KGT_BASE}/v1/tools/{tool}")


def read_jsonl(path):
    p = Path(path)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(path, row):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")
