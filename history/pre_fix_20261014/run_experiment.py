"""로컬 모델(Ollama) 실험 실행기.

조건 C0: 모델 단독 / C2: KGT 도구 사용. 두 조건의 시스템 지시문은 도구 안내 문장 하나만 다르다.
결과는 results/runs/<모델>/<조건>/run<k>.jsonl 에 한 줄씩 쌓이며, 중단 후 다시 실행하면 이어서 돈다.

예) python3 code/run_experiment.py --models qwen3.8:27b,gemma4:26b,gemma4:12b --conds C0,C2 --runs 3
    python3 code/run_experiment.py --models gemma4:12b --conds C2 --runs 1 --limit 5   (시험 실행)
"""
import argparse
import hashlib
import json
import re
import sys
import time

from common import DATA, EXPERIMENT_TOOLS, OLLAMA_URL, RESULTS, append_jsonl, http_json, kgt_call, kgt_schema, now_iso, read_jsonl, write_json

BASE_PROMPT = (
    "당신은 한국 관련 사실 질문에 답하는 비서입니다. 정확하게 답하고, 확실하지 않으면 모른다고 답하세요. "
    "답변의 마지막 줄에는 반드시 다음 형식의 JSON 한 줄만 쓰세요: "
    '{"answer": "<답, 모르면 null>", "status": "answered" 또는 "unknown"}'
)
TOOL_SENTENCE = " 아래 도구를 사용할 수 있습니다. 필요하면 도구로 확인한 뒤 답하세요."

TEMPERATURE = 0.7
NUM_CTX = 16384
MAX_ROUNDS = 8
LIST_KEEP = 20
TOOL_RESULT_MAX_CHARS = 16000


def tool_specs():
    """KGT 도구 정의를 받아 고정 저장한다(처음 한 번). 이후에는 저장본을 그대로 쓴다."""
    path = DATA / "tool_schemas.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["tools"]
    tools = []
    for name in EXPERIMENT_TOOLS:
        status, body = kgt_schema(name)
        if status != 200:
            raise SystemExit(f"도구 정의 조회 실패: {name} HTTP {status} {body}")
        tools.append({"type": "function", "function": {
            "name": body["name"], "description": body["description"], "parameters": body["input_schema"]}})
    write_json(path, {"fetched_at": now_iso(), "tools": tools})
    return tools


def compact(obj):
    """긴 목록은 앞 20개만 남기고 잘린 개수를 표시한다(문맥 길이 제한 대응)."""
    if isinstance(obj, list):
        out = [compact(x) for x in obj[:LIST_KEEP]]
        if len(obj) > LIST_KEEP:
            out.append({"_truncated": f"{len(obj) - LIST_KEEP}개 항목 생략"})
        return out
    if isinstance(obj, dict):
        return {k: compact(v) for k, v in obj.items()}
    if isinstance(obj, str) and len(obj) > 500:
        return obj[:500] + "…"
    return obj


def run_tool(name, args):
    if name not in EXPERIMENT_TOOLS:
        return {"ok": False, "error": f"unknown tool {name}"}, 0
    status, body = kgt_call(name, args)
    if status == 402:
        raise SystemExit("KGT 크레딧이 부족합니다(402). 충전 후 다시 실행하세요. 진행분은 저장돼 있습니다.")
    return body, status


def chat(model, messages, tools, seed, think_state):
    body = {"model": model, "messages": messages, "stream": False,
            "options": {"temperature": TEMPERATURE, "seed": seed, "num_ctx": NUM_CTX}}
    if tools:
        body["tools"] = tools
    if think_state.get("send", True):
        body["think"] = False
    status, resp = http_json("POST", f"{OLLAMA_URL}/api/chat", body=body, timeout=600, retries=2)
    if status == 400 and "think" in json.dumps(resp, ensure_ascii=False).lower() and think_state.get("send", True):
        think_state["send"] = False
        return chat(model, messages, tools, seed, think_state)
    if status != 200:
        raise RuntimeError(f"Ollama HTTP {status}: {str(resp)[:300]}")
    return resp


def ask(model, item, cond, run_idx, tools, think_state):
    system = BASE_PROMPT + (TOOL_SENTENCE if cond == "C2" else "")
    user = f"{item['question']}\n(답 형식: {item['answer_format']})"
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    seed = int(hashlib.sha1(f"{item['id']}|{run_idx}".encode()).hexdigest()[:8], 16)
    trace, tokens_in, tokens_out = [], 0, 0
    started = time.time()
    final = None
    for rnd in range(MAX_ROUNDS):
        resp = chat(model, messages, tools if cond == "C2" else None, seed, think_state)
        msg = resp.get("message", {})
        tokens_in += resp.get("prompt_eval_count", 0) or 0
        tokens_out += resp.get("eval_count", 0) or 0
        calls = msg.get("tool_calls") or []
        messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
        if not calls:
            final = msg.get("content", "")
            break
        for c in calls:
            fn = c.get("function", {})
            name, args = fn.get("name"), fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {"_raw": args}
            body, status = run_tool(name, args)
            shown = json.dumps(compact(body), ensure_ascii=False)[:TOOL_RESULT_MAX_CHARS]
            trace.append({"round": rnd, "tool": name, "args": args, "http_status": status, "result": shown})
            messages.append({"role": "tool", "tool_name": name, "content": shown})
    return {
        "id": item["id"], "domain": item["domain"], "model": model, "condition": cond, "run": run_idx,
        "seed": seed, "final_text": final, "hit_round_limit": final is None, "tool_calls": trace,
        "tokens_in": tokens_in, "tokens_out": tokens_out, "seconds": round(time.time() - started, 2),
        "think_param_sent": think_state.get("send", True), "finished_at": now_iso(),
    }


def model_info(model):
    status, body = http_json("POST", f"{OLLAMA_URL}/api/show", body={"model": model})
    _, tags = http_json("GET", f"{OLLAMA_URL}/api/tags")
    digest = next((m.get("digest") for m in (tags or {}).get("models", []) if m.get("name") == model), None)
    return {"model": model, "digest": digest, "details": (body or {}).get("details"),
            "capabilities": (body or {}).get("capabilities"), "recorded_at": now_iso()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--conds", default="C0,C2")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0, help="시험 실행용: 앞에서 N문항만")
    ap.add_argument("--domains", default="", help="쉼표로 구분, 비우면 전체")
    a = ap.parse_args()
    items = read_jsonl(DATA / "items.jsonl")
    if not items:
        raise SystemExit("data/items.jsonl 이 없습니다. 먼저 build_items.py를 실행하세요.")
    if a.domains:
        keep = set(a.domains.split(","))
        items = [i for i in items if i["domain"] in keep]
    if a.limit:
        items = items[: a.limit]
    conds = a.conds.split(",")
    tools = tool_specs() if "C2" in conds else None
    for model in a.models.split(","):
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", model)
        info = model_info(model)
        if "C2" in conds and info.get("capabilities") and "tools" not in info["capabilities"]:
            print(f"! {model}: Ollama가 도구 호출 지원을 표시하지 않습니다 {info['capabilities']}", file=sys.stderr)
        write_json(RESULTS / "runs" / safe / "model_info.json", info)
        think_state = {}
        for k in range(1, a.runs + 1):
            for cond in conds:
                out = RESULTS / "runs" / safe / cond / f"run{k}.jsonl"
                done = {r["id"] for r in read_jsonl(out) if "error" not in r}  # 오류 난 문항은 다시 시도
                todo = [i for i in items if i["id"] not in done]
                print(f"[{model} {cond} run{k}] 남은 문항 {len(todo)}/{len(items)}", file=sys.stderr)
                for n, it in enumerate(todo, 1):
                    try:
                        row = ask(model, it, cond, k, tools, think_state)
                    except RuntimeError as e:
                        row = {"id": it["id"], "domain": it["domain"], "model": model, "condition": cond, "run": k,
                               "error": str(e), "finished_at": now_iso()}
                    append_jsonl(out, row)
                    if n % 10 == 0:
                        print(f"  {n}/{len(todo)}", file=sys.stderr)


if __name__ == "__main__":
    main()
