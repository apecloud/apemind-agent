#!/usr/bin/env python3
"""把已上传文件批量绑到知识库。每次 10 个，成功的写入本地记录，重复执行会跳过。"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

HOST = "https://go-genai-hub-sit.aiaazure.biz"
WORKSPACE_ID = "7e703e64-66ce-40a5-a34d-79e2e0892bcd"
USER_ID = "Yongzhen.Luo@aia.com"
BATCH_SIZE = 10

# 四个测评集 → 知识库。缺 ID 的那一项会跳过。
DATASETS = [
    {"name": "hotpotqa", "prefix": "hpqa-", "knowledge_id": ""},
    {"name": "nq-v2", "prefix": "nq-v2-", "knowledge_id": ""},
    {"name": "musique-v3", "prefix": "musique-", "knowledge_id": "44cdc9ac-d36c-4678-a9f2-5f4a5fa405e3"},
    {"name": "rgb", "prefix": "rgb-", "knowledge_id": ""},
]
BEARER_TOKEN = (
    "eyJraWQiOiJfeU52UzA4MGZsRnZEZUxlVWlTSkhnYW5fVjdNdDVrMDViTDdMNGEwLWNnIiwiYWxnIjoiUlMyNTYifQ."
    "eyJ2ZXIiOjEsImp0aSI6IkFULl9pQnhpdVhWaW8ybE0tWGtHNXZsWVgzc3ZOUUhxZElfMFNtTzQ0Yy1QNEEiLCJpc3MiOiJodHRwczovL2FpYXNlYy5va3RhcHJldmlldy5jb20vb2F1dGgyL2F1c3Nob24zMnJONkZBazBuMWQ3IiwiYXVkIjoiQUlBIEdyb3VwIE9mZmljZSBBSSBLbm93bGVkZ2UgUGxhdGZvcm0iLCJpYXQiOjE3ODcyMjM2NzQsImV4cCI6MTc4NzIyNzI3NCwiY2lkIjoiMG9hdTFiZTFoaVhleXhIU0kxZDciLCJ1aWQiOiIwMHV5cHQ4OXhzS1BJNE9DZjFkNyIsInNjcCI6WyJvcGVuaWQiXSwiYXV0aF90aW1lIjoxNzg3MjIzNjcxLCJzdWIiOiJFMTUzMjg5IiwiQURHcm91cHMiOlsiQUlBLUctQXp1cmUtR0VOQUlIVUItU0lULVVTRVIiLCJBSUEtRy1BenVyZS1HRU5BSUhVQi1TSVQtUFJPSkVDVE9XTkVSIiwiQUlBLUctQXp1cmUtR0VOQUlIVUItU0lULUJVSUxERVIiXSwiQURncm91cCI6WyJBSUFfR19BS1BfU0lUX2NoYXRib3QiLCJBSUFfR19BS1BfU0lUX0tNUyIsIkFJQV9HX0FLUF9TSVRfb3ZlcmFsbCIsIkFJQV9HX0FLUF9TSVRfT0MiLCJBSUFfR19BS1BfU0lUX0tNU19FZGl0b3JfS0IiLCJBSUFfR19BS1BfU0lUX0tNU19WaWV3ZXJfRkFRIiwiQUlBX0dfQUtQX1NJVF9LTVNfVmlld2VyX0RvY3VtZW50Il0sImVtYWlsIjoiWW9uZ3poZW4uTHVvQGFpYS5jb20ifQ."
    "Qp4dvLfDnF8dYGPidHGHfPsdBfFs8CFJn49Zc77px6VL-bwlZ_K_gcTg02XYwZZOKUt4lNLojswPC2ksa7yrVWZr4k0VikxwDuUX13UIeiFCSB-_BhQ2Vr0mAhyyB07TJnS2UViy8A5B4H3TBfG6BRZAlt9kMU3YogOpooWFXAraJfaWdMiFryGpejzNe4KCVxVEuJEMwfOOVSjY98-r641e8lRsPCw5GRiLDLvdYYdOJvmYIBOwNwbBTQXdovUO2vt1ZROLjqewLboEjWqJ2kbhw5RzIuhkuJqJLbxMTMSxBZrqyeDoMQG19mdLhVSWHYFLOCceDIL1xNXoFyjnRQ"
)
SSL_CTX = ssl._create_unverified_context()
STATE_DIR = Path(__file__).resolve().parent


def headers() -> dict[str, str]:
    return {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {BEARER_TOKEN}",
        "x-access-token": "",
        "x-aia-env": "dev",
        "x-aia-lbu": "HK",
        "x-aiahk-context-id": "sbymy",
        "x-aiahk-trace-id": "9l03kshjzb",
        "x-authorization-app": "aaa",
        "x-csrf-token": "undefined",
        "x-requested-with": "XMLHttpRequest",
        "x-user-id": USER_ID,
        "x-workspace-id": WORKSPACE_ID,
    }


def request(method: str, url: str, payload=None, timeout: int = 120):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    hdrs = headers()
    if data is not None:
        hdrs["content-type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        return e.code, raw


def parse_json(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_text": raw}


def state_path(knowledge_id: str) -> Path:
    return STATE_DIR / f".kb_bound_{knowledge_id}.json"


def load_bound(knowledge_id: str) -> list[dict]:
    path = state_path(knowledge_id)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    items = data.get("bound") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict) and item.get("id")]


def save_bound(knowledge_id: str, items: list[dict]) -> None:
    seen = {}
    for item in items:
        seen[item["id"]] = item
    path = state_path(knowledge_id)
    path.write_text(
        json.dumps({"knowledge_id": knowledge_id, "bound": list(seen.values())}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


def list_page(knowledge_id: str, page: int, limit: int = 25) -> dict:
    query = urllib.parse.urlencode(
        {"targetKnowledgeId": knowledge_id, "limit": limit, "page": page}
    )
    url = f"{HOST}/digital/ai-sc/v1/files/selection?{query}"
    status, raw = request("GET", url)
    body = parse_json(raw)
    if status != 200:
        raise RuntimeError(f"列文件失败 HTTP {status}: {raw[:400]}")
    return body.get("data") or {}


def iter_candidates(knowledge_id: str, prefix: str, bound_ids: set[str]):
    page = 1
    while True:
        data = list_page(knowledge_id, page)
        files = data.get("fileList") or []
        print(f"  第 {page} 页 {len(files)} 个  total={data.get('total')} hasMore={data.get('hasMore')}")
        for item in files:
            if item.get("isFolder"):
                continue
            name = item.get("fileName") or ""
            file_id = item.get("fileId") or ""
            if prefix and not name.startswith(prefix):
                continue
            if not file_id or file_id in bound_ids:
                continue
            if item.get("hasAdded"):
                continue
            yield {"id": file_id, "name": name}
        if not data.get("hasMore"):
            break
        page += 1


def bind_batch(knowledge_id: str, files: list[dict]) -> tuple[int, dict]:
    url = f"{HOST}/digital/ai-sc/v1/knowledges/{knowledge_id}/files"
    payload = {
        "contentId": 0,
        "fileIds": [
            {
                "effectiveDate": date.today().isoformat(),
                "expireDate": "2099-12-31",
                "id": item["id"],
                "name": item["name"],
            }
            for item in files
        ],
        "parserId": "Default batch process algorithm",
        "parserType": "",
    }
    status, raw = request("POST", url, payload)
    return status, parse_json(raw)


def run_bind(knowledge_id: str, prefix: str = "", max_files: int | None = None, batch_size: int = BATCH_SIZE) -> None:
    bound = load_bound(knowledge_id)
    bound_ids = {item["id"] for item in bound}
    print(f"知识库 {knowledge_id}")
    print(f"前缀   {prefix or '(全部)'}")
    print(f"已绑定 {len(bound_ids)}，记录 {state_path(knowledge_id)}")
    print(f"每批   {batch_size} 个")

    batch: list[dict] = []
    this_run = 0
    for item in iter_candidates(knowledge_id, prefix, bound_ids):
        batch.append(item)
        if len(batch) < batch_size:
            continue
        this_run += _flush(knowledge_id, bound, bound_ids, batch)
        batch = []
        if max_files is not None and this_run >= max_files:
            break

    if batch and (max_files is None or this_run < max_files):
        remain = batch if max_files is None else batch[: max_files - this_run]
        if remain:
            this_run += _flush(knowledge_id, bound, bound_ids, remain)

    print(f"\n本次新绑定 {this_run}，累计 {len(load_bound(knowledge_id))}")
    return this_run


def run_all(max_files_per_kb: int | None, batch_size: int = BATCH_SIZE) -> None:
    configured = [item for item in DATASETS if (item.get("knowledge_id") or "").strip()]
    missing = [item["name"] for item in DATASETS if not (item.get("knowledge_id") or "").strip()]
    if missing:
        print(f"未填写知识库 ID，跳过: {', '.join(missing)}")
        print("在 bind_kb_lib.py 的 DATASETS 里补上 knowledge_id")
    if not configured:
        raise SystemExit("四个知识库 ID 都是空的，先在 DATASETS 里填好")

    for spec in configured:
        print("\n" + "=" * 60)
        print(f"[{spec['name']}] prefix={spec['prefix']}")
        run_bind(
            spec["knowledge_id"].strip(),
            prefix=spec["prefix"],
            max_files=max_files_per_kb,
            batch_size=batch_size,
        )


def _flush(knowledge_id: str, bound: list[dict], bound_ids: set[str], batch: list[dict]) -> int:
    names = ", ".join(item["name"] for item in batch)
    print(f"\n绑定 {len(batch)} 个: {names[:180]}")
    status, body = bind_batch(knowledge_id, batch)
    print(f"HTTP {status}  {json.dumps(body, ensure_ascii=False)[:400]}")
    ok = status == 200 and str((body or {}).get("data")).lower() in {"true", "success", "ok"}
    if not ok and status == 200 and (body or {}).get("status", {}).get("code") == "200":
        ok = True
    if not ok:
        print("  本批失败，不写入记录")
        return 0
    bound.extend(batch)
    bound_ids.update(item["id"] for item in batch)
    save_bound(knowledge_id, bound)
    return len(batch)
