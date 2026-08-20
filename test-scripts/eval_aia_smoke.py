#!/usr/bin/env python3
"""冒烟：指定一个测试集，只跑 1 道还没有答案的题。

    python eval_aia_smoke.py hotpotqa
    python eval_aia_smoke.py nq-v2
    python eval_aia_smoke.py musique-v3
    python eval_aia_smoke.py rgb
"""

import argparse

from eval_aia_lib import dataset_names, run_eval

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", choices=dataset_names(), help="一次只跑一个测试集")
    args = parser.parse_args()
    run_eval(args.dataset, limit=1)
