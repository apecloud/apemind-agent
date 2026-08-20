#!/usr/bin/env python3
"""全量：四个知识库按文件名前缀把对应文档绑完。每批 10 个，已绑定的会跳过。

    python bind_kb.py
"""

from bind_kb_lib import run_all

if __name__ == "__main__":
    run_all(max_files_per_kb=None)
