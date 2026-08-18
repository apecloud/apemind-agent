#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 DeepSeek 发一条消息，能收到回复就算本地可用。"""
import json
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API_KEY = "sk-REPLACE_ME"
URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"
USER_MESSAGE = "请用一句话介绍你自己，并在最后加上 OK。"

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "你是一个简洁的助手。"},
        {"role": "user", "content": USER_MESSAGE},
    ],
    "max_tokens": 128,
    "temperature": 0.3,
}

print("模型: %s" % MODEL)
print("发送: %s" % USER_MESSAGE)
print("等待回复...")

req = Request(
    URL,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + API_KEY,
    },
    method="POST",
)

started = time.time()
try:
    with urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        status = resp.status
    elapsed = time.time() - started
    data = json.loads(raw)
    choice = data["choices"][0]
    reply = (choice.get("message") or {}).get("content") or ""
    reply = reply.strip()
    usage = data.get("usage") or {}

    if not reply:
        print("失败: 请求成功，但模型没有返回内容")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    print("状态: HTTP %s" % status)
    print("耗时: %.2f 秒" % elapsed)
    print("用量: prompt=%s completion=%s total=%s" % (
        usage.get("prompt_tokens", "-"),
        usage.get("completion_tokens", "-"),
        usage.get("total_tokens", "-"),
    ))
    print("回复:")
    print(reply)
    print("结果: 成功，本地可以调用 DeepSeek")
except HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print("失败: HTTP %s" % e.code)
    print(body)
    raise SystemExit(1)
except URLError as e:
    print("失败: 网络不通 — %s" % e.reason)
    raise SystemExit(1)
except Exception as e:
    print("失败: %s" % e)
    raise SystemExit(1)
