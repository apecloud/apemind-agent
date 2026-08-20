#!/usr/bin/env python3
"""单文件测试：内置问题，调用一条 AIA RAG 流水线。

    python test_ask.py

改流水线只改下面的 WORKFLOW_ID。
"""

import os

# aisearch : eff70524-df48-4879-a5b8-4a53ce391f10
# coeus    : 51a03c81-3d02-43c9-bab6-7586ee4e4466
WORKFLOW_ID = "eff70524-df48-4879-a5b8-4a53ce391f10"
os.environ["WORKFLOW_ID"] = WORKFLOW_ID

from ask import ask, get_token  # noqa: E402

QUESTIONS = [
    "What is AIA Vitality?",
    "How do I earn Vitality points?",
    "What rewards can I get from AIA Vitality?",
]


def main() -> None:
    print(f"流水线 ID: {WORKFLOW_ID}")
    token = get_token()
    print("token 已拿到，开始提问\n")

    for i, question in enumerate(QUESTIONS, 1):
        print(f"[{i}/{len(QUESTIONS)}] {question}")
        row = ask(token, question)
        print(row["answer"] or row["error"])
        print()


if __name__ == "__main__":
    main()
