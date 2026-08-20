#!/usr/bin/env python3
"""全量：指定一个测试集，把该集题目跑完。已有答案的题自动跳过。

    python eval_aia_full.py hotpotqa
    python eval_aia_full.py nq-v2
    python eval_aia_full.py musique-v3
    python eval_aia_full.py rgb
"""

import argparse

from eval_aia_lib import dataset_names, run_eval

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", choices=dataset_names(), help="一次只跑一个测试集")
    args = parser.parse_args()
    run_eval(args.dataset, limit=None)
