#!/usr/bin/env python3
"""按抓包调用 AIA ai-sc：先上传文件，再 notification。

    python upload_ai_sc.py /path/to/file.txt
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import ssl
import uuid
import urllib.error
import urllib.request
from pathlib import Path

HOST = "https://go-genai-hub-sit.aiaazure.biz"
UPLOAD_PATH = "/digital/ai-sc/v1/files/upload"
NOTIFY_PATH = "/digital/ai-sc/v1/files/notification"
SSL_CTX = ssl._create_unverified_context()
WORKSPACE_ID = "7e703e64-66ce-40a5-a34d-79e2e0892bcd"
USER_ID = "Yongzhen.Luo@aia.com"
BEARER_TOKEN = (
    "eyJraWQiOiJfeU52UzA4MGZsRnZEZUxlVWlTSkhnYW5fVjdNdDVrMDViTDdMNGEwLWNnIiwiYWxnIjoiUlMyNTYifQ."
    "eyJ2ZXIiOjEsImp0aSI6IkFULlJ5dDVYdkVNT3d0X1I1UVp5djFFeVBIMHpmN3kxUDEzSl9YTzhSRVR1OXMiLCJpc3MiOiJodHRwczovL2FpYXNlYy5va3RhcHJldmlldy5jb20vb2F1dGgyL2F1c3Nob24zMnJONkZBazBuMWQ3IiwiYXVkIjoiQUlBIEdyb3VwIE9mZmljZSBBSSBLbm93bGVkZ2UgUGxhdGZvcm0iLCJpYXQiOjE3ODcyMTQwNjMsImV4cCI6MTc4NzIxNzY2MywiY2lkIjoiMG9hdTFiZTFoaVhleXhIU0kxZDciLCJ1aWQiOiIwMHV5cHQ4OXhzS1BJNE9DZjFkNyIsInNjcCI6WyJvcGVuaWQiXSwiYXV0aF90aW1lIjoxNzg3MjE0MDU5LCJzdWIiOiJFMTUzMjg5IiwiQURHcm91cHMiOlsiQUlBLUctQXp1cmUtR0VOQUlIVUItU0lULVVTRVIiLCJBSUEtRy1BenVyZS1HRU5BSUhVQi1TSVQtUFJPSkVDVE9XTkVSIiwiQUlBLUctQXp1cmUtR0VOQUlIVUItU0lULUJVSUxERVIiXSwiQURncm91cCI6WyJBSUFfR19BS1BfU0lUX2NoYXRib3QiLCJBSUFfR19BS1BfU0lUX0tNUyIsIkFJQV9HX0FLUF9TSVRfb3ZlcmFsbCIsIkFJQV9HX0FLUF9TSVRfT0MiLCJBSUFfR19BS1BfU0lUX0tNU19FZGl0b3JfS0IiLCJBSUFfR19BS1BfU0lUX0tNU19WaWV3ZXJfRkFRIiwiQUlBX0dfQUtQX1NJVF9LTVNfVmlld2VyX0RvY3VtZW50Il0sImVtYWlsIjoiWW9uZ3poZW4uTHVvQGFpYS5jb20ifQ."
    "euVw13zsKM-xFIuOScg5-GD3QFvZbgddKx04zLTqb8xEY9gUomAjdiuOHqpmdzZXjg-gLv0Jct_SDb2IdMZNGYhYA9pkNoTdOZ2h-3EOUNanyQsbwEMIl5iVMzaf4uShMU34yNDE2B1Jjsx78X7oDM0cz9jPjTTWP8BqWnRHH0PCKLW77wPljJt_HqaRD9L6z5F2Z_3g5rlyrWcC-s_iVGzq8VqmJeU2SlG0G1JsrwvvT71fpxUR5hRwuoKNL8GfPAfWHHWLZWTee7fvR9DK_crga4ZsTF3mPbVZOOtRw8gXx399qvteog_84KWg7qOc9Uh5EMXsbooe2cv571XTDg"
)


def base_headers(token: str) -> dict[str, str]:
    return {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {token}",
        "x-access-token": "",
        "x-aia-env": "dev",
        "x-aia-lbu": "HK",
        "x-aiahk-context-id": "t834o",
        "x-aiahk-trace-id": "lbci1xkton",
        "x-authorization-app": "aaa",
        "x-csrf-token": "undefined",
        "x-requested-with": "XMLHttpRequest",
        "x-user-id": USER_ID,
        "x-workspace-id": WORKSPACE_ID,
    }


def build_upload_body(file_path: Path, boundary: str) -> bytes:
    filename = file_path.name
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    content = file_path.read_bytes()
    return b"".join(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode(),
            content,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )


def request(url: str, headers: dict[str, str], data: bytes, timeout: int = 120):
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        return e.code, raw


def print_http(title: str, url: str, status: int, raw: str):
    print(f"\n=== {title} ===")
    print(f"POST {url}")
    print(f"HTTP {status}")
    try:
        print(json.dumps(json.loads(raw), ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(raw)


def extract_file_ids(raw: str) -> list[str]:
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return []
    data = body.get("data") if isinstance(body, dict) else None
    cases = data.get("successCases") if isinstance(data, dict) else None
    if not isinstance(cases, list):
        return []
    ids = []
    for item in cases:
        if isinstance(item, dict) and item.get("id"):
            ids.append(str(item["id"]))
    return ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="要上传的本地文件")
    args = parser.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.is_file():
        raise SystemExit(f"文件不存在: {file_path}")

    token = BEARER_TOKEN

    print(f"file {file_path} ({file_path.stat().st_size} bytes)")
    print(f"x-workspace-id {WORKSPACE_ID}")

    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex[:16]
    upload_url = HOST.rstrip("/") + UPLOAD_PATH
    upload_headers = base_headers(token)
    upload_headers["accept"] = "*/*"
    upload_headers["content-type"] = f"multipart/form-data; boundary={boundary}"
    status, raw = request(upload_url, upload_headers, build_upload_body(file_path, boundary))
    print_http("1) 上传文件", upload_url, status, raw)

    file_ids = extract_file_ids(raw)
    if not file_ids:
        raise SystemExit("上传没有返回 successCases.id，不发 notification")

    notify_url = HOST.rstrip("/") + NOTIFY_PATH
    notify_headers = base_headers(token)
    notify_headers["content-type"] = "application/json"
    status, raw = request(notify_url, notify_headers, json.dumps(file_ids).encode("utf-8"))
    print_http("2) notification", notify_url, status, raw)


if __name__ == "__main__":
    main()
