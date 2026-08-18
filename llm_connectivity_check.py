#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大模型 API 连通性测试脚本（纯标准库，零依赖，Python 3.6+ 可跑）
用法：python3 llm_connectivity_check.py
输出：逐项测试结果 + 汇总表；同时在脚本目录生成 llm_connectivity_report.txt
"""
import json
import socket
import ssl
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

TIMEOUT = 10  # 秒

# (名称, API地址, 额外API地址备用, 官网, 文档/状态页)
TARGETS = [
    ("OpenAI",            "api.openai.com",           "chatgpt.com",            "openai.com"),
    ("Anthropic Claude",  "api.anthropic.com",        "claude.ai",              "anthropic.com"),
    ("Google Gemini",     "generativelanguage.googleapis.com", "aistudio.google.com", "cloud.google.com"),
    ("Azure OpenAI",      "*.openai.azure.com（需客户实例名）", "management.azure.com", "azure.com"),
    ("AWS Bedrock",       "bedrock-runtime.*.amazonaws.com（需区域）", "aws.amazon.com", "console.aws.amazon.com"),
    ("DeepSeek",          "api.deepseek.com",         "platform.deepseek.com",  "deepseek.com"),
    ("阿里通义千问/百炼", "dashscope.aliyuncs.com",   "bailian.aliyun.com",     "aliyun.com"),
    ("月之暗面 Kimi",      "api.moonshot.cn",          "platform.moonshot.cn",   "moonshot.cn"),
    ("智谱 GLM",          "open.bigmodel.cn",         "chatglm.cn",             "bigmodel.cn"),
    ("字节豆包(火山方舟)", "ark.cn-beijing.volces.com", "volcengine.com",        "console.volcengine.com"),
    ("百度千帆 ERNIE",    "qianfan.baidubce.com",     "yiyan.baidu.com",        "bce.baidu.com"),
    ("腾讯混元",          "hunyuan.tencentcloudapi.com", "cloud.tencent.com",    "tencent.com"),
    ("讯飞星火",          "spark-api-open.xf-yun.com", "xinghuo.xfyun.cn",      "xfyun.cn"),
    ("xAI Grok",          "api.x.ai",                 "x.com",                  "x.ai"),
    ("Mistral",           "api.mistral.ai",           "chat.mistral.ai",        "mistral.ai"),
    ("Cohere",            "api.cohere.com",           "dashboard.cohere.com",   "cohere.com"),
    ("OpenRouter(网关)",  "openrouter.ai",            "",                       "openrouter.ai"),
    ("SiliconFlow(网关)", "api.siliconflow.cn",       "siliconflow.cn",         "siliconflow.com"),
    ("HuggingFace",       "huggingface.co",           "cdn-lfs.huggingface.co", "hf.co"),
    ("ModelScope(魔搭)",  "modelscope.cn",            "www.modelscope.cn",      "aliyun.com"),
]


def resolve(host):
    """DNS 解析"""
    try:
        ip = socket.gethostbyname(host)
        return True, ip
    except Exception as e:
        return False, str(e)[:40]


def tcp_probe(ip, port=443):
    """TCP 连通（443）"""
    try:
        s = socket.create_connection((ip, port), timeout=TIMEOUT)
        s.close()
        return True
    except Exception:
        return False


def tls_handshake(host, ip=None):
    """TLS 握手 + 证书验证（SNI 用真实主机名）"""
    try:
        ctx = ssl.create_default_context()
        addr = ip or host
        with socket.create_connection((addr, 443), timeout=TIMEOUT) as sock:
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


def https_probe(url):
    """完整 HTTPS 请求（经过代理/防火墙的最终判定）"""
    try:
        req = Request(url, method="GET",
                      headers={"User-Agent": "Mozilla/5.0 (connectivity-check)"})
        with urlopen(req, timeout=TIMEOUT) as resp:
            return True, "HTTP %d" % resp.status
    except HTTPError as e:
        # 能拿到 HTTP 状态码 = 链路通（401/403/404 都说明网络层通了）
        return True, "HTTP %d（网络通，鉴权层响应）" % e.code
    except URLError as e:
        reason = getattr(e, "reason", e)
        return False, str(reason)[:70]
    except Exception as e:
        return False, str(e)[:70]


def check(name, api_host, backup_host, web_host):
    row = {"name": name}
    host = api_host.split("（")[0].strip()  # 去掉中文注释部分

    # 0. 通配符/区域占位的主机：只做官网连通
    if "*" in host or host.startswith("bedrock"):
        ok, msg = https_probe("https://" + web_host)
        row.update(dns="N/A(需实例名)", tcp="—", tls="—", https=("✅" if ok else "❌"), note="API 地址需客户提供实例/区域，仅测官网: " + msg)
        return row

    # 1. DNS
    ok, ip = resolve(host)
    row["dns"] = "✅ " + ip if ok else "❌ " + ip
    if not ok:
        row.update(tcp="—", tls="—", https="❌", note="DNS 解析失败")
        return row

    # 2. TCP 443
    t_ok = tcp_probe(ip)
    row["tcp"] = "✅" if t_ok else "❌"
    if not t_ok:
        row.update(tls="—", https="❌", note="TCP 443 不通（防火墙拦截或 IP 封锁）")
        return row

    # 3. TLS
    s_ok, s_msg = tls_handshake(host, ip)
    row["tls"] = "✅" if s_ok else "❌"
    if not s_ok:
        row.update(https="❌", note=s_msg)
        return row

    # 4. 完整 HTTPS GET（会走系统代理设置）
    url = "https://" + host
    h_ok, h_msg = https_probe(url)
    row["https"] = "✅" if h_ok else "❌"
    row["note"] = h_msg

    # 附带测官网（有的客户封 API 但放官网，或反之）
    if web_host:
        w_ok, w_msg = https_probe("https://" + web_host)
        row["web"] = ("✅" if w_ok else "❌")
    return row


def main():
    print("=" * 72)
    print("大模型 API 连通性测试  |  开始: %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 72)
    lines = []
    results = []
    for name, api, backup, web in TARGETS:
        row = check(name, api, backup, web)
        results.append(row)
        ok = row.get("https") == "✅"
        mark = "✅ 可用" if ok else ("⚠️ 部分" if row.get("tcp") == "✅" else "❌ 不通")
        line = "%-22s %s | DNS:%s TCP:%s TLS:%s HTTPS:%s %s" % (
            name, mark, row["dns"], row["tcp"], row["tls"], row["https"], row.get("note", ""))
        print(line)
        lines.append(line)
        time.sleep(0.3)

    total = len(results)
    ok_n = sum(1 for r in results if r.get("https") == "✅")
    part_n = sum(1 for r in results if r.get("https") != "✅" and r.get("tcp") == "✅")
    fail_n = total - ok_n - part_n
    summary = "\n汇总: 共 %d 项 | ✅完全可用 %d | ⚠️网络层通但HTTPS被拦 %d | ❌不通 %d" % (total, ok_n, part_n, fail_n)
    print(summary)
    lines.append(summary)

    report = "\n".join(lines) + "\n"
    out = "llm_connectivity_report.txt"
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write(report)
        print("报告已写入: %s（把这个文件发回来即可）" % out)
    except Exception as e:
        print("（写报告文件失败: %s，直接截图终端输出也行）" % e)

    # 判读提示
    print("\n判读提示:")
    print("- DNS ❌: 客户内网 DNS 不解析该域名（域名级封锁）")
    print("- TCP ❌ 但 DNS ✅: 443 出口被防火墙按 IP/域名拦")
    print("- TLS ❌ 证书校验失败: 大概率有中间人代理（自签证书拦截 HTTPS）")
    print("- TLS ✅ 但 HTTPS ❌: 有代理但只放行白名单 SNI/URL")
    print("- Azure/Bedrock 的 API 地址含实例名/区域，需拿到客户实例后补测")


if __name__ == "__main__":
    main()
