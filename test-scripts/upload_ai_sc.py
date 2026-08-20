#!/usr/bin/env python3
"""按抓包调用 AIA ai-sc：上传文件或整个目录，再 notification。

    python upload_ai_sc.py /path/to/file.txt
    python upload_ai_sc.py /path/to/dir
    python upload_ai_sc.py /path/to/dir --recursive

成功记录写在目录下的 .ai_sc_uploaded.json，重复执行会跳过已成功文件。
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
STATE_NAME = ".ai_sc_uploaded.json"
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


def state_file(root: Path) -> Path:
    return root / STATE_NAME if root.is_dir() else root.parent / STATE_NAME


def rel_name(root: Path, file_path: Path) -> str:
    base = root if root.is_dir() else root.parent
    return str(file_path.relative_to(base))


def load_uploaded(path: Path) -> list[str]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, dict):
        names = data.get("uploaded") or data.get("files") or []
    elif isinstance(data, list):
        names = data
    else:
        return []
    return [str(name) for name in names]


def save_uploaded(path: Path, names: list[str]) -> None:
    unique = sorted(set(names))
    path.write_text(
        json.dumps({"uploaded": unique}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def collect_files(path: Path, recursive: bool) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise SystemExit(f"路径不存在: {path}")
    iterator = path.rglob("*") if recursive else path.iterdir()
    files = [
        p
        for p in iterator
        if p.is_file() and not p.name.startswith(".")
    ]
    files.sort()
    if not files:
        raise SystemExit(f"目录里没有可上传的文件: {path}")
    return files


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


def print_json(raw: str) -> None:
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
    return [str(item["id"]) for item in cases if isinstance(item, dict) and item.get("id")]


def upload_one(file_path: Path, token: str) -> tuple[int, str, list[str]]:
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex[:16]
    url = HOST.rstrip("/") + UPLOAD_PATH
    headers = base_headers(token)
    headers["accept"] = "*/*"
    headers["content-type"] = f"multipart/form-data; boundary={boundary}"
    status, raw = request(url, headers, build_upload_body(file_path, boundary))
    return status, raw, extract_file_ids(raw)


def notify(file_ids: list[str], token: str) -> tuple[int, str]:
    url = HOST.rstrip("/") + NOTIFY_PATH
    headers = base_headers(token)
    headers["content-type"] = "application/json"
    return request(url, headers, json.dumps(file_ids).encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="本地文件或目录")
    parser.add_argument("--recursive", action="store_true", help="目录时包含子目录")
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    files = collect_files(root, args.recursive)
    record_path = state_file(root)
    uploaded = load_uploaded(record_path)
    uploaded_set = set(uploaded)
    pending = [p for p in files if rel_name(root, p) not in uploaded_set]
    skipped = len(files) - len(pending)

    print(f"共 {len(files)} 个文件，跳过已成功 {skipped}，待上传 {len(pending)}")
    print(f"记录文件 {record_path}  workspace={WORKSPACE_ID}")
    if not pending:
        print("没有新文件需要上传")
        return

    all_ids: list[str] = []
    failed: list[str] = []
    for i, file_path in enumerate(pending, 1):
        name = rel_name(root, file_path)
        print(f"\n[{i}/{len(pending)}] {name} ({file_path.stat().st_size} bytes)")
        status, raw, ids = upload_one(file_path, BEARER_TOKEN)
        print(f"HTTP {status}")
        print_json(raw)
        if ids:
            all_ids.extend(ids)
            uploaded.append(name)
            save_uploaded(record_path, uploaded)
        else:
            failed.append(name)

    if not all_ids:
        raise SystemExit("没有成功上传的文件，不发 notification")

    print(f"\n=== notification ({len(all_ids)} ids) ===")
    status, raw = notify(all_ids, BEARER_TOKEN)
    print(f"HTTP {status}")
    print_json(raw)

    print(f"\n本次成功 {len(all_ids)}，失败 {len(failed)}，累计已记录 {len(load_uploaded(record_path))}")
    for path in failed:
        print(f"  fail {path}")


if __name__ == "__main__":
    main()
