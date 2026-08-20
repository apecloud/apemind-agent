#!/usr/bin/env python3
"""用 Dify API Key 调用流水线，不走 M2M。

    python test_ask_apikey.py
"""

import json
import ssl
import urllib.error
import urllib.request

HOST = "https://go-genai-hub-sit.aiaazure.biz:443"

# aisearch
WORKFLOW_ID = "eff70524-df48-4879-a5b8-4a53ce391f10"
API_KEY = "app-TbHP7uMCefuRgZzFRWDfWfT9"

# coeus
# WORKFLOW_ID = "51a03c81-3d02-43c9-bab6-7586ee4e4466"
# API_KEY = "app-JPKO6VKdSd5REukrDo3N7e0h"

SSL_CTX = ssl._create_unverified_context()

QUESTIONS = [
    "What is AIA Vitality?",
    "How do I earn Vitality points?",
]


def headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


def request(method: str, path: str, payload=None, timeout: int = 120):
    url = HOST.rstrip("/") + path
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers(), method=method)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        status = e.code
    except Exception as e:
        return url, None, {"error": f"{type(e).__name__}: {e}"}
    try:
        parsed = json.loads(body) if body else {}
    except json.JSONDecodeError:
        parsed = {"raw_text": body}
    return url, status, parsed


def shorten(data, limit: int = 400) -> str:
    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "..."


def extract_answer(obj) -> str:
    if isinstance(obj, str):
        return obj.strip()
    if not isinstance(obj, dict):
        return ""
    for key in ("answer", "text", "output", "result", "content"):
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("outputs", "data"):
        nested = extract_answer(obj.get(key))
        if nested:
            return nested
    return ""


def meaning(status) -> str:
    if status is None:
        return "请求失败"
    if status == 200:
        return "成功"
    if status == 400:
        return "接口存在，请求体不对"
    if status == 401:
        return "API Key 无效或不被接受"
    if status == 403:
        return "Key 能识别，但没权限"
    if status == 404:
        return "找不到这条路径或这个应用"
    return f"状态 {status}"


def diagnose() -> str | None:
    print("=" * 60)
    print("API Key 方式诊断")
    print("=" * 60)
    print(f"HOST      : {HOST}")
    print(f"API_KEY   : {API_KEY[:12]}...")
    print(f"FLOW ID   : {WORKFLOW_ID}")
    print()

    print("1) 能不能看到这个应用？")
    see_ok = False
    for path in ("/v1/info", "/v1/parameters"):
        url, status, body = request("GET", path, timeout=30)
        print(f"  GET {path}")
        print(f"      HTTP {status}  {meaning(status)}")
        print(f"      {shorten(body)}")
        print()
        if status == 200:
            see_ok = True
    print("  结论：看得到。" if see_ok else "  结论：用 API Key 看不到 /v1/info、/v1/parameters。")
    print()

    print("2) 能不能调用？")
    candidates = [
        (
            "/v1/workflows/run",
            {"inputs": {"query": "ping"}, "response_mode": "blocking", "user": "eval-apikey"},
        ),
        (
            "/v1/chat-messages",
            {"inputs": {}, "query": "ping", "response_mode": "blocking", "user": "eval-apikey"},
        ),
        (
            f"/digital/genai/v1/api/chat-messages/rags/{WORKFLOW_ID}/workflows/run",
            {
                "query": "ping",
                "inputs": {"query": "ping"},
                "response_mode": "blocking",
                "user": "eval-apikey",
            },
        ),
    ]
    working = None
    for path, payload in candidates:
        url, status, body = request("POST", path, payload, timeout=60)
        print(f"  POST {path}")
        print(f"      HTTP {status}  {meaning(status)}")
        print(f"      {shorten(body)}")
        print()
        if status == 200:
            working = path
            break
        if status in {400, 422} and working is None:
            working = path
    if working:
        print(f"  结论：可调用，后续用 {working}")
    else:
        print("  结论：API Key 方式目前调不通。")
    print("=" * 60)
    print()
    return working


def main() -> None:
    working_path = diagnose()
    if not working_path:
        print("没有可调用的路径，停止提问。")
        return

    if working_path == "/v1/chat-messages":
        def payload(question: str):
            return {"inputs": {}, "query": question, "response_mode": "blocking", "user": "eval-apikey"}
    elif working_path == "/v1/workflows/run":
        def payload(question: str):
            return {"inputs": {"query": question}, "response_mode": "blocking", "user": "eval-apikey"}
    else:
        def payload(question: str):
            return {
                "query": question,
                "inputs": {"query": question},
                "response_mode": "blocking",
                "user": "eval-apikey",
            }

    print("开始提问\n")
    for i, question in enumerate(QUESTIONS, 1):
        print(f"[{i}/{len(QUESTIONS)}] {question}")
        url, status, body = request("POST", working_path, payload(question))
        answer = extract_answer(body) if status == 200 else ""
        print(answer or f"HTTP {status} {shorten(body)}")
        print()


if __name__ == "__main__":
    main()
