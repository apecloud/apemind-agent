#!/usr/bin/env python3
"""测试：四个知识库各绑 1 个文件。已绑定的会跳过。

    python bind_kb_smoke.py
"""

from bind_kb_lib import run_all

if __name__ == "__main__":
    run_all(max_files_per_kb=1, batch_size=1)
