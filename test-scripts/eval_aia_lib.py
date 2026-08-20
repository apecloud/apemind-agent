#!/usr/bin/env python3
"""AIA / Dify 评测公共逻辑：读题目、调工作流、按测试集落盘、断点续跑。"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ask import GATEWAY, RUN_PATH, extract_answer, get_token, post

BUNDLE = Path(__file__).resolve().parent / "eval-latest-bundle-v2"
RESULTS_DIR = BUNDLE / "results" / "aia"

DATASETS = [
    {"name": "hotpotqa", "dir": "hotpotqa", "out": "aia-hotpotqa.jsonl"},
    {"name": "nq-v2", "dir": "nq-v2", "out": "aia-nq-v2.jsonl"},
    {"name": "musique-v3", "dir": "musique-v3", "out": "aia-musique-v3.jsonl"},
    {"name": "rgb", "dir": "rgb", "out": "aia-rgb.jsonl"},
]


def load_questions(dataset_dir: Path) -> list[dict]:
    path = dataset_dir / "questions.jsonl"
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("case_key") and row.get("question"):
            rows.append(row)
    return rows


def load_done(out_path: Path) -> set[str]:
    done = set()
    if not out_path.is_file():
        return done
    for line in out_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = row.get("case_key")
        answer = (row.get("answer") or "").strip()
        if key and answer:
            done.add(key)
    return done


def append_result(out_path: Path, row: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def ask_case(token: str, question: str, case_key: str) -> dict:
    started = time.time()
    status, data = post(
        GATEWAY + RUN_PATH,
        {
            "query": question,
            "inputs": {"query": question},
            "response_mode": "blocking",
            "user": f"eval-{case_key}",
        },
        token=token,
        timeout=180,
    )
    elapsed = round(time.time() - started, 3)
    answer = extract_answer(data) if status == 200 else ""
    raw = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    if not answer:
        print(f"    原始返回: {raw[:800]}")
    error = None if answer else f"HTTP {status}"
    return {
        "answer": answer,
        "error": error,
        "elapsed_s": elapsed,
        "http_status": status,
        "raw": raw[:2000],
    }


def run_dataset(token: str, spec: dict, limit: int | None) -> tuple[int, int, int]:
    dataset_dir = BUNDLE / "datasets" / spec["dir"]
    out_path = RESULTS_DIR / spec["out"]
    questions = load_questions(dataset_dir)
    done = load_done(out_path)
    pending = [q for q in questions if q["case_key"] not in done]
    if limit is not None:
        pending = pending[:limit]

    print(f"\n[{spec['name']}] 共 {len(questions)} 题，已有答案 {len(done)}，本次 {len(pending)}")
    if not pending:
        return 0, 0, len(done)

    ok = 0
    fail = 0
    for i, item in enumerate(pending, 1):
        case_key = item["case_key"]
        question = item["question"]
        print(f"  [{i}/{len(pending)}] {case_key}: {question[:80]}")
        result = ask_case(token, question, case_key)
        row = {
            "case_key": case_key,
            "dataset": spec["name"],
            "question": question,
            "expected_answer": item.get("expected_answer"),
            "answer": result["answer"],
            "elapsed_s": result["elapsed_s"],
            "error": result["error"],
            "http_status": result["http_status"],
            "raw": result.get("raw", ""),
        }
        append_result(out_path, row)
        if result["answer"]:
            ok += 1
            print(f"    ok ({result['elapsed_s']}s) {result['answer'][:80]}")
        else:
            fail += 1
            print(f"    fail {result['error']}")
    print(f"  写出 {out_path}")
    return ok, fail, len(done)


def dataset_names() -> list[str]:
    return [item["name"] for item in DATASETS]


def pick_dataset(name: str) -> dict:
    for spec in DATASETS:
        if spec["name"] == name:
            return spec
    raise SystemExit(f"未知测试集 {name}，可选: {', '.join(dataset_names())}")


def run_eval(dataset_name: str, limit: int | None) -> None:
    spec = pick_dataset(dataset_name)
    print(f"测试集 {spec['name']}")
    print(f"题目目录 {BUNDLE / 'datasets' / spec['dir']}")
    print(f"结果文件 {RESULTS_DIR / spec['out']}")
    token = get_token()
    print("token 已拿到")
    ok, fail, done = run_dataset(token, spec, limit)
    print(f"\n[{spec['name']}] 本次成功 {ok}，失败 {fail}，已有答案累计 {done + ok}")
