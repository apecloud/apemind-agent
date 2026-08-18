#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大模型 API 连通性测试（纯标准库，Python 3.6+）

测的是「客户机器能不能调用模型」，不是「域名能不能打开」。

判定：
  ✅ 可用     真实对话接口返回了模型内容
  ⚠️ 入口通   网络到了 API，但没 Key / Key 无效（401/400），还不能当可用
  ❌ 被拦截   典型是 HTTP 403（防火墙 / WAF / 地区限制）
  ❌ 不通     DNS / TCP / TLS / 超时

用法：python3 llm_connectivity_check.py
可选：在 API_KEYS 里填 Key，对应厂商会真的发一条消息。
"""
import json
import socket
import ssl
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

TIMEOUT = 15

# 填了就会对该厂商发一条真实对话；不填只探测 API 入口
API_KEYS = {
    "DeepSeek": "",
}

# name, api_host, web_host, chat_url, model
# chat_url 为空则只测主机，不测对话接口
TARGETS = [
    ("OpenAI",            "api.openai.com",                    "openai.com",              "https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
    ("Anthropic Claude",  "api.anthropic.com",                 "anthropic.com",           "https://api.anthropic.com/v1/messages", None),
    ("Google Gemini",     "generativelanguage.googleapis.com", "cloud.google.com",        None, None),
    ("Azure OpenAI",      "*.openai.azure.com（需客户实例名）",  "azure.com",               None, None),
    ("AWS Bedrock",       "bedrock-runtime.*.amazonaws.com（需区域）", "aws.amazon.com",  None, None),
    ("DeepSeek",          "api.deepseek.com",                  "deepseek.com",            "https://api.deepseek.com/chat/completions", "deepseek-chat"),
    ("阿里通义千问/百炼", "dashscope.aliyuncs.com",             "aliyun.com",              "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "qwen-turbo"),
    ("月之暗面 Kimi",      "api.moonshot.cn",                   "moonshot.cn",             "https://api.moonshot.cn/v1/chat/completions", "moonshot-v1-8k"),
    ("智谱 GLM",          "open.bigmodel.cn",                  "bigmodel.cn",             "https://open.bigmodel.cn/api/paas/v4/chat/completions", "glm-4-flash"),
    ("字节豆包(火山方舟)", "ark.cn-beijing.volces.com",         "volcengine.com",          "https://ark.cn-beijing.volces.com/api/v3/chat/completions", "dummy"),
    ("百度千帆 ERNIE",    "qianfan.baidubce.com",              "bce.baidu.com",           None, None),
    ("腾讯混元",          "hunyuan.tencentcloudapi.com",       "tencent.com",             None, None),
    ("讯飞星火",          "spark-api-open.xf-yun.com",         "xfyun.cn",                "https://spark-api-open.xf-yun.com/v1/chat/completions", "generalv3.5"),
    ("xAI Grok",          "api.x.ai",                          "x.ai",                    "https://api.x.ai/v1/chat/completions", "grok-2-latest"),
    ("Mistral",           "api.mistral.ai",                    "mistral.ai",              "https://api.mistral.ai/v1/chat/completions", "mistral-small-latest"),
    ("Cohere",            "api.cohere.com",                    "cohere.com",              None, None),
    ("OpenRouter(网关)",  "openrouter.ai",                     "openrouter.ai",           "https://openrouter.ai/api/v1/chat/completions", "openai/gpt-4o-mini"),
    ("SiliconFlow(网关)", "api.siliconflow.cn",                "siliconflow.com",         "https://api.siliconflow.cn/v1/chat/completions", "deepseek-ai/DeepSeek-V3"),
    ("HuggingFace",       "huggingface.co",                    "hf.co",                   None, None),
    ("ModelScope(魔搭)",  "modelscope.cn",                     "aliyun.com",              None, None),
]


def resolve(host):
    try:
        return True, socket.gethostbyname(host)
    except Exception as e:
        return False, str(e)[:40]


def tcp_probe(ip, port=443):
    try:
        s = socket.create_connection((ip, port), timeout=TIMEOUT)
        s.close()
        return True
    except Exception:
        return False


def tls_handshake(host, ip=None):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((ip or host, 443), timeout=TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls:
                cert = tls.getpeercert()
                cn = ""
                for rdn in cert.get("subject", ()):
                    for k, v in rdn:
                        if k == "commonName":
                            cn = v
                return True, "TLS ok / cert CN=%s" % cn
    except ssl.SSLCertVerificationError as e:
        return False, "证书校验失败(可能被代理劫持): %s" % str(e)[:60]
    except Exception as e:
        return False, str(e)[:60]


def http_request(url, method="GET", data=None, headers=None):
    hdrs = {"User-Agent": "llm-connectivity-check"}
    if headers:
        hdrs.update(headers)
    req = Request(url, data=data, headers=hdrs, method=method)
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except URLError as e:
        return None, str(getattr(e, "reason", e))[:80]
    except Exception as e:
        return None, str(e)[:80]


def looks_like_api_error(status, body):
    text = (body or "").lower()
    if "application/json" in text:
        return True
    try:
        data = json.loads(body)
    except Exception:
        data = None
    if isinstance(data, dict) and ("error" in data or "message" in data or "code" in data):
        return True
    keys = ("unauthorized", "authentication", "invalid api", "invalid_api",
            "api key", "incorrect api", "permission", "insufficient")
    return any(k in text for k in keys)


def classify_api(status, body):
    snippet = (body or "").replace("\n", " ").strip()[:80]
    if status is None:
        return "down", snippet or "请求失败"

    if status == 200:
        reply = ""
        try:
            data = json.loads(body)
            reply = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        except Exception:
            reply = ""
        reply = reply.strip()
        if reply:
            return "ok", "模型已回复: %s" % reply[:60]
        return "ok", "HTTP 200（接口通）"

    if status == 403:
        if looks_like_api_error(status, body):
            return "auth", "HTTP 403 无权限/Key 被拒（入口通，不是网络阻断）"
        return "blocked", "HTTP 403 被拦截（防火墙/WAF/地区限制）: %s" % snippet

    if status in (401, 400, 404, 422):
        if looks_like_api_error(status, body) or status in (401, 400, 422):
            return "auth", "HTTP %d API 入口通（鉴权/参数响应）" % status
        return "partial", "HTTP %d %s" % (status, snippet)

    if 500 <= status <= 599:
        return "partial", "HTTP %d 服务端错误（主机通）" % status

    return "partial", "HTTP %d %s" % (status, snippet)


def check(name, api_host, web_host, chat_url, model):
    row = {"name": name, "verdict": "down"}
    host = api_host.split("（")[0].strip()

    if "*" in host or host.startswith("bedrock"):
        status, msg = http_request("https://" + web_host)
        row.update(dns="N/A(需实例名)", tcp="—", tls="—", https="—", api="—")
        row["note"] = "API 地址需客户提供实例/区域，仅测官网 HTTP %s %s" % (status, msg[:40])
        row["verdict"] = "partial" if status else "down"
        return row

    ok, ip = resolve(host)
    row["dns"] = "✅ " + ip if ok else "❌ " + ip
    if not ok:
        row.update(tcp="—", tls="—", https="—", api="—", note="DNS 解析失败", verdict="down")
        return row

    t_ok = tcp_probe(ip)
    row["tcp"] = "✅" if t_ok else "❌"
    if not t_ok:
        row.update(tls="—", https="—", api="—", note="TCP 443 不通（防火墙拦截或 IP 封锁）", verdict="down")
        return row

    s_ok, s_msg = tls_handshake(host, ip)
    row["tls"] = "✅" if s_ok else "❌"
    if not s_ok:
        row.update(https="—", api="—", note=s_msg, verdict="down")
        return row

    # 主机 GET：只作参考，不再据此宣布「可用」
    h_status, h_body = http_request("https://" + host)
    if h_status is None:
        row.update(https="❌", api="—", note="HTTPS GET 失败: %s" % h_body, verdict="down")
        return row
    row["https"] = "HTTP %s" % h_status

    if not chat_url:
        kind, msg = classify_api(h_status, h_body)
        # 没有对话接口时，403 也只能说明被拦/或主机拒 GET，不能叫可用
        if kind == "ok":
            kind = "auth"
            msg = "主机通 HTTP %s，未测对话接口" % h_status
        elif kind == "blocked":
            msg = "主机 GET 被拦: %s" % msg
        else:
            msg = "主机通，未测对话接口: %s" % msg
        row.update(api="—", note=msg, verdict=kind)
        return row

    api_key = (API_KEYS.get(name) or "").strip()
    payload = json.dumps({
        "model": model or "dummy",
        "messages": [{"role": "user", "content": "只回复：pong"}],
        "max_tokens": 16,
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    else:
        headers["Authorization"] = "Bearer sk-connectivity-probe"

    a_status, a_body = http_request(chat_url, method="POST", data=payload, headers=headers)
    kind, msg = classify_api(a_status, a_body)
    if api_key and kind == "ok":
        msg = "已带 Key 实测对话。%s" % msg
    elif not api_key and kind == "ok":
        kind = "auth"
        msg = "未填 Key，但对话接口返回了 200: %s" % msg
    row["api"] = "HTTP %s" % (a_status if a_status is not None else "失败")
    row["note"] = msg
    row["verdict"] = kind
    return row


def mark_of(verdict):
    return {
        "ok": "✅ 可用",
        "auth": "⚠️ 入口通",
        "blocked": "❌ 被拦截",
        "partial": "⚠️ 部分",
        "down": "❌ 不通",
    }.get(verdict, "⚠️ 未知")


def main():
    print("=" * 78)
    print("大模型 API 可用性测试  |  开始: %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    print("说明: 主机能打开 ≠ 模型能调用。403 记为被拦截，不再算可用。")
    print("=" * 78)
    lines = []
    results = []
    for name, host, web, chat_url, model in TARGETS:
        row = check(name, host, web, chat_url, model)
        results.append(row)
        line = "%-22s %s | DNS:%s TCP:%s TLS:%s 主机:%s 对话:%s | %s" % (
            name,
            mark_of(row.get("verdict")),
            row.get("dns", "—"),
            row.get("tcp", "—"),
            row.get("tls", "—"),
            row.get("https", "—"),
            row.get("api", "—"),
            row.get("note", ""),
        )
        print(line)
        lines.append(line)
        time.sleep(0.2)

    counts = {"ok": 0, "auth": 0, "blocked": 0, "partial": 0, "down": 0}
    for r in results:
        counts[r.get("verdict", "down")] = counts.get(r.get("verdict", "down"), 0) + 1
    summary = (
        "\n汇总: 共 %d 项 | ✅可用 %d | ⚠️入口通(还不能调用) %d | "
        "❌被拦截 %d | ⚠️部分 %d | ❌不通 %d"
        % (len(results), counts["ok"], counts["auth"], counts["blocked"],
           counts["partial"], counts["down"])
    )
    print(summary)
    lines.append(summary)

    out = "llm_connectivity_report.txt"
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print("报告已写入: %s" % out)
    except Exception as e:
        print("（写报告失败: %s，截图终端即可）" % e)

    print("\n判读提示:")
    print("- ✅ 可用: 已经拿到模型回复，客户机器可以调这个模型")
    print("- ⚠️ 入口通: 网络到了官方 API，但没有效 Key，不能说客户能用")
    print("- ❌ 被拦截: 常见 HTTP 403。test_deepseek.py 失败多半就是这个")
    print("- ❌ 不通: DNS/TCP/TLS 某一层断了")
    print("- 旧脚本把 401/403/404 都标成可用，会误判；现在已拆开")


if __name__ == "__main__":
    main()
