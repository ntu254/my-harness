#!/usr/bin/env python3
"""my-harness v0.2 SQLite-backed CLI MVP."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "harness" / "harness.db"
SCHEMA = ROOT / "state" / "schema" / "001-init.sql"


INTENTS = {"read", "analyze", "plan", "modify", "execute"}
WORK_TYPES = {
    "feature",
    "bugfix",
    "refactor",
    "maintenance",
    "migration",
    "release",
    "incident",
    "harness_improvement",
}
SCOPES = {"file", "module", "repository", "infrastructure", "external_system"}
UNCERTAINTY = {"low", "medium", "high"}
REVERSIBILITY = {"easy", "costly", "irreversible"}
RISKS = {"low", "medium", "high", "critical"}
LANES = {"tiny", "normal", "high_risk", "approval_required"}
STORY_STATUSES = {
    "planned",
    "in_progress",
    "verifying",
    "completed",
    "blocked",
    "failed",
    "cancelled",
    "superseded",
    "needs_human",
}
EVIDENCE_RESULTS = {"pass", "fail", "skipped", "partial"}
TRACE_OUTCOMES = {"completed", "partial", "blocked", "failed"}


def db_path() -> Path:
    return Path(os.environ.get("MY_HARNESS_DB", DEFAULT_DB))


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_db() -> None:
    if not SCHEMA.exists():
        raise SystemExit(f"schema not found: {SCHEMA}")
    with connect() as conn:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))


def require_db() -> None:
    if not db_path().exists():
        raise SystemExit("harness database missing; run `harness init` first")


def row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def emit(data: Any, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    if isinstance(data, list):
        if not data:
            print("(none)")
            return
        keys = list(data[0].keys())
        widths = {key: max(len(key), *(len(str(row.get(key, ""))) for row in data)) for key in keys}
        print("  ".join(key.ljust(widths[key]) for key in keys))
        print("  ".join("-" * widths[key] for key in keys))
        for row in data:
            print("  ".join(str(row.get(key, "")).ljust(widths[key]) for key in keys))
        return
    if isinstance(data, dict):
        for key, value in data.items():
            print(f"{key}: {value}")
        return
    print(data)


def git_head() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None


def git_dirty_files() -> str:
    try:
        output = subprocess.check_output(
            ["git", "status", "--short"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return json.dumps([line.strip() for line in output.splitlines() if line.strip()])
    except Exception:
        return "[]"


def validate_choice(value: str, allowed: set[str], label: str) -> str:
    if value not in allowed:
        raise SystemExit(f"invalid {label}: {value}. Use one of: {', '.join(sorted(allowed))}")
    return value


def cmd_init(args: argparse.Namespace) -> None:
    ensure_db()
    emit({"database": str(db_path()), "status": "initialized"}, args.json)


def cmd_intake_add(args: argparse.Namespace) -> None:
    require_db()
    values = {
        "intent": validate_choice(args.intent, INTENTS, "intent"),
        "work_type": validate_choice(args.work_type, WORK_TYPES, "work-type"),
        "scope": validate_choice(args.scope, SCOPES, "scope"),
        "uncertainty": validate_choice(args.uncertainty, UNCERTAINTY, "uncertainty"),
        "reversibility": validate_choice(args.reversibility, REVERSIBILITY, "reversibility"),
        "risk": validate_choice(args.risk, RISKS, "risk"),
        "lane": validate_choice(args.lane, LANES, "lane"),
        "confidence": args.confidence,
        "summary": args.summary,
        "notes": args.notes,
    }
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO intake
              (intent, work_type, scope, uncertainty, reversibility, risk, lane, confidence, summary, notes)
            VALUES
              (:intent, :work_type, :scope, :uncertainty, :reversibility, :risk, :lane, :confidence, :summary, :notes)
            """,
            values,
        )
        values["id"] = cur.lastrowid
    emit(values, args.json)


def cmd_story_add(args: argparse.Namespace) -> None:
    require_db()
    values = {
        "id": args.id,
        "title": args.title,
        "lane": validate_choice(args.lane, LANES, "lane"),
        "status": validate_choice(args.status, STORY_STATUSES, "status"),
        "contract_ref": args.contract,
        "verify_command": args.verify,
        "notes": args.notes,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO story (id, title, lane, status, contract_ref, verify_command, notes)
            VALUES (:id, :title, :lane, :status, :contract_ref, :verify_command, :notes)
            """,
            values,
        )
    emit(values, args.json)


def cmd_story_update(args: argparse.Namespace) -> None:
    require_db()
    updates: dict[str, Any] = {"id": args.id}
    clauses: list[str] = []
    if args.status:
        updates["status"] = validate_choice(args.status, STORY_STATUSES, "status")
        clauses.append("status = :status")
    if args.evidence is not None:
        updates["evidence"] = args.evidence
        clauses.append("evidence = :evidence")
    if args.notes is not None:
        updates["notes"] = args.notes
        clauses.append("notes = :notes")
    if args.verify is not None:
        updates["verify_command"] = args.verify
        clauses.append("verify_command = :verify_command")
    if not clauses:
        raise SystemExit("story update needs at least one field")
    clauses.append("updated_at = datetime('now')")
    clauses.append("revision = revision + 1")
    expected = ""
    if args.expected_revision is not None:
        updates["expected_revision"] = args.expected_revision
        expected = " AND revision = :expected_revision"
    with connect() as conn:
        cur = conn.execute(
            f"UPDATE story SET {', '.join(clauses)} WHERE id = :id{expected}",
            updates,
        )
        if cur.rowcount != 1:
            raise SystemExit("story update failed: not found or revision conflict")
        row = conn.execute("SELECT * FROM story WHERE id = ?", (args.id,)).fetchone()
    emit(row_dict(row), args.json)


def cmd_evidence_add(args: argparse.Namespace) -> None:
    require_db()
    values = {
        "kind": args.kind,
        "target": args.target,
        "command": args.command,
        "result": validate_choice(args.result, EVIDENCE_RESULTS, "result"),
        "artifact": args.artifact,
        "story_id": args.story,
        "notes": args.notes,
        "git_head": git_head(),
        "dirty_files": git_dirty_files(),
        "trust": args.trust,
    }
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO evidence
              (kind, target, command, result, artifact, story_id, notes, git_head, dirty_files, trust)
            VALUES
              (:kind, :target, :command, :result, :artifact, :story_id, :notes, :git_head, :dirty_files, :trust)
            """,
            values,
        )
        values["id"] = cur.lastrowid
    emit(values, args.json)


def cmd_trace_add(args: argparse.Namespace) -> None:
    require_db()
    values = {
        "summary": args.summary,
        "outcome": validate_choice(args.outcome, TRACE_OUTCOMES, "outcome"),
        "intake_id": args.intake,
        "story_id": args.story,
        "files_read": args.read,
        "files_changed": args.changed,
        "evidence_ids": args.evidence,
        "friction": args.friction,
        "notes": args.notes,
    }
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO trace
              (summary, outcome, intake_id, story_id, files_read, files_changed, evidence_ids, friction, notes)
            VALUES
              (:summary, :outcome, :intake_id, :story_id, :files_read, :files_changed, :evidence_ids, :friction, :notes)
            """,
            values,
        )
        values["id"] = cur.lastrowid
    emit(values, args.json)


def query_table(table: str, args: argparse.Namespace, where: str = "", params: tuple[Any, ...] = ()) -> None:
    require_db()
    limit = max(1, min(args.limit, 200))
    with connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} {where} ORDER BY created_at DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
    emit([row_dict(row) for row in rows], args.json)


def cmd_query_active(args: argparse.Namespace) -> None:
    require_db()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, title, lane, status, revision, verify_command
            FROM story
            WHERE status IN ('planned','in_progress','verifying','blocked','needs_human')
            ORDER BY created_at ASC
            """
        ).fetchall()
    emit([row_dict(row) for row in rows], args.json)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harness", description="my-harness CLI MVP")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="initialize SQLite state")
    init.set_defaults(func=cmd_init)

    intake = sub.add_parser("intake", help="intake commands")
    intake_sub = intake.add_subparsers(dest="intake_command", required=True)
    intake_add = intake_sub.add_parser("add", help="record intake")
    intake_add.add_argument("--intent", required=True)
    intake_add.add_argument("--work-type", required=True)
    intake_add.add_argument("--scope", required=True)
    intake_add.add_argument("--uncertainty", default="low")
    intake_add.add_argument("--reversibility", default="easy")
    intake_add.add_argument("--risk", required=True)
    intake_add.add_argument("--lane", required=True)
    intake_add.add_argument("--confidence", type=float, default=1.0)
    intake_add.add_argument("--summary", required=True)
    intake_add.add_argument("--notes")
    intake_add.set_defaults(func=cmd_intake_add)

    story = sub.add_parser("story", help="story commands")
    story_sub = story.add_subparsers(dest="story_command", required=True)
    story_add = story_sub.add_parser("add", help="add story")
    story_add.add_argument("--id", required=True)
    story_add.add_argument("--title", required=True)
    story_add.add_argument("--lane", required=True)
    story_add.add_argument("--status", default="planned")
    story_add.add_argument("--contract")
    story_add.add_argument("--verify")
    story_add.add_argument("--notes")
    story_add.set_defaults(func=cmd_story_add)
    story_update = story_sub.add_parser("update", help="update story")
    story_update.add_argument("--id", required=True)
    story_update.add_argument("--status")
    story_update.add_argument("--evidence")
    story_update.add_argument("--notes")
    story_update.add_argument("--verify")
    story_update.add_argument("--expected-revision", type=int)
    story_update.set_defaults(func=cmd_story_update)

    evidence = sub.add_parser("evidence", help="evidence commands")
    evidence_sub = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_add = evidence_sub.add_parser("add", help="add evidence")
    evidence_add.add_argument("--kind", required=True)
    evidence_add.add_argument("--target", required=True)
    evidence_add.add_argument("--result", required=True)
    evidence_add.add_argument("--command")
    evidence_add.add_argument("--artifact")
    evidence_add.add_argument("--story")
    evidence_add.add_argument("--notes")
    evidence_add.add_argument("--trust", default="tool_generated")
    evidence_add.set_defaults(func=cmd_evidence_add)

    trace = sub.add_parser("trace", help="trace commands")
    trace_sub = trace.add_subparsers(dest="trace_command", required=True)
    trace_add = trace_sub.add_parser("add", help="add trace")
    trace_add.add_argument("--summary", required=True)
    trace_add.add_argument("--outcome", required=True)
    trace_add.add_argument("--intake", type=int)
    trace_add.add_argument("--story")
    trace_add.add_argument("--read")
    trace_add.add_argument("--changed")
    trace_add.add_argument("--evidence")
    trace_add.add_argument("--friction")
    trace_add.add_argument("--notes")
    trace_add.set_defaults(func=cmd_trace_add)

    query = sub.add_parser("query", help="query state")
    query_sub = query.add_subparsers(dest="query_command", required=True)
    for name, table in [
        ("intakes", "intake"),
        ("stories", "story"),
        ("evidence", "evidence"),
        ("traces", "trace"),
        ("tools", "tool"),
    ]:
        q = query_sub.add_parser(name, help=f"query {name}")
        q.add_argument("--limit", type=int, default=20)
        q.set_defaults(func=lambda args, table=table: query_table(table, args))
    active = query_sub.add_parser("active", help="query active stories")
    active.set_defaults(func=cmd_query_active)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except sqlite3.IntegrityError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
