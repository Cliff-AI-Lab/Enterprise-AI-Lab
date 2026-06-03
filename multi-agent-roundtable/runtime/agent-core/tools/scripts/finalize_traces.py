"""把 codesphere saas-test 录到的 raw jsonl 转成完整 GoldenTrace 文件。

输入：raw jsonl（每行一个 event，no meta header）
输出：
- golden trace（开头加 meta line）
- 文件名按 payload.context.agent_run_id（如有）或 session_id 重命名
- category 按用户传入或 'mixed' 默认
"""
import argparse
import json
import sys
from pathlib import Path


def extract_real_run_id(events: list[dict]) -> str | None:
    """从第一个含 context.agent_run_id 的 event 提取真 run_id。"""
    for e in events:
        ctx = (e.get("payload") or {}).get("context") or {}
        rid = ctx.get("agent_run_id")
        if rid:
            return rid
    return None


def categorize(events: list[dict]) -> str:
    """根据事件构成猜场景类别。"""
    types = {e.get("event_type") for e in events}
    if "tool_use" in types or "tool_completed" in types:
        return "tool_use"
    if "ask_user" in types:
        return "ask_user"
    if "cancellation" in types or "cancelled" in types:
        return "cancellation"
    return "chat"


def finalize(in_path: Path, out_dir: Path, category_override: str | None = None) -> Path:
    events = []
    with open(in_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("_kind") != "event":
                continue
            obj.pop("_kind", None)
            events.append(obj)

    if not events:
        raise ValueError(f"No events in {in_path}")

    # 校验 seq 单调
    seqs = [e["seq"] for e in events]
    if seqs != sorted(seqs):
        # rebuild seqs to be monotonic
        events.sort(key=lambda e: e["seq"])

    real_run_id = extract_real_run_id(events) or events[0]["run_id"]
    if real_run_id != events[0]["run_id"]:
        # update all events to use real run_id
        for e in events:
            e["run_id"] = real_run_id

    category = category_override or categorize(events)
    meta = {
        "trace_id": f"saas_test_{real_run_id[:8]}",
        "recorded_at_ms": events[0]["timestamp_ms"],
        "category": category,
        "run_id": real_run_id,
        "schema_version": "1.0.0",
        "tags": ["saas-test", "phase-a-bplus", "first-real-trace"],
    }

    out_path = out_dir / f"{real_run_id}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"_kind": "meta", **meta}, ensure_ascii=False) + "\n")
        for e in events:
            f.write(json.dumps({"_kind": "event", **e}, ensure_ascii=False) + "\n")

    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--category", default=None)
    args = parser.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for raw_file in sorted(in_dir.glob("*.jsonl")):
        try:
            out = finalize(raw_file, out_dir, args.category)
            print(f"OK  {raw_file.name} -> {out.name}")
        except Exception as e:
            print(f"ERR {raw_file.name}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
