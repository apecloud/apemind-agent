#!/usr/bin/env python3
"""全量：指定一个测试集，把该集文档绑完。每批 10 个，已绑定的会跳过。

    python bind_kb.py hotpotqa
    python bind_kb.py nq-v2
    python bind_kb.py musique-v3
    python bind_kb.py rgb
"""

import argparse

from bind_kb_lib import dataset_names, run_dataset

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", choices=dataset_names(), help="一次只绑一个测试集")
    args = parser.parse_args()
    run_dataset(args.dataset, max_files=None)
