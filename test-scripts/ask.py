#!/usr/bin/env python3
"""读问题文件，调用 AIA RAG 工作流，把问答结果写出去。

    python ask.py --questions questions.jsonl --output qa.jsonl
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path


GATEWAY = os.environ.get("AIA_GATEWAY_HOST", "https://go-genai-hub-sit.aiaazure.biz:443")
WORKFLOW_ID = os.environ.get("WORKFLOW_ID", "eff70524-df48-4879-a5b8-4a53ce391f10")
RUN_PATH = f"/digital/genai/v1/api/chat-messages/rags/{WORKFLOW_ID}/workflows/run"
TOKEN_PATH = "/digital/genai/v1/api/m2m_token"
CLIENT_ID = os.environ.get("M2M_CLIENT_ID", "APP-359-885-185")
CLIENT_SECRET = os.environ.get("M2M_CLIENT_SECRET", "4337ea03-94a3-45ac-a2d6-d2f8e03943e9")

SSL_CTX = ssl._create_unverified_context()


def headers(token: str | None = None) -> dict[str, str]:
    h = {
        "Content-Type": "application/json",
        "connection": "close",
        "x-aia-env": os.environ.get("X_AIA_ENV", "dev"),
        "x-aia-lbu": os.environ.get("X_AIA_LBU", "HK"),
        "x-aiahk-context-id": os.environ.get("X_AIAHK_CONTEXT_ID", "5zo2e"),
        "x-aiahk-trace-id": os.environ.get("X_AIAHK_TRACE_ID", "logbooklogr"),
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def post(url: str, payload: dict, token: str | None = None, timeout: int = 120):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers(token),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        status = e.code
    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        return status, {"raw_text": body}


def get_token() -> str:
    status, data = post(
        GATEWAY + TOKEN_PATH,
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "type": "dify_app",
            "object_id": WORKFLOW_ID,
        },
        timeout=30,
    )
    if status != 200 or not isinstance(data, dict) or not data.get("access_token"):
        raise RuntimeError(f"获取 token 失败: HTTP {status} {data}")
    return data["access_token"]


def extract_answer(obj) -> str:
    preferred = ("answer", "text", "output", "result", "message", "response", "content")

    def serialize(value) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (dict, list)) and value:
            return json.dumps(value, ensure_ascii=False)
        return ""

    def from_outputs(outputs) -> str:
        if not isinstance(outputs, dict):
            return serialize(outputs)
        lower_map = {str(k).lower(): k for k in outputs}
        for name in preferred:
            actual = lower_map.get(name)
            if actual is not None:
                text = serialize(outputs[actual])
                if text:
                    return text
        for value in outputs.values():
            text = serialize(value)
            if text:
                return text
        return ""

    if isinstance(obj, str):
        return obj.strip()
    if not isinstance(obj, dict):
        return serialize(obj)

    stack = [obj]
    seen: set[int] = set()
    while stack:
        current = stack.pop(0)
        if not isinstance(current, dict):
            continue
        if id(current) in seen:
            continue
        seen.add(id(current))
        for key in ("outputs", "workflowOutputs"):
            if key in current:
                text = from_outputs(current[key])
                if text:
                    return text
        stack.extend(v for v in current.values() if isinstance(v, dict))

    stack = [obj]
    seen.clear()
    while stack:
        current = stack.pop(0)
        if not isinstance(current, dict):
            continue
        if id(current) in seen:
            continue
        seen.add(id(current))
        lower_map = {str(k).lower(): k for k in current}
        for name in preferred:
            actual = lower_map.get(name)
            if actual is not None:
                text = serialize(current[actual])
                if text:
                    return text
        stack.extend(v for v in current.values() if isinstance(v, dict))
    return ""


def load_questions(path: Path) -> list[str]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        questions = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            questions.append(row if isinstance(row, str) else row.get("question") or row.get("Questions"))
        return [q.strip() for q in questions if q]
    if suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as f:
            return [row.get("question") or row.get("Questions") for row in csv.DictReader(f) if row]
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def ask(token: str, question: str) -> dict:
    started = time.time()
    status, data = post(
        GATEWAY + RUN_PATH,
        {
            "query": question,
            "inputs": {"query": question},
            "response_mode": "blocking",
            "user": "eval-pipeline",
        },
        token=token,
    )
    answer = extract_answer(data) if status == 200 else ""
    return {
        "question": question,
        "answer": answer,
        "error": None if answer else f"HTTP {status}",
        "elapsed_seconds": round(time.time() - started, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    questions = load_questions(Path(args.questions))
    if not questions:
        raise SystemExit("问题文件是空的")

    token = get_token()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8") as f:
        for i, question in enumerate(questions, 1):
            print(f"[{i}/{len(questions)}] {question}")
            row = ask(token, question)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(row["answer"] or row["error"])


if __name__ == "__main__":
    main()
