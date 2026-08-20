#!/usr/bin/env python3
"""测试：只绑一批，默认 10 个。已绑定的会跳过。

    python bind_kb_smoke.py
    python bind_kb_smoke.py --prefix musique-
    python bind_kb_smoke.py --knowledge-id 44cdc9ac-d36c-4678-a9f2-5f4a5fa405e3 --prefix hpqa-
"""

import argparse

from bind_kb_lib import BATCH_SIZE, KNOWLEDGE_ID, run_bind

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--knowledge-id", default=KNOWLEDGE_ID)
    parser.add_argument("--prefix", default="", help="文件名前缀，如 musique- / hpqa- / nq-v2- / rgb-")
    args = parser.parse_args()
    run_bind(args.knowledge_id, prefix=args.prefix, max_files=BATCH_SIZE, batch_size=BATCH_SIZE)
