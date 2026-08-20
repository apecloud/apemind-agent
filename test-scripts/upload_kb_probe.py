#!/usr/bin/env python3
"""探测：本地文件能不能传到 Dify 知识库。多种路径和鉴权都试一遍。

    python upload_kb_probe.py /path/to/file.pdf
    python upload_kb_probe.py /path/to/file.pdf --dataset-id <知识库ID>
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import ssl
import uuid
import urllib.error
import urllib.request
from pathlib import Path

GATEWAY = os.environ.get("AIA_GATEWAY_HOST", "https://go-genai-hub-sit.aiaazure.biz:443")
TOKEN_PATH = "/digital/genai/v1/api/m2m_token"
CLIENT_ID = os.environ.get("M2M_CLIENT_ID", "APP-359-885-185")
CLIENT_SECRET = os.environ.get("M2M_CLIENT_SECRET", "4337ea03-94a3-45ac-a2d6-d2f8e03943e9")
WORKFLOW_ID = os.environ.get("WORKFLOW_ID", "eff70524-df48-4879-a5b8-4a53ce391f10")
API_KEY = os.environ.get("DIFY_API_KEY", "app-TbHP7uMCefuRgZzFRWDfWfT9")
SSL_CTX = ssl._create_unverified_context()

LIST_PATHS = [
    "/v1/datasets",
    "/datasets",
    "/digital/genai/v1/api/datasets",
    "/digital/genai/v1/api/knowledge",
    "/digital/genai/v1/api/knowledges",
    f"/digital/genai/v1/api/chat-messages/rags/{WORKFLOW_ID}/datasets",
]


def gateway_headers(token: str | None = None) -> dict[str, str]:
    h = {
        "connection": "close",
        "x-aia-env": os.environ.get("X_AIA_ENV", "dev"),
        "x-aia-lbu": os.environ.get("X_AIA_LBU", "HK"),
        "x-aiahk-context-id": os.environ.get("X_AIAHK_CONTEXT_ID", "5zo2e"),
        "x-aiahk-trace-id": os.environ.get("X_AIAHK_TRACE_ID", "logbooklogr"),
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def apikey_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "connection": "close",
    }


def shorten(data, limit: int = 800) -> str:
    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "..."


def parse_body(raw: str):
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_text": raw}


def send(method: str, path: str, headers: dict, data: bytes | None = None, timeout: int = 60):
    url = GATEWAY.rstrip("/") + path
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return url, resp.status, parse_body(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        return url, e.code, parse_body(raw)
    except Exception as e:
        return url, None, {"error": f"{type(e).__name__}: {e}"}


def get_m2m_token() -> str | None:
    payload = json.dumps(
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "type": "dify_app",
            "object_id": WORKFLOW_ID,
        }
    ).encode("utf-8")
    headers = gateway_headers()
    headers["Content-Type"] = "application/json"
    url, status, body = send("POST", TOKEN_PATH, headers, payload, timeout=30)
    print(f"换 M2M token: HTTP {status}  {shorten(body, 300)}")
    if status == 200 and isinstance(body, dict):
        return body.get("access_token")
    return None


def build_multipart(file_path: Path) -> tuple[bytes, str]:
    boundary = "----DifyBoundary" + uuid.uuid4().hex
    filename = file_path.name
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    meta = json.dumps(
        {
            "indexing_technique": "high_quality",
            "process_rule": {"mode": "automatic"},
        },
        ensure_ascii=False,
    )
    file_bytes = file_path.read_bytes()
    chunks: list[bytes] = []

    def add_field(name: str, value: str, extra: str = ""):
        chunks.append(f"--{boundary}\r\n".encode())
        disposition = f'Content-Disposition: form-data; name="{name}"{extra}\r\n'
        chunks.append(disposition.encode())
        chunks.append(b"\r\n")
        chunks.append(value.encode("utf-8") if isinstance(value, str) else value)
        chunks.append(b"\r\n")

    add_field("data", meta)
    chunks.append(f"--{boundary}\r\n".encode())
    chunks.append(
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
    )
    chunks.append(f"Content-Type: {content_type}\r\n\r\n".encode())
    chunks.append(file_bytes)
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def print_result(title: str, url: str, status, body) -> None:
    print(f"\n--- {title} ---")
    print(f"URL    : {url}")
    print(f"HTTP   : {status}")
    print(f"Body   : {shorten(body)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="本地文件路径")
    parser.add_argument("--dataset-id", help="知识库 ID，不传则先尝试列出知识库")
    parser.add_argument("--dataset-key", help="知识库 API Key；不传则用应用 API Key")
    args = parser.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.is_file():
        raise SystemExit(f"文件不存在: {file_path}")

    dataset_key = args.dataset_key or API_KEY
    print(f"文件        : {file_path} ({file_path.stat().st_size} bytes)")
    print(f"网关        : {GATEWAY}")
    print(f"应用 API Key: {API_KEY[:12]}...")
    print(f"知识库 Key  : {dataset_key[:12]}...")
    print(f"workflow id : {WORKFLOW_ID}")
    print()

    m2m_token = get_m2m_token()
    auths = []
    if m2m_token:
        auths.append(("M2M", gateway_headers(m2m_token)))
    auths.append(("API Key", apikey_headers(dataset_key)))
    auths.append(("API Key + 网关头", {**gateway_headers(), **apikey_headers(dataset_key)}))

    print("\n========== 1) 先看能不能列出知识库 ==========")
    found_ids: list[str] = []
    for auth_name, hdrs in auths:
        for path in LIST_PATHS:
            headers = dict(hdrs)
            url, status, body = send("GET", path, headers, timeout=20)
            interesting = status not in {404, None}
            mark = "  << 值得看" if interesting else ""
            print(f"[{auth_name}] GET {path}  HTTP {status}{mark}")
            if interesting:
                print("   ", shorten(body))
            if status == 200 and isinstance(body, dict):
                rows = body.get("data") or body.get("datasets") or []
                if isinstance(rows, list):
                    for row in rows:
                        if isinstance(row, dict) and row.get("id"):
                            found_ids.append(str(row["id"]))
                            print(f"    发现 dataset: {row.get('name')} / {row['id']}")

    dataset_id = args.dataset_id or (found_ids[0] if found_ids else None)
    if not dataset_id:
        dataset_id = WORKFLOW_ID
        print("\n没有拿到知识库 ID，下面用 workflow id 当 dataset_id 再试上传（多半会 404）。")
    else:
        print(f"\n后续上传使用 dataset_id = {dataset_id}")

    body_bytes, boundary = build_multipart(file_path)
    upload_paths = [
        f"/v1/datasets/{dataset_id}/document/create-by-file",
        f"/datasets/{dataset_id}/document/create-by-file",
        f"/digital/genai/v1/api/datasets/{dataset_id}/document/create-by-file",
        f"/digital/genai/v1/api/knowledge/{dataset_id}/document/create-by-file",
        f"/digital/genai/v1/api/chat-messages/rags/{WORKFLOW_ID}/datasets/{dataset_id}/document/create-by-file",
        "/v1/files/upload",
        "/digital/genai/v1/api/files/upload",
    ]

    print("\n========== 2) 试上传本地文件 ==========")
    for auth_name, hdrs in auths:
        for path in upload_paths:
            headers = dict(hdrs)
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
            timeout = 120 if "create-by-file" in path else 30
            url, status, body = send("POST", path, headers, body_bytes, timeout=timeout)
            title = f"{auth_name}  POST {path}"
            print_result(title, url, status, body)

    print("\n看上面哪条不是 404/401。200/201 就是通了；400 说明接口在但字段或知识库 ID 不对。")


if __name__ == "__main__":
    main()
