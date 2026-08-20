#!/usr/bin/env python3
"""全量：分页找出未绑定文件，每 10 个绑一批，直到没有新文件。

    python bind_kb.py
    python bind_kb.py --prefix musique-
    python bind_kb.py --knowledge-id <知识库ID> --prefix hpqa-
"""

import argparse

from bind_kb_lib import BATCH_SIZE, KNOWLEDGE_ID, run_bind

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--knowledge-id", default=KNOWLEDGE_ID)
    parser.add_argument("--prefix", default="", help="文件名前缀，如 musique- / hpqa- / nq-v2- / rgb-")
    args = parser.parse_args()
    run_bind(args.knowledge_id, prefix=args.prefix, max_files=None, batch_size=BATCH_SIZE)
