"""dump_run: 从 codesphere-saas events 表 dump 出指定 run_id 的 GoldenTrace。

用法：
  uv run python -m rd_tools.dump_run \\
      --pg-url postgresql://user:pass@host:5432/codesphere \\
      --run-id <run_id> \\
      --category chat \\
      --out traces/golden/01-chat.jsonl

通过直连 PG 读 events 表，不依赖 codesphere-saas 代码（不 import app.*）。
"""
from __future__ import annotations

from typing import Any

import click
import psycopg2
from psycopg2.extras import RealDictCursor
from rd_replay_evals.dumper import EventRow, dump_event_rows
from rd_replay_evals.trace_format import write_trace


def row_to_event_row(row: Any) -> EventRow:
    """SQL row（attribute 风格 / dict 风格都接受）→ EventRow。

    SQLAlchemy 默认返回 attribute 风格；psycopg2 RealDictCursor 返回 dict 风格。
    """
    if isinstance(row, dict):
        project_id = row["project_id"]
        event_type = row["event_type"]
        content = row["content"]
        created_at = row["created_at"]
    else:
        project_id = row.project_id
        event_type = row.event_type
        content = row.content
        created_at = row.created_at

    return EventRow(
        project_id=str(project_id),
        event_type=str(event_type),
        content_json=str(content),
        created_at_ms=int(created_at.timestamp() * 1000),
    )


@click.command()
@click.option("--pg-url", required=True, help="PostgreSQL connection URL")
@click.option("--run-id", required=True, help="run_id to dump")
@click.option(
    "--category",
    required=True,
    help="trace category (chat / single_tool / ...)",
)
@click.option(
    "--out", required=True, type=click.Path(), help="output jsonl path"
)
def main(pg_url: str, run_id: str, category: str, out: str) -> None:
    conn = psycopg2.connect(pg_url, cursor_factory=RealDictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT project_id, event_type, content, created_at
                FROM events
                WHERE event_type = 'ai_session'
                ORDER BY id ASC
                """
            )
            db_rows = cur.fetchall()
    finally:
        conn.close()

    rows = [row_to_event_row(r) for r in db_rows]

    trace = dump_event_rows(rows=rows, run_id=run_id, category=category)
    with open(out, "w", encoding="utf-8") as f:
        write_trace(trace, f)
    click.echo(f"dumped {len(trace.events)} events to {out}")


if __name__ == "__main__":
    main()
