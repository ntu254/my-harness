#!/usr/bin/env python3
"""my-harness SQLite-backed CLI."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "harness" / "harness.db"
SCHEMA_DIR = ROOT / "state" / "schema"


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
RUN_STATUSES = {"in_progress", "completed", "failed", "blocked", "needs_human"}
ADAPTER_AVAILABILITY = {"present", "missing", "unknown", "inactive"}
ADAPTER_TRUST = {"project_declared", "user_declared", "verified_local"}

ADAPTER_PRESETS: dict[str, dict[str, str]] = {
    "mock-python": {
        "id": "mock-python",
        "provider": "mock",
        "command_template": "python --version",
        "availability": "present",
        "trust_level": "verified_local",
        "executable": "python",
        "version_command": "python --version",
        "notes": "Local smoke adapter that never sends prompts to an external model.",
    },
    "codex-local": {
        "id": "codex-local",
        "provider": "codex",
        "command_template": "codex exec --prompt-file {prompt_file_shell}",
        "availability": "unknown",
        "trust_level": "user_declared",
        "executable": "codex",
        "version_command": "codex --version",
        "notes": "Codex CLI preset. Verify locally before use; flags may vary by installed version.",
    },
    "claude-local": {
        "id": "claude-local",
        "provider": "claude",
        "command_template": "claude -p {prompt_shell}",
        "availability": "unknown",
        "trust_level": "user_declared",
        "executable": "claude",
        "version_command": "claude --version",
        "notes": "Claude CLI preset. Verify locally before use; flags may vary by installed version.",
    },
}


def db_path() -> Path:
    return Path(os.environ.get("MY_HARNESS_DB", DEFAULT_DB))


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def schema_file_version(path: Path) -> int:
    match = re.match(r"^(\d+)", path.name)
    if not match:
        raise SystemExit(f"schema file must start with a numeric version: {path}")
    return int(match.group(1))


def schema_files() -> list[Path]:
    if not SCHEMA_DIR.exists():
        raise SystemExit(f"schema directory not found: {SCHEMA_DIR}")
    files = sorted(SCHEMA_DIR.glob("*.sql"), key=schema_file_version)
    if not files:
        raise SystemExit(f"no schema files found in: {SCHEMA_DIR}")
    return files


def applied_schema_versions(conn: sqlite3.Connection) -> set[int]:
    try:
        rows = conn.execute("SELECT version FROM schema_version").fetchall()
    except sqlite3.OperationalError:
        return set()
    return {int(row["version"]) for row in rows}


def ensure_db() -> list[int]:
    applied_now: list[int] = []
    with connect() as conn:
        applied = applied_schema_versions(conn)
        for path in schema_files():
            version = schema_file_version(path)
            if version in applied:
                continue
            conn.executescript(path.read_text(encoding="utf-8"))
            conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (?)", (version,))
            applied.add(version)
            applied_now.append(version)
    return applied_now


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


def classify_lane(
    work_type: str,
    scope: str,
    uncertainty: str,
    reversibility: str,
    risk: str,
) -> str:
    if risk == "critical" or reversibility == "irreversible":
        return "approval_required"
    if work_type in {"release", "migration", "incident"} and scope in {"infrastructure", "external_system"}:
        return "approval_required"
    if risk == "high" or uncertainty == "high" or reversibility == "costly":
        return "high_risk"
    if scope in {"infrastructure", "external_system"}:
        return "high_risk"
    if risk == "low" and scope == "file" and uncertainty == "low" and reversibility == "easy":
        return "tiny"
    return "normal"


def sanitize_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "run"


def run_command(command: str, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def shell_quote(value: str) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline([value])
    return shlex.quote(value)


def render_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def prompt_dir() -> Path:
    path = ROOT / "harness" / "prompts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_prompt_file(story_id: str, prompt: str) -> str:
    path = prompt_dir() / f"{sanitize_name(story_id)}.prompt.txt"
    path.write_text(prompt, encoding="utf-8")
    return str(path.relative_to(ROOT))


def read_prompt(args: argparse.Namespace) -> tuple[str, str | None]:
    if args.prompt and args.prompt_file:
        raise SystemExit("use --prompt or --prompt-file, not both")
    if args.prompt_file:
        path = Path(args.prompt_file)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            raise SystemExit(f"prompt file not found: {path}")
        return path.read_text(encoding="utf-8"), str(path.relative_to(ROOT))
    if args.prompt:
        return args.prompt, None
    raise SystemExit("adapter run requires --prompt or --prompt-file")


def adapter_command_values(args: argparse.Namespace, prompt: str, prompt_file: str | None) -> dict[str, str]:
    prompt_file = prompt_file or write_prompt_file(args.id, prompt)
    values = {
        "prompt": prompt,
        "prompt_shell": shell_quote(prompt),
        "prompt_file": prompt_file,
        "prompt_file_shell": shell_quote(prompt_file),
        "story_id": args.id,
        "story_id_shell": shell_quote(args.id),
        "summary": args.summary,
        "summary_shell": shell_quote(args.summary),
        "adapter": args.adapter,
        "adapter_shell": shell_quote(args.adapter),
    }
    return values


def write_run_log(run_id: int, story_id: str, stage: str, command: str, result: subprocess.CompletedProcess[str]) -> str:
    log_dir = ROOT / "harness" / "runs" / f"{sanitize_name(story_id)}-{run_id}"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{stage}.log"
    log_path.write_text(
        "\n".join(
            [
                f"stage: {stage}",
                f"command: {command}",
                f"exit_code: {result.returncode}",
                "",
                "stdout:",
                result.stdout,
                "",
                "stderr:",
                result.stderr,
            ]
        ),
        encoding="utf-8",
    )
    return str(log_path.relative_to(ROOT))


def insert_evidence(conn: sqlite3.Connection, values: dict[str, Any]) -> int:
    payload = {
        "kind": values["kind"],
        "target": values["target"],
        "command": values.get("command"),
        "result": validate_choice(values["result"], EVIDENCE_RESULTS, "result"),
        "artifact": values.get("artifact"),
        "story_id": values.get("story_id"),
        "notes": values.get("notes"),
        "git_head": git_head(),
        "dirty_files": git_dirty_files(),
        "trust": values.get("trust", "tool_generated"),
    }
    cur = conn.execute(
        """
        INSERT INTO evidence
          (kind, target, command, result, artifact, story_id, notes, git_head, dirty_files, trust)
        VALUES
          (:kind, :target, :command, :result, :artifact, :story_id, :notes, :git_head, :dirty_files, :trust)
        """,
        payload,
    )
    return int(cur.lastrowid)


def cmd_init(args: argparse.Namespace) -> None:
    applied = ensure_db()
    emit({"database": str(db_path()), "status": "initialized", "applied_schema_versions": applied}, args.json)


def check_required_files() -> list[dict[str, Any]]:
    required = [
        "AGENTS.md",
        "README.md",
        "harness.yaml",
        "harness/features.json",
        "harness/progress.md",
        "harness/init.ps1",
        "cli/harness.py",
        "state/schema/001-init.sql",
        "state/schema/002-adapters.sql",
        "state/schema/003-adapter-discovery.sql",
    ]
    return [
        {
            "name": f"file:{path}",
            "status": "pass" if (ROOT / path).exists() else "fail",
            "detail": path,
        }
        for path in required
    ]


def check_command(name: str, command: str, timeout: int = 60) -> dict[str, Any]:
    try:
        result = run_command(command, timeout)
        return {
            "name": name,
            "status": "pass" if result.returncode == 0 else "fail",
            "detail": command,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"name": name, "status": "fail", "detail": f"timeout: {command}", "exit_code": None}


def cmd_check(args: argparse.Namespace) -> None:
    applied = ensure_db()
    checks = check_required_files()
    checks.extend(
        [
            check_command("features.json parses", "python -m json.tool harness/features.json", args.timeout),
            check_command("cli compiles", "python -m py_compile cli/harness.py", args.timeout),
            check_command("git diff whitespace", "git diff --check", args.timeout),
        ]
    )
    if args.include_active:
        with connect() as conn:
            active = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM story
                WHERE status IN ('planned','in_progress','verifying','blocked','needs_human')
                """
            ).fetchone()["count"]
        checks.append(
            {
                "name": "active queue",
                "status": "pass" if active == 0 or not args.strict_active else "fail",
                "detail": f"{active} active stories",
            }
        )
    passed = all(item["status"] == "pass" for item in checks)
    payload = {
        "status": "pass" if passed else "fail",
        "database": str(db_path()),
        "applied_schema_versions": applied,
        "checks": checks,
    }
    emit(payload, args.json)
    if not passed:
        raise SystemExit(1)


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
        values["id"] = insert_evidence(conn, values)
    emit(values, args.json)


def cmd_adapter_register(args: argparse.Namespace) -> None:
    ensure_db()
    values = {
        "id": args.id,
        "provider": args.provider,
        "command_template": args.command_template,
        "availability": validate_choice(args.availability, ADAPTER_AVAILABILITY, "availability"),
        "trust_level": validate_choice(args.trust, ADAPTER_TRUST, "trust"),
        "executable": args.executable,
        "version_command": args.version_command,
        "notes": args.notes,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO agent_adapter
              (id, provider, command_template, availability, trust_level,
               executable, version_command, notes)
            VALUES
              (:id, :provider, :command_template, :availability, :trust_level,
               :executable, :version_command, :notes)
            ON CONFLICT(id) DO UPDATE SET
              provider = excluded.provider,
              command_template = excluded.command_template,
              availability = excluded.availability,
              trust_level = excluded.trust_level,
              executable = excluded.executable,
              version_command = excluded.version_command,
              notes = excluded.notes
            """,
            values,
        )
        conn.execute(
            """
            INSERT INTO tool (id, capability, command, availability, trust_level, notes)
            VALUES (:id, 'agent_adapter', :command_template, :availability, :trust_level, :notes)
            ON CONFLICT(id) DO UPDATE SET
              capability = excluded.capability,
              command = excluded.command,
              availability = excluded.availability,
              trust_level = excluded.trust_level,
              notes = excluded.notes
            """,
            values,
        )
    emit(values, args.json)


def register_adapter_values(values: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO agent_adapter
              (id, provider, command_template, availability, trust_level,
               executable, version_command, notes)
            VALUES
              (:id, :provider, :command_template, :availability, :trust_level,
               :executable, :version_command, :notes)
            ON CONFLICT(id) DO UPDATE SET
              provider = excluded.provider,
              command_template = excluded.command_template,
              availability = excluded.availability,
              trust_level = excluded.trust_level,
              executable = excluded.executable,
              version_command = excluded.version_command,
              notes = excluded.notes
            """,
            values,
        )
        conn.execute(
            """
            INSERT INTO tool (id, capability, command, availability, trust_level, notes)
            VALUES (:id, 'agent_adapter', :command_template, :availability, :trust_level, :notes)
            ON CONFLICT(id) DO UPDATE SET
              capability = excluded.capability,
              command = excluded.command,
              availability = excluded.availability,
              trust_level = excluded.trust_level,
              notes = excluded.notes
            """,
            values,
        )


def cmd_adapter_preset(args: argparse.Namespace) -> None:
    ensure_db()
    if args.name == "list":
        emit(list(ADAPTER_PRESETS.values()), args.json)
        return
    names = list(ADAPTER_PRESETS) if args.name == "all" else [args.name]
    installed: list[dict[str, str]] = []
    for name in names:
        if name not in ADAPTER_PRESETS:
            raise SystemExit(f"unknown adapter preset: {name}")
        values = dict(ADAPTER_PRESETS[name])
        register_adapter_values(values)
        installed.append(values)
    emit(installed if len(installed) != 1 else installed[0], args.json)


def cmd_adapter_list(args: argparse.Namespace) -> None:
    ensure_db()
    query_table("agent_adapter", args)


def discover_executable(executable: str) -> tuple[str, str | None]:
    command = "where" if os.name == "nt" else "command -v"
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["where", executable],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
        else:
            result = subprocess.run(
                ["sh", "-lc", f"command -v {shlex.quote(executable)}"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
    except subprocess.TimeoutExpired:
        return "missing", f"discovery timed out: {command} {executable}"
    if result.returncode == 0:
        first = next((line.strip() for line in result.stdout.splitlines() if line.strip()), None)
        return "present", first
    return "missing", result.stderr.strip() or result.stdout.strip() or "not found"


def cmd_adapter_discover(args: argparse.Namespace) -> None:
    ensure_db()
    with connect() as conn:
        if args.adapter:
            rows = conn.execute("SELECT * FROM agent_adapter WHERE id = ?", (args.adapter,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM agent_adapter ORDER BY id").fetchall()
    results: list[dict[str, Any]] = []
    with connect() as conn:
        for row in rows:
            executable = row["executable"] or row["provider"]
            availability, detail = discover_executable(executable)
            version_result: subprocess.CompletedProcess[str] | None = None
            version_output = None
            if availability == "present" and row["version_command"]:
                try:
                    version_result = run_command(row["version_command"], args.timeout)
                    version_output = (version_result.stdout or version_result.stderr).strip()
                except subprocess.TimeoutExpired:
                    version_output = "version command timed out"
            if availability == "present":
                trust = "verified_local"
            else:
                trust = row["trust_level"]
            conn.execute(
                """
                UPDATE agent_adapter
                SET availability = ?, trust_level = ?, last_checked_at = datetime('now'),
                    last_check_result = ?
                WHERE id = ?
                """,
                (availability, trust, version_output or detail, row["id"]),
            )
            conn.execute(
                """
                UPDATE tool
                SET availability = ?, trust_level = ?, notes = ?
                WHERE id = ?
                """,
                (availability, trust, version_output or detail, row["id"]),
            )
            results.append(
                {
                    "id": row["id"],
                    "provider": row["provider"],
                    "executable": executable,
                    "availability": availability,
                    "detail": detail,
                    "version": version_output,
                }
            )
    emit(results, args.json)


def cmd_adapter_run(args: argparse.Namespace) -> None:
    ensure_db()
    with connect() as conn:
        adapter = conn.execute("SELECT * FROM agent_adapter WHERE id = ?", (args.adapter,)).fetchone()
    if adapter is None:
        raise SystemExit(f"adapter not found: {args.adapter}")
    if adapter["availability"] in {"missing", "inactive"} and not args.allow_unavailable:
        raise SystemExit(f"adapter is {adapter['availability']}: {args.adapter}")
    prompt, prompt_file = read_prompt(args)
    values = adapter_command_values(args, prompt, prompt_file)
    agent_command = render_template(adapter["command_template"], values)
    if "{prompt}" in adapter["command_template"] and not args.allow_raw_prompt:
        raise SystemExit("adapter template uses raw {prompt}; use {prompt_shell}, {prompt_file_shell}, or --allow-raw-prompt")
    run_args = argparse.Namespace(
        json=args.json,
        id=args.id,
        summary=args.summary,
        agent_command=agent_command,
        verify_command=args.verify_command,
        intent=args.intent,
        work_type=args.work_type,
        scope=args.scope,
        uncertainty=args.uncertainty,
        reversibility=args.reversibility,
        risk=args.risk,
        lane=args.lane,
        confidence=args.confidence,
        timeout=args.timeout,
        allow_high_risk=args.allow_high_risk,
        changed=args.changed,
        notes=args.notes or f"adapter={args.adapter}",
        adapter=args.adapter,
        prompt=prompt,
    )
    cmd_run_once(run_args)


def cmd_run_once(args: argparse.Namespace) -> None:
    ensure_db()
    work_type = validate_choice(args.work_type, WORK_TYPES, "work-type")
    scope = validate_choice(args.scope, SCOPES, "scope")
    uncertainty = validate_choice(args.uncertainty, UNCERTAINTY, "uncertainty")
    reversibility = validate_choice(args.reversibility, REVERSIBILITY, "reversibility")
    risk = validate_choice(args.risk, RISKS, "risk")
    lane = args.lane or classify_lane(work_type, scope, uncertainty, reversibility, risk)
    lane = validate_choice(lane, LANES, "lane")
    if args.timeout < 1:
        raise SystemExit("timeout must be positive")

    with connect() as conn:
        intake_id = conn.execute(
            """
            INSERT INTO intake
              (intent, work_type, scope, uncertainty, reversibility, risk, lane, confidence, summary, notes)
            VALUES
              (:intent, :work_type, :scope, :uncertainty, :reversibility, :risk, :lane, :confidence, :summary, :notes)
            """,
            {
                "intent": validate_choice(args.intent, INTENTS, "intent"),
                "work_type": work_type,
                "scope": scope,
                "uncertainty": uncertainty,
                "reversibility": reversibility,
                "risk": risk,
                "lane": lane,
                "confidence": args.confidence,
                "summary": args.summary,
                "notes": args.notes,
            },
        ).lastrowid
        conn.execute(
            """
            INSERT INTO story (id, title, lane, status, verify_command, notes)
            VALUES (?, ?, ?, 'planned', ?, ?)
            """,
            (args.id, args.summary, lane, args.verify_command, args.notes),
        )
        run_id = conn.execute(
            """
            INSERT INTO agent_run
              (intake_id, story_id, lane, status, agent_command, verify_command,
               timeout_seconds, adapter_id, prompt, notes)
            VALUES
              (?, ?, ?, 'in_progress', ?, ?, ?, ?, ?, ?)
            """,
            (
                intake_id,
                args.id,
                lane,
                args.agent_command,
                args.verify_command,
                args.timeout,
                getattr(args, "adapter", None),
                getattr(args, "prompt", None),
                args.notes,
            ),
        ).lastrowid

    if lane in {"high_risk", "approval_required"} and not args.allow_high_risk:
        with connect() as conn:
            conn.execute(
                "UPDATE story SET status = 'needs_human', updated_at = datetime('now'), revision = revision + 1 WHERE id = ?",
                (args.id,),
            )
            conn.execute(
                """
                UPDATE agent_run
                SET status = 'needs_human', completed_at = datetime('now'), notes = ?
                WHERE id = ?
                """,
                ("High-risk lane requires --allow-high-risk before command execution.", run_id),
            )
            conn.execute(
                """
                INSERT INTO trace (summary, outcome, intake_id, story_id, friction, notes)
                VALUES (?, 'blocked', ?, ?, 'needs human approval', ?)
                """,
                (args.summary, intake_id, args.id, f"lane={lane}; command not executed"),
            )
        emit(
            {
                "run_id": run_id,
                "intake_id": intake_id,
                "story_id": args.id,
                "lane": lane,
                "status": "needs_human",
                "executed": False,
                "reason": "high-risk lane requires --allow-high-risk",
            },
            args.json,
        )
        return

    evidence_ids: list[int] = []
    status = "completed"
    agent_exit: int | None = None
    verify_exit: int | None = None
    log_dir: str | None = None

    try:
        with connect() as conn:
            conn.execute(
                "UPDATE story SET status = 'in_progress', updated_at = datetime('now'), revision = revision + 1 WHERE id = ?",
                (args.id,),
            )
        agent_result = run_command(args.agent_command, args.timeout)
        agent_exit = agent_result.returncode
        agent_log = write_run_log(run_id, args.id, "agent", args.agent_command, agent_result)
        log_dir = str(Path(agent_log).parent)
        with connect() as conn:
            evidence_ids.append(
                insert_evidence(
                    conn,
                    {
                        "kind": "agent",
                        "target": "runner",
                        "command": args.agent_command,
                        "result": "pass" if agent_exit == 0 else "fail",
                        "artifact": agent_log,
                        "story_id": args.id,
                        "notes": f"agent exit code {agent_exit}",
                    },
                )
            )
        if agent_exit != 0:
            status = "failed"
        else:
            with connect() as conn:
                conn.execute(
                    "UPDATE story SET status = 'verifying', updated_at = datetime('now'), revision = revision + 1 WHERE id = ?",
                    (args.id,),
                )
            verify_result = run_command(args.verify_command, args.timeout)
            verify_exit = verify_result.returncode
            verify_log = write_run_log(run_id, args.id, "verify", args.verify_command, verify_result)
            with connect() as conn:
                evidence_ids.append(
                    insert_evidence(
                        conn,
                        {
                            "kind": "verification",
                            "target": "runner",
                            "command": args.verify_command,
                            "result": "pass" if verify_exit == 0 else "fail",
                            "artifact": verify_log,
                            "story_id": args.id,
                            "notes": f"verify exit code {verify_exit}",
                        },
                    )
                )
            if verify_exit != 0:
                status = "failed"
    except subprocess.TimeoutExpired:
        status = "failed"
        with connect() as conn:
            evidence_ids.append(
                insert_evidence(
                    conn,
                    {
                        "kind": "runner",
                        "target": "timeout",
                        "command": args.agent_command,
                        "result": "fail",
                        "story_id": args.id,
                        "notes": f"command timed out after {args.timeout} seconds",
                    },
                )
            )

    evidence_text = ",".join(str(item) for item in evidence_ids)
    story_status = "completed" if status == "completed" else "failed"
    trace_outcome = "completed" if status == "completed" else "failed"
    with connect() as conn:
        conn.execute(
            """
            UPDATE story
            SET status = ?, evidence = ?, updated_at = datetime('now'), revision = revision + 1
            WHERE id = ?
            """,
            (story_status, evidence_text, args.id),
        )
        conn.execute(
            """
            UPDATE agent_run
            SET status = ?, completed_at = datetime('now'), agent_exit_code = ?,
                verify_exit_code = ?, evidence_ids = ?, log_dir = ?
            WHERE id = ?
            """,
            (status, agent_exit, verify_exit, evidence_text, log_dir, run_id),
        )
        conn.execute(
            """
            INSERT INTO trace (summary, outcome, intake_id, story_id, evidence_ids, files_changed, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (args.summary, trace_outcome, intake_id, args.id, evidence_text, args.changed, args.notes),
        )
    emit(
        {
            "run_id": run_id,
            "intake_id": intake_id,
            "story_id": args.id,
            "lane": lane,
            "status": status,
            "agent_exit_code": agent_exit,
            "verify_exit_code": verify_exit,
            "evidence_ids": evidence_ids,
            "log_dir": log_dir,
        },
        args.json,
    )


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
    parser = argparse.ArgumentParser(prog="harness", description="my-harness CLI")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="initialize SQLite state")
    init.set_defaults(func=cmd_init)

    check = sub.add_parser("check", help="run standard harness checks")
    check.add_argument("--timeout", type=int, default=60)
    check.add_argument("--include-active", action="store_true")
    check.add_argument("--strict-active", action="store_true")
    check.set_defaults(func=cmd_check)

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

    adapter = sub.add_parser("adapter", help="agent adapter commands")
    adapter_sub = adapter.add_subparsers(dest="adapter_command", required=True)
    adapter_register = adapter_sub.add_parser("register", help="register or update an agent adapter")
    adapter_register.add_argument("--id", required=True)
    adapter_register.add_argument("--provider", required=True)
    adapter_register.add_argument("--command-template", required=True)
    adapter_register.add_argument("--availability", default="unknown")
    adapter_register.add_argument("--trust", default="project_declared")
    adapter_register.add_argument("--executable")
    adapter_register.add_argument("--version-command")
    adapter_register.add_argument("--notes")
    adapter_register.set_defaults(func=cmd_adapter_register)
    adapter_preset = adapter_sub.add_parser("preset", help="install or list adapter presets")
    adapter_preset.add_argument("name", help="preset name, 'all', or 'list'")
    adapter_preset.set_defaults(func=cmd_adapter_preset)
    adapter_discover = adapter_sub.add_parser("discover", help="discover adapter executable availability")
    adapter_discover.add_argument("--adapter")
    adapter_discover.add_argument("--timeout", type=int, default=20)
    adapter_discover.set_defaults(func=cmd_adapter_discover)
    adapter_list = adapter_sub.add_parser("list", help="list registered adapters")
    adapter_list.add_argument("--limit", type=int, default=20)
    adapter_list.set_defaults(func=cmd_adapter_list)
    adapter_run = adapter_sub.add_parser("run", help="run a task through a registered adapter")
    adapter_run.add_argument("--adapter", required=True)
    adapter_run.add_argument("--id", required=True)
    adapter_run.add_argument("--summary", required=True)
    adapter_run.add_argument("--prompt")
    adapter_run.add_argument("--prompt-file")
    adapter_run.add_argument("--verify-command", required=True)
    adapter_run.add_argument("--intent", default="modify")
    adapter_run.add_argument("--work-type", default="feature")
    adapter_run.add_argument("--scope", default="module")
    adapter_run.add_argument("--uncertainty", default="medium")
    adapter_run.add_argument("--reversibility", default="easy")
    adapter_run.add_argument("--risk", default="medium")
    adapter_run.add_argument("--lane")
    adapter_run.add_argument("--confidence", type=float, default=1.0)
    adapter_run.add_argument("--timeout", type=int, default=1800)
    adapter_run.add_argument("--allow-high-risk", action="store_true")
    adapter_run.add_argument("--allow-unavailable", action="store_true")
    adapter_run.add_argument("--allow-raw-prompt", action="store_true")
    adapter_run.add_argument("--changed")
    adapter_run.add_argument("--notes")
    adapter_run.set_defaults(func=cmd_adapter_run)

    run = sub.add_parser("run", help="runner commands")
    run_sub = run.add_subparsers(dest="run_command", required=True)
    run_once = run_sub.add_parser("once", help="run one orchestrated task")
    run_once.add_argument("--id", required=True)
    run_once.add_argument("--summary", required=True)
    run_once.add_argument("--agent-command", required=True)
    run_once.add_argument("--verify-command", required=True)
    run_once.add_argument("--intent", default="modify")
    run_once.add_argument("--work-type", default="feature")
    run_once.add_argument("--scope", default="module")
    run_once.add_argument("--uncertainty", default="medium")
    run_once.add_argument("--reversibility", default="easy")
    run_once.add_argument("--risk", default="medium")
    run_once.add_argument("--lane")
    run_once.add_argument("--confidence", type=float, default=1.0)
    run_once.add_argument("--timeout", type=int, default=1800)
    run_once.add_argument("--allow-high-risk", action="store_true")
    run_once.add_argument("--changed")
    run_once.add_argument("--notes")
    run_once.set_defaults(func=cmd_run_once)

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
        ("runs", "agent_run"),
        ("adapters", "agent_adapter"),
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
