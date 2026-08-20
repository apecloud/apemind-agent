#!/usr/bin/env python3
"""测试：先诊断当前 M2M 账号对这条流水线的可见/可调用，再提问。

    python test_ask.py

改流水线只改下面的 WORKFLOW_ID。
"""

import base64
import json
import os
import urllib.error
import urllib.request

# aisearch : eff70524-df48-4879-a5b8-4a53ce391f10
# coeus    : 51a03c81-3d02-43c9-bab6-7586ee4e4466
WORKFLOW_ID = "eff70524-df48-4879-a5b8-4a53ce391f10"
os.environ["WORKFLOW_ID"] = WORKFLOW_ID

from ask import (  # noqa: E402
    CLIENT_ID,
    CLIENT_SECRET,
    GATEWAY,
    SSL_CTX,
    TOKEN_PATH,
    ask,
    get_token,
    headers,
    post,
)

KNOWN_FLOWS = {
    "aisearch": "eff70524-df48-4879-a5b8-4a53ce391f10",
    "coeus": "51a03c81-3d02-43c9-bab6-7586ee4e4466",
}

QUESTIONS = [
    "What is AIA Vitality?",
    "How do I earn Vitality points?",
    "What rewards can I get from AIA Vitality?",
]


def flow_name(workflow_id: str) -> str:
    for name, value in KNOWN_FLOWS.items():
        if value == workflow_id:
            return name
    return "unknown"


def shorten(data, limit: int = 400) -> str:
    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "..."


def decode_jwt(token: str):
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return None


def http_get(path: str, token: str, timeout: int = 30):
    url = GATEWAY.rstrip("/") + path
    req = urllib.request.Request(url, headers=headers(token), method="GET")
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


def meaning(status) -> str:
    if status is None:
        return "请求失败，没拿到 HTTP 状态"
    if status == 200:
        return "成功"
    if status == 400:
        return "接口存在，但请求体不对"
    if status == 401:
        return "token 不被这个接口接受"
    if status == 403:
        return "接口存在，当前账号没权限"
    if status == 404:
        return "找不到这条流水线，或这条路径不存在"
    if status == 405:
        return "路径存在，但不接受这种 HTTP 方法"
    if status == 406:
        return "接口存在，响应格式不被接受"
    return f"未分类状态 {status}"


def fetch_token(object_id: str):
    return post(
        GATEWAY + TOKEN_PATH,
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "type": "dify_app",
            "object_id": object_id,
        },
        timeout=30,
    )


def diagnose(token: str) -> bool:
    print("=" * 60)
    print("诊断：当前账号 vs 这条流水线")
    print("=" * 60)
    print(f"M2M client_id : {CLIENT_ID}")
    print(f"流水线        : {flow_name(WORKFLOW_ID)} / {WORKFLOW_ID}")
    print(f"网关          : {GATEWAY}")
    print()

    claims = decode_jwt(token)
    if claims:
        print("[token 内容]")
        for key in (
            "object_id",
            "objectId",
            "app_id",
            "appId",
            "client_id",
            "clientId",
            "aud",
            "scope",
            "roles",
            "permissions",
        ):
            if key in claims:
                print(f"  {key}: {claims[key]}")
        bound = claims.get("object_id") or claims.get("objectId")
        if bound and str(bound) != WORKFLOW_ID:
            print(f"  !! token 绑定的 object_id 是 {bound}")
            print(f"     当前要调的流水线是     {WORKFLOW_ID}")
            print("     这两边不一致，调用时很容易 404/403")
        print()
    else:
        print("[token 内容] 不是 JWT，无法从 token 里读绑定的流水线\n")

    print("1) 能不能看到这条流水线？")
    see_paths = [
        f"/digital/genai/v1/api/chat-messages/rags/{WORKFLOW_ID}",
        f"/digital/genai/v1/api/chat-messages/rags/{WORKFLOW_ID}/parameters",
        f"/digital/genai/v1/api/chat-messages/rags/{WORKFLOW_ID}/info",
        f"/digital/genai/v1/api/workflows/{WORKFLOW_ID}",
    ]
    see_hit = False
    for path in see_paths:
        url, status, body = http_get(path, token)
        print(f"  GET {path}")
        print(f"      HTTP {status}  {meaning(status)}")
        print(f"      {shorten(body)}")
        if status in {200, 400, 401, 403, 405, 406}:
            see_hit = True
        print()

    if see_hit:
        print("  结论：网关里能碰到这条流水线相关接口，账号至少「看得到路径」。")
    else:
        print("  结论：查询接口全是 404。这不一定是没权限，也可能是网关根本没提供 GET 查询。")
        print("         能不能看见，要看下面的「调用」结果：403 多半是看见了但没权限，404 才是找不到。")
    print()

    print("2) 能不能调用这条流水线？")
    payload = {
        "query": "ping",
        "inputs": {"query": "ping"},
        "response_mode": "blocking",
        "user": "eval-pipeline",
    }
    call_paths = [
        f"/digital/genai/v1/api/chat-messages/rags/{WORKFLOW_ID}/workflows/run",
        f"/digital/genai/v1/api/workflows/{WORKFLOW_ID}/run",
        f"/digital/genai/v1/api/chat-messages/rags/{WORKFLOW_ID}",
    ]
    can_call = False
    found_api = False
    for path in call_paths:
        url = GATEWAY.rstrip("/") + path
        status, body = post(url, payload, token=token, timeout=60)
        print(f"  POST {path}")
        print(f"      HTTP {status}  {meaning(status)}")
        print(f"      {shorten(body)}")
        if status == 200:
            can_call = True
            found_api = True
        elif status in {400, 403, 405, 406, 422}:
            found_api = True
        print()

    if can_call:
        print("  结论：当前账号可以调用这条流水线。")
    elif found_api:
        print("  结论：接口找得到，但这次没跑成功。看上面是 403（没权限）还是 400（请求体字段不对）。")
    else:
        print("  结论：当前账号调不到这条流水线（一直 404）。")
        print("         常见原因：flow id 不对，或这个 M2M client 没有绑定这条流。")
    print()

    print("3) 对照：这个 M2M 账号能不能给另一条已知流水线换 token？")
    other_id = next((vid for vid in KNOWN_FLOWS.values() if vid != WORKFLOW_ID), None)
    if other_id:
        status, body = fetch_token(other_id)
        print(f"  object_id={flow_name(other_id)} / {other_id}")
        print(f"      HTTP {status}  {meaning(status)}")
        print(f"      {shorten(body)}")
        if status == 200 and isinstance(body, dict) and body.get("access_token"):
            print("      另一条流也能换到 token，说明 client_id 本身有效，问题更像是「当前这条 flow id 不匹配」。")
        elif status in {403, 404}:
            print("      另一条流换 token 失败，说明这个 M2M 账号可能只绑定了特定应用。")
        print()

    print("=" * 60)
    return can_call


def main() -> None:
    print(f"流水线 ID: {flow_name(WORKFLOW_ID)} / {WORKFLOW_ID}")
    token = get_token()
    print("token 已拿到\n")

    can_call = diagnose(token)
    if not can_call:
        print("调用不通，先根据上面的诊断改 flow id 或账号，暂不继续提问。")
        return

    print("token 已拿到，开始提问\n")
    for i, question in enumerate(QUESTIONS, 1):
        print(f"[{i}/{len(QUESTIONS)}] {question}")
        row = ask(token, question)
        print(row["answer"] or row["error"])
        print()


if __name__ == "__main__":
    main()
