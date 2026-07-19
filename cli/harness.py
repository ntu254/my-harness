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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(os.environ.get("MY_HARNESS_WORKSPACE", PACKAGE_ROOT)).resolve()
ROOT = PACKAGE_ROOT
DEFAULT_DB = WORKSPACE_ROOT / "harness" / "harness.db"
SCHEMA_DIR = PACKAGE_ROOT / "state" / "schema"


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
COMMAND_MODES = {"shell", "argv"}
VERIFICATION_MODES = {"shell", "argv", "native"}
HUMAN_GATE_STATUSES = {"pending", "approved", "rejected", "cancelled"}
COMPLETION_STATUSES = {"pass", "blocked", "weak"}

SKILL_REGISTRY = PACKAGE_ROOT / "harness" / "skills.json"
BENCHMARK_REGISTRY = PACKAGE_ROOT / "harness" / "benchmarks.json"

ADAPTER_PRESETS: dict[str, dict[str, str]] = {
    "mock-python": {
        "id": "mock-python",
        "provider": "mock",
        "command_template": "python --version",
        "command_mode": "argv",
        "command_argv_json": json.dumps(["python", "--version"]),
        "availability": "present",
        "trust_level": "verified_local",
        "executable": "python",
        "version_command": "python --version",
        "notes": "Local smoke adapter that never sends prompts to an external model.",
        "capabilities_json": json.dumps(["echo", "demo"]),
        "max_prompt_length": "1000000",
        "supports_raw_prompt": "True",
        "supports_templates": "True",
        "supports_argv": "True",
        "verification_mode": "argv",
    },
    "codex-local": {
        "id": "codex-local",
        "provider": "codex",
        "command_template": "codex exec --prompt-file {prompt_file_shell}",
        "command_mode": "argv",
        "command_argv_json": json.dumps(["codex", "exec", "--prompt-file", "{prompt_file}"]),
        "availability": "unknown",
        "trust_level": "user_declared",
        "executable": "codex",
        "version_command": "codex --version",
        "notes": "Codex CLI preset. Verify locally before use; flags may vary by installed version.",
        "capabilities_json": json.dumps(["code-generation", "code-analysis", "refactor"]),
        "max_prompt_length": "4000",
        "supports_raw_prompt": "False",
        "supports_templates": "True",
        "supports_argv": "True",
        "verification_mode": "argv",
    },
    "claude-local": {
        "id": "claude-local",
        "provider": "claude",
        "command_template": "claude -p {prompt_shell}",
        "command_mode": "argv",
        "command_argv_json": json.dumps(["claude", "-p", "{prompt}"]),
        "availability": "unknown",
        "trust_level": "user_declared",
        "executable": "claude",
        "version_command": "claude --version",
        "notes": "Claude CLI preset. Verify locally before use; flags may vary by installed version.",
        "capabilities_json": json.dumps(["code-generation", "code-analysis", "refactor", "review"]),
        "max_prompt_length": "100000",
        "supports_raw_prompt": "False",
        "supports_templates": "True",
        "supports_argv": "True",
        "verification_mode": "argv",
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


def relative_text(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def resolve_resource_or_workspace_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    workspace_path = WORKSPACE_ROOT / path
    if workspace_path.exists():
        return workspace_path
    return PACKAGE_ROOT / path


def git_head() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=WORKSPACE_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None


def git_dirty_files() -> str:
    try:
        output = subprocess.check_output(
            ["git", "status", "--short"],
            cwd=WORKSPACE_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return json.dumps([line.strip() for line in output.splitlines() if line.strip()])
    except Exception:
        return "[]"


def utc_now_text() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def utc_after_minutes(minutes: int) -> str:
    return (datetime.utcnow() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")


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


def run_command(command: str, timeout: int, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd or WORKSPACE_ROOT,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_argv(argv: list[str], timeout: int, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd or WORKSPACE_ROOT,
        shell=False,
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


def render_argv_template(argv_json: str, values: dict[str, str]) -> list[str]:
    try:
        raw = json.loads(argv_json)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid command argv JSON: {exc}") from exc
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise SystemExit("command argv JSON must be a JSON array of strings")
    return [render_template(item, values) for item in raw]


def read_json_file(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON file {path}: {exc}") from exc


def normalize_csv(values: list[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        for item in value.split(","):
            item = item.strip()
            if item and item not in result:
                result.append(item)
    return result


def load_skills() -> list[dict[str, Any]]:
    data = read_json_file(SKILL_REGISTRY, {"skills": []})
    skills = data.get("skills", []) if isinstance(data, dict) else []
    if not isinstance(skills, list):
        raise SystemExit("harness/skills.json must contain a skills array")
    return [item for item in skills if isinstance(item, dict) and item.get("id")]


def skills_by_id() -> dict[str, dict[str, Any]]:
    return {str(skill["id"]): skill for skill in load_skills()}


def choose_workflow(lane: str, intent: str, work_type: str, tags: list[str]) -> str:
    tag_set = set(tags)
    if lane == "approval_required":
        return "approval-first"
    if lane == "high_risk":
        return "plan-gated"
    if "ui" in tag_set or "frontend" in tag_set or "design" in tag_set:
        return "design-quality-slice"
    if work_type in {"bugfix", "incident"}:
        return "debug-regression-loop"
    if intent in {"read", "analyze", "plan"}:
        return "analysis-only"
    if lane == "tiny":
        return "tiny-change"
    return "spec-code-verify"


def choose_skill_ids(lane: str, intent: str, work_type: str, scope: str, tags: list[str]) -> list[str]:
    tag_set = set(tags)
    selected: list[str] = []

    def add(skill_id: str) -> None:
        if skill_id not in selected:
            selected.append(skill_id)

    if lane == "tiny":
        add("tiny-change")
    elif work_type in {"bugfix", "incident"}:
        add("systematic-debugging")
        add("regression-proof")
    elif work_type in {"migration", "release"}:
        add("spec-clarification")
    elif intent in {"read", "analyze", "plan"}:
        add("spec-clarification")
    else:
        add("normal-feature")

    if work_type in {"feature", "migration", "release", "harness_improvement"} and scope != "file":
        add("spec-clarification")
        add("artifact-lifecycle")
    if intent in {"modify", "execute"} or work_type in {"refactor", "maintenance", "harness_improvement"}:
        add("code-quality-review")
    if {"ui", "frontend", "design", "accessibility"} & tag_set:
        add("design-quality-review")
    if lane in {"high_risk", "approval_required"}:
        add("high-risk-plan")
    if work_type in {"migration", "release"}:
        add("release-readiness")
    if lane == "approval_required":
        add("human-gate")
    return selected


def capability_plan_for(
    skill_ids: list[str],
    extra_required: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    registry = skills_by_id()
    required: list[str] = []
    optional: list[str] = []
    for skill_id in skill_ids:
        for capability in registry.get(skill_id, {}).get("required_capabilities", []):
            if capability not in required:
                required.append(capability)
        for capability in registry.get(skill_id, {}).get("optional_capabilities", []):
            if capability not in required and capability not in optional:
                optional.append(capability)
    for capability in extra_required or []:
        if capability not in required:
            required.append(capability)
        if capability in optional:
            optional.remove(capability)
    optional = [capability for capability in optional if capability not in required]
    return required, optional


def required_capabilities_for(skill_ids: list[str], extra: list[str] | None = None) -> list[str]:
    required, _ = capability_plan_for(skill_ids, extra)
    return required


def available_tools(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, capability, command, availability, trust_level, notes
        FROM tool
        ORDER BY capability, id
        """
    ).fetchall()
    tools = [row_dict(row) for row in rows]
    adapters = conn.execute(
        """
        SELECT id, provider, capabilities_json, availability, trust_level
        FROM agent_adapter
        ORDER BY id
        """
    ).fetchall()
    for row in adapters:
        try:
            capabilities = json.loads(row["capabilities_json"] or "[]")
        except json.JSONDecodeError:
            capabilities = []
        for capability in capabilities:
            tools.append(
                {
                    "id": row["id"],
                    "capability": capability,
                    "command": f"agent-adapter:{row['provider']}",
                    "availability": row["availability"],
                    "trust_level": row["trust_level"],
                    "notes": "adapter capability",
                }
            )
    return tools


def build_route_decision(args: argparse.Namespace, persist: bool = False) -> dict[str, Any]:
    ensure_db()
    intent = validate_choice(args.intent, INTENTS, "intent")
    work_type = validate_choice(args.work_type, WORK_TYPES, "work-type")
    scope = validate_choice(args.scope, SCOPES, "scope")
    uncertainty = validate_choice(args.uncertainty, UNCERTAINTY, "uncertainty")
    reversibility = validate_choice(args.reversibility, REVERSIBILITY, "reversibility")
    risk = validate_choice(args.risk, RISKS, "risk")
    lane = args.lane or classify_lane(work_type, scope, uncertainty, reversibility, risk)
    lane = validate_choice(lane, LANES, "lane")
    tags = normalize_csv(getattr(args, "tag", None))
    explicit_capabilities = normalize_csv(getattr(args, "requires", None))
    skill_ids = choose_skill_ids(lane, intent, work_type, scope, tags)
    required, optional = capability_plan_for(skill_ids, explicit_capabilities)
    all_capabilities = required + [capability for capability in optional if capability not in required]
    with connect() as conn:
        tools = available_tools(conn)
        present_capabilities = {
            tool["capability"]
            for tool in tools
            if tool.get("availability") == "present"
        }
        missing_required = [capability for capability in required if capability not in present_capabilities]
        missing_optional = [capability for capability in optional if capability not in present_capabilities]
        missing = missing_required + [capability for capability in missing_optional if capability not in missing_required]
        available = [
            tool for tool in tools if tool.get("capability") in all_capabilities and tool.get("availability") == "present"
        ]
        candidates = [
            tool
            for tool in tools
            if tool.get("capability") in all_capabilities and tool.get("availability") in {"unknown", "missing"}
        ]
        proof_policy = "pass"
        if lane == "approval_required" or missing_required:
            proof_policy = "block"
        elif missing_optional:
            proof_policy = "warn"
        decision = {
            "summary": args.summary,
            "lane": lane,
            "workflow": choose_workflow(lane, intent, work_type, tags),
            "skills": skill_ids,
            "required_capabilities": required,
            "optional_capabilities": optional,
            "available_tools": available,
            "candidate_tools": candidates,
            "missing_capabilities": missing,
            "missing_required_capabilities": missing_required,
            "missing_optional_capabilities": missing_optional,
            "proof_policy": proof_policy,
            "weak_proof": bool(missing_optional),
            "human_gate_required": lane == "approval_required",
            "rationale": {
                "intent": intent,
                "work_type": work_type,
                "scope": scope,
                "uncertainty": uncertainty,
                "reversibility": reversibility,
                "risk": risk,
                "tags": tags,
            },
        }
        if persist:
            cur = conn.execute(
                """
                INSERT INTO route_decision
                  (summary, intent, work_type, scope, uncertainty, reversibility, risk, lane,
                   workflow, skills_json, required_capabilities_json, available_tools_json,
                   missing_capabilities_json, proof_policy, human_gate_required, rationale_json,
                   optional_capabilities_json, missing_required_capabilities_json,
                   missing_optional_capabilities_json, candidate_tools_json)
                VALUES
                  (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    args.summary,
                    intent,
                    work_type,
                    scope,
                    uncertainty,
                    reversibility,
                    risk,
                    lane,
                    decision["workflow"],
                    json.dumps(skill_ids, ensure_ascii=False),
                    json.dumps(required, ensure_ascii=False),
                    json.dumps(available, ensure_ascii=False),
                    json.dumps(missing, ensure_ascii=False),
                    proof_policy,
                    int(decision["human_gate_required"]),
                    json.dumps(decision["rationale"], ensure_ascii=False),
                    json.dumps(optional, ensure_ascii=False),
                    json.dumps(missing_required, ensure_ascii=False),
                    json.dumps(missing_optional, ensure_ascii=False),
                    json.dumps(candidates, ensure_ascii=False),
                ),
            )
            decision["route_id"] = cur.lastrowid
    return decision


def prompt_dir() -> Path:
    path = WORKSPACE_ROOT / "harness" / "prompts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_prompt_file(story_id: str, prompt: str) -> str:
    path = prompt_dir() / f"{sanitize_name(story_id)}.prompt.txt"
    path.write_text(prompt, encoding="utf-8")
    return relative_text(path, WORKSPACE_ROOT)


def read_prompt(args: argparse.Namespace) -> tuple[str, str | None]:
    sources = [bool(args.prompt), bool(args.prompt_file), bool(getattr(args, "prompt_template", None))]
    if sum(sources) > 1:
        raise SystemExit("use only one of --prompt, --prompt-file, or --prompt-template")
    if getattr(args, "prompt_template", None):
        path = resolve_resource_or_workspace_path(args.prompt_template)
        if not path.exists():
            raise SystemExit(f"prompt template not found: {path}")
        prompt = path.read_text(encoding="utf-8")
        for key, value in parse_prompt_vars(getattr(args, "prompt_vars", []) or []).items():
            prompt = prompt.replace("{{" + key + "}}", value)
        return prompt, None
    if args.prompt_file:
        path = resolve_resource_or_workspace_path(args.prompt_file)
        if not path.exists():
            raise SystemExit(f"prompt file not found: {path}")
        return path.read_text(encoding="utf-8"), relative_text(path, WORKSPACE_ROOT)
    if args.prompt:
        return args.prompt, None
    raise SystemExit("adapter run requires --prompt or --prompt-file")


def parse_prompt_vars(items: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"invalid --var value, expected key=value: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit(f"invalid --var key: {item}")
        values[key] = value
    return values


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
    log_dir = WORKSPACE_ROOT / "harness" / "runs" / f"{sanitize_name(story_id)}-{run_id}"
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
    return relative_text(log_path, WORKSPACE_ROOT)


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


def parse_json_list(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def story_evidence_rows(conn: sqlite3.Connection, story: sqlite3.Row) -> list[sqlite3.Row]:
    evidence_ids: list[int] = []
    for item in (story["evidence"] or "").split(","):
        item = item.strip()
        if item.isdigit():
            evidence_ids.append(int(item))
    rows_by_id: dict[int, sqlite3.Row] = {}
    if evidence_ids:
        placeholders = ",".join("?" for _ in evidence_ids)
        for row in conn.execute(f"SELECT * FROM evidence WHERE id IN ({placeholders})", tuple(evidence_ids)).fetchall():
            rows_by_id[int(row["id"])] = row
    for row in conn.execute("SELECT * FROM evidence WHERE story_id = ?", (story["id"],)).fetchall():
        rows_by_id[int(row["id"])] = row
    return [rows_by_id[key] for key in sorted(rows_by_id)]


def stale_evidence(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    current_head = git_head()
    current_dirty = git_dirty_files()
    stale: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        if row["git_head"] and current_head and row["git_head"] != current_head:
            reasons.append("git_head_changed")
        if row["dirty_files"] != current_dirty:
            reasons.append("dirty_state_changed")
        if reasons:
            stale.append(
                {
                    "id": row["id"],
                    "kind": row["kind"],
                    "target": row["target"],
                    "reasons": reasons,
                    "evidence_git_head": row["git_head"],
                    "current_git_head": current_head,
                }
            )
    return stale


def approval_validity(
    conn: sqlite3.Connection,
    approval_id: int | None,
    scope_ref: str | None,
    require_approval: bool = False,
) -> dict[str, Any]:
    if approval_id is None:
        return {
            "valid": not require_approval,
            "status": "not_required" if not require_approval else "missing",
            "reason": None if not require_approval else "approval_required",
        }
    row = conn.execute("SELECT * FROM human_gate WHERE id = ?", (approval_id,)).fetchone()
    if row is None:
        return {"valid": False, "status": "missing", "reason": "approval_not_found"}
    if row["status"] != "approved":
        return {"valid": False, "status": row["status"], "reason": "approval_not_approved"}
    if row["expires_at"] and row["expires_at"] <= utc_now_text():
        return {"valid": False, "status": "expired", "reason": "approval_expired"}
    if row["scope_ref"] and scope_ref and row["scope_ref"] != scope_ref:
        return {
            "valid": False,
            "status": "scope_mismatch",
            "reason": f"expected {row['scope_ref']} got {scope_ref}",
        }
    if row["scope_ref"] and not scope_ref:
        return {"valid": False, "status": "scope_missing", "reason": "approval_scope_required"}
    return {
        "valid": True,
        "status": "approved",
        "reason": None,
        "scope_ref": row["scope_ref"],
        "expires_at": row["expires_at"],
    }


def route_gate_payload(conn: sqlite3.Connection, route_id: int | None) -> dict[str, Any]:
    if route_id is None:
        return {
            "route_id": None,
            "missing_required_capabilities": [],
            "missing_optional_capabilities": [],
            "proof_policy": "unknown",
        }
    row = conn.execute("SELECT * FROM route_decision WHERE id = ?", (route_id,)).fetchone()
    if row is None:
        raise SystemExit(f"route decision not found: {route_id}")
    keys = set(row.keys())
    missing_required = (
        parse_json_list(row["missing_required_capabilities_json"])
        if "missing_required_capabilities_json" in keys
        else parse_json_list(row["missing_capabilities_json"])
    )
    missing_optional = (
        parse_json_list(row["missing_optional_capabilities_json"])
        if "missing_optional_capabilities_json" in keys
        else []
    )
    return {
        "route_id": route_id,
        "lane": row["lane"],
        "workflow": row["workflow"],
        "proof_policy": row["proof_policy"],
        "missing_required_capabilities": missing_required,
        "missing_optional_capabilities": missing_optional,
        "skills": parse_json_list(row["skills_json"]),
    }


def build_final_report(args: argparse.Namespace, persist: bool = False) -> dict[str, Any]:
    ensure_db()
    with connect() as conn:
        story = conn.execute("SELECT * FROM story WHERE id = ?", (args.story,)).fetchone()
        if story is None:
            raise SystemExit(f"story not found: {args.story}")
        evidence_rows = story_evidence_rows(conn, story)
        evidence = [row_dict(row) for row in evidence_rows]
        stale = stale_evidence(evidence_rows)
        route_payload = route_gate_payload(conn, getattr(args, "route_id", None))
        approval_required = story["lane"] == "approval_required" or route_payload.get("lane") == "approval_required"
        approval = approval_validity(
            conn,
            getattr(args, "approval_id", None),
            getattr(args, "scope", None) or story["id"],
            require_approval=approval_required,
        )
        blockers: list[str] = []
        warnings: list[str] = []
        if not evidence_rows:
            blockers.append("missing_evidence")
        if stale and not getattr(args, "allow_stale_evidence", False):
            blockers.append("stale_evidence")
        if route_payload["missing_required_capabilities"]:
            blockers.append("missing_required_capabilities")
        if approval_required and not approval["valid"]:
            blockers.append("approval_not_valid")
        if route_payload["missing_optional_capabilities"]:
            warnings.append("missing_optional_capabilities")
        skipped_checks = normalize_csv(getattr(args, "skipped_check", []) or [])
        if skipped_checks:
            warnings.append("skipped_checks")
        status = "pass"
        if blockers:
            status = "blocked"
        elif warnings:
            status = "weak"
        report = {
            "story": {
                "id": story["id"],
                "title": story["title"],
                "lane": story["lane"],
                "status": story["status"],
                "revision": story["revision"],
            },
            "status": status,
            "blockers": blockers,
            "warnings": warnings,
            "route": route_payload,
            "approval": approval,
            "evidence_ids": [row["id"] for row in evidence],
            "stale_evidence": stale,
            "skipped_checks": skipped_checks,
            "residual_risk": getattr(args, "residual_risk", None),
            "rollback_info": getattr(args, "rollback", None),
            "git_head": git_head(),
            "dirty_files": parse_json_list(git_dirty_files()),
        }
        if persist:
            cur = conn.execute(
                """
                INSERT INTO completion_report
                  (story_id, route_id, approval_id, status, evidence_ids, stale_evidence_json,
                   missing_required_capabilities_json, missing_optional_capabilities_json,
                   approval_status, skipped_checks_json, residual_risk, rollback_info, report_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    story["id"],
                    route_payload["route_id"],
                    getattr(args, "approval_id", None),
                    status,
                    json.dumps(report["evidence_ids"], ensure_ascii=False),
                    json.dumps(stale, ensure_ascii=False),
                    json.dumps(route_payload["missing_required_capabilities"], ensure_ascii=False),
                    json.dumps(route_payload["missing_optional_capabilities"], ensure_ascii=False),
                    approval["status"],
                    json.dumps(skipped_checks, ensure_ascii=False),
                    getattr(args, "residual_risk", None),
                    getattr(args, "rollback", None),
                    json.dumps(report, ensure_ascii=False),
                ),
            )
            report["completion_report_id"] = cur.lastrowid
    return report


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
        "state/schema/004-argv-and-prompt-templates.sql",
        "state/schema/005-adapter-capabilities.sql",
        "state/schema/006-routing-alignment.sql",
        "state/schema/007-core-gates.sql",
        "harness/skills.json",
        "harness/benchmarks.json",
        "schemas/skill.schema.json",
        "schemas/benchmark.schema.json",
        "schemas/route-decision.schema.json",
        "schemas/final-report.schema.json",
        "tests/test_cli_contracts.py",
        "tests/test_professional_review_contracts.py",
        "ANALYSIS_CROSS_REPO_IDEAS.md",
        "docs/INDEX.md",
        "docs/CONTRACTS.md",
        "docs/RELEASE_INSTALL.md",
        "docs/HARNESS_ENGINEERING_ADOPTION.md",
        "docs/decisions/ADR-001-state-store.md",
        "docs/GATES.md",
        "templates/prompts/adapter-smoke.md",
        "package.json",
        "bin/my-harness.js",
    ]
    return [
        {
            "name": f"file:{path}",
            "status": "pass" if (ROOT / path).exists() else "fail",
            "detail": path,
        }
        for path in required
    ]


def check_command(name: str, command: str, timeout: int = 60, cwd: Path | None = None) -> dict[str, Any]:
    try:
        result = run_command(command, timeout, cwd=cwd)
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
            check_command("features.json parses", "python -m json.tool harness/features.json", args.timeout, cwd=PACKAGE_ROOT),
            check_command("skills.json parses", "python -m json.tool harness/skills.json", args.timeout, cwd=PACKAGE_ROOT),
            check_command("benchmarks.json parses", "python -m json.tool harness/benchmarks.json", args.timeout, cwd=PACKAGE_ROOT),
            check_command("skill schema parses", "python -m json.tool schemas/skill.schema.json", args.timeout, cwd=PACKAGE_ROOT),
            check_command("benchmark schema parses", "python -m json.tool schemas/benchmark.schema.json", args.timeout, cwd=PACKAGE_ROOT),
            check_command("route schema parses", "python -m json.tool schemas/route-decision.schema.json", args.timeout, cwd=PACKAGE_ROOT),
            check_command("final report schema parses", "python -m json.tool schemas/final-report.schema.json", args.timeout, cwd=PACKAGE_ROOT),
            check_command("cli compiles", "python -m py_compile cli/harness.py", args.timeout, cwd=PACKAGE_ROOT),
            check_command("cli contract tests", 'python -m unittest discover -s tests -p "test_*.py"', args.timeout, cwd=PACKAGE_ROOT),
            check_command("package.json parses", "python -m json.tool package.json", args.timeout, cwd=PACKAGE_ROOT),
            check_command("npm launcher syntax", "node --check bin/my-harness.js", args.timeout, cwd=PACKAGE_ROOT),
            check_command("git diff whitespace", "git diff --check", args.timeout, cwd=WORKSPACE_ROOT),
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
    capabilities_json = getattr(args, "capabilities", None) or "[]"
    if isinstance(capabilities_json, str):
        if not capabilities_json.startswith("["):
            capabilities_json = json.dumps([c.strip() for c in capabilities_json.split(",")])
    else:
        capabilities_json = json.dumps(capabilities_json)

    values = {
        "id": args.id,
        "provider": args.provider,
        "command_template": args.command_template,
        "command_mode": validate_choice(args.command_mode, COMMAND_MODES, "command-mode"),
        "command_argv_json": args.command_argv_json,
        "availability": validate_choice(args.availability, ADAPTER_AVAILABILITY, "availability"),
        "trust_level": validate_choice(args.trust, ADAPTER_TRUST, "trust"),
        "executable": args.executable,
        "version_command": args.version_command,
        "notes": args.notes,
        "capabilities_json": capabilities_json,
        "max_prompt_length": getattr(args, "max_prompt_length", 100000),
        "supports_raw_prompt": getattr(args, "supports_raw_prompt", False),
        "supports_templates": getattr(args, "supports_templates", True),
        "supports_argv": getattr(args, "supports_argv", True),
        "verification_mode": validate_choice(
            getattr(args, "verification_mode", "shell"), VERIFICATION_MODES, "verification-mode"
        ),
    }
    if values["command_mode"] == "argv" and not values["command_argv_json"]:
        raise SystemExit("--command-argv-json is required when --command-mode argv")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO agent_adapter
              (id, provider, command_template, availability, trust_level,
               executable, version_command, command_mode, command_argv_json, notes,
               capabilities_json, max_prompt_length, supports_raw_prompt, supports_templates,
               supports_argv, verification_mode)
            VALUES
              (:id, :provider, :command_template, :availability, :trust_level,
               :executable, :version_command, :command_mode, :command_argv_json, :notes,
               :capabilities_json, :max_prompt_length, :supports_raw_prompt, :supports_templates,
               :supports_argv, :verification_mode)
            ON CONFLICT(id) DO UPDATE SET
              provider = excluded.provider,
              command_template = excluded.command_template,
              availability = excluded.availability,
              trust_level = excluded.trust_level,
              executable = excluded.executable,
              version_command = excluded.version_command,
              command_mode = excluded.command_mode,
              command_argv_json = excluded.command_argv_json,
              notes = excluded.notes,
              capabilities_json = excluded.capabilities_json,
              max_prompt_length = excluded.max_prompt_length,
              supports_raw_prompt = excluded.supports_raw_prompt,
              supports_templates = excluded.supports_templates,
              supports_argv = excluded.supports_argv,
              verification_mode = excluded.verification_mode
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
    ensure_defaults = {
        "capabilities_json": values.get("capabilities_json", "[]"),
        "max_prompt_length": int(values.get("max_prompt_length", 100000)),
        "supports_raw_prompt": str(values.get("supports_raw_prompt", "False")) in ("True", "true", "1"),
        "supports_templates": str(values.get("supports_templates", "True")) in ("True", "true", "1"),
        "supports_argv": str(values.get("supports_argv", "True")) in ("True", "true", "1"),
        "verification_mode": values.get("verification_mode", "shell"),
    }
    values.update(ensure_defaults)

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO agent_adapter
              (id, provider, command_template, availability, trust_level,
               executable, version_command, command_mode, command_argv_json, notes,
               capabilities_json, max_prompt_length, supports_raw_prompt, supports_templates,
               supports_argv, verification_mode)
            VALUES
              (:id, :provider, :command_template, :availability, :trust_level,
               :executable, :version_command, :command_mode, :command_argv_json, :notes,
               :capabilities_json, :max_prompt_length, :supports_raw_prompt, :supports_templates,
               :supports_argv, :verification_mode)
            ON CONFLICT(id) DO UPDATE SET
              provider = excluded.provider,
              command_template = excluded.command_template,
              availability = excluded.availability,
              trust_level = excluded.trust_level,
              executable = excluded.executable,
              version_command = excluded.version_command,
              command_mode = excluded.command_mode,
              command_argv_json = excluded.command_argv_json,
              notes = excluded.notes,
              capabilities_json = excluded.capabilities_json,
              max_prompt_length = excluded.max_prompt_length,
              supports_raw_prompt = excluded.supports_raw_prompt,
              supports_templates = excluded.supports_templates,
              supports_argv = excluded.supports_argv,
              verification_mode = excluded.verification_mode
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


def cmd_adapter_capability(args: argparse.Namespace) -> None:
    require_db()
    with connect() as conn:
        if args.adapter:
            rows = conn.execute("SELECT * FROM agent_adapter WHERE id = ?", (args.adapter,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM agent_adapter ORDER BY id").fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        row_dict_val = row_dict(row)
        try:
            capabilities = json.loads(row_dict_val.get("capabilities_json") or "[]")
        except json.JSONDecodeError:
            capabilities = []
        results.append(
            {
                "adapter_id": row_dict_val["id"],
                "provider": row_dict_val["provider"],
                "capabilities": capabilities,
                "max_prompt_length": row_dict_val.get("max_prompt_length", 100000),
                "supports_raw_prompt": bool(row_dict_val.get("supports_raw_prompt")),
                "supports_templates": bool(row_dict_val.get("supports_templates")),
                "supports_argv": bool(row_dict_val.get("supports_argv")),
                "verification_mode": row_dict_val.get("verification_mode", "shell"),
                "trust_level": row_dict_val["trust_level"],
                "availability": row_dict_val["availability"],
            }
        )
    emit(results, args.json)


def register_tool_values(values: dict[str, Any]) -> None:
    values["availability"] = validate_choice(values["availability"], ADAPTER_AVAILABILITY, "availability")
    values["trust_level"] = validate_choice(values["trust_level"], ADAPTER_TRUST, "trust")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO tool (id, capability, command, availability, trust_level, notes)
            VALUES (:id, :capability, :command, :availability, :trust_level, :notes)
            ON CONFLICT(id) DO UPDATE SET
              capability = excluded.capability,
              command = excluded.command,
              availability = excluded.availability,
              trust_level = excluded.trust_level,
              notes = excluded.notes
            """,
            values,
        )


def cmd_tool_register(args: argparse.Namespace) -> None:
    ensure_db()
    values = {
        "id": args.id,
        "capability": args.capability,
        "command": args.command,
        "availability": args.availability,
        "trust_level": args.trust,
        "notes": args.notes,
    }
    register_tool_values(values)
    emit(values, args.json)


def cmd_tool_seed(args: argparse.Namespace) -> None:
    ensure_db()
    executable_tools = [
        ("rg", "code-search", "rg", "rg --files", "Fast repository search."),
        ("python", "fast-check", "python", "python -m py_compile cli/harness.py", "Local Python smoke checks."),
        ("harness-pycompile", "test-runner", "python", "python -m py_compile cli/harness.py", "Built-in harness test runner."),
        ("git", "change-trace", "git", "git status --short", "Local change and history inspection."),
        ("pytest", "test-runner", "pytest", "pytest", "Python test runner when available."),
    ]
    seeded: list[dict[str, Any]] = []
    for tool_id, capability, executable, command, notes in executable_tools:
        availability, detail = discover_executable(executable)
        values = {
            "id": tool_id,
            "capability": capability,
            "command": command,
            "availability": availability,
            "trust_level": "verified_local" if availability == "present" else "project_declared",
            "notes": f"{notes} Discovery: {detail}",
        }
        register_tool_values(values)
        seeded.append(values)

    manual_tools = [
        ("manual-spec-review", "spec-analysis", "manual:spec-review", "present", "Spec and requirement review checklist."),
        ("manual-code-review", "code-review", "manual:code-review", "present", "Senior code review checklist."),
        ("manual-impact-analysis", "impact-analysis", "manual:impact-analysis", "present", "Blast-radius and dependency analysis."),
        ("manual-rollback-plan", "rollback-plan", "manual:rollback-plan", "present", "Rollback and recovery planning."),
        ("manual-human-approval", "human-approval", "manual:human-approval", "present", "Explicit approval record for risky work."),
        ("harness-bench", "benchmark-runner", "harness bench run", "present", "Local route benchmark harness."),
        ("manual-static-analysis", "static-analysis", "manual:static-analysis", "present", "Maintainability and quality rubric."),
        ("manual-diagnostic-logs", "diagnostic-logs", "manual:diagnostic-logs", "present", "Collect and inspect logs or repro output."),
        ("manual-log-viewer", "log-viewer", "manual:log-viewer", "present", "Inspect local logs and command output."),
        ("manual-perf-check", "performance-check", "manual:performance-check", "unknown", "Performance check when relevant."),
        ("manual-browser-check", "browser-check", "manual:browser-check", "unknown", "Browser/UI verification when a UI exists."),
        ("manual-accessibility-check", "accessibility-check", "manual:accessibility-check", "unknown", "Accessibility review when a UI exists."),
        ("manual-visual-review", "visual-review", "manual:visual-review", "unknown", "Visual QA evidence when a UI exists."),
        ("manual-artifact-contract-check", "artifact-contract-check", "manual:artifact-contract-check", "unknown", "Validate spec/plan artifact contracts when enabled."),
        ("manual-documentation-check", "documentation-check", "manual:documentation-check", "present", "Check durable docs and indexes for workflow changes."),
        ("manual-post-release-check", "post-release-check", "manual:post-release-check", "unknown", "Post-release verification checklist when release work exists."),
        ("manual-monitoring-check", "monitoring-check", "manual:monitoring-check", "unknown", "Monitoring or health verification when operational work exists."),
    ]
    for tool_id, capability, command, availability, notes in manual_tools:
        values = {
            "id": tool_id,
            "capability": capability,
            "command": command,
            "availability": availability,
            "trust_level": "project_declared",
            "notes": notes,
        }
        register_tool_values(values)
        seeded.append(values)
    emit(seeded, args.json)


def cmd_route(args: argparse.Namespace) -> None:
    decision = build_route_decision(args, persist=args.persist)
    emit(decision, args.json)


def cmd_approval_request(args: argparse.Namespace) -> None:
    ensure_db()
    if args.ttl_minutes < 0:
        raise SystemExit("--ttl-minutes must be zero or positive")
    values = {
        "story_id": args.story,
        "summary": args.summary,
        "risk": validate_choice(args.risk, RISKS, "risk"),
        "requested_by": args.requested_by,
        "status": "pending",
        "scope_ref": args.scope,
        "expires_at": utc_after_minutes(args.ttl_minutes),
        "notes": args.notes,
    }
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO human_gate (story_id, summary, risk, requested_by, status, scope_ref, expires_at, notes)
            VALUES (:story_id, :summary, :risk, :requested_by, :status, :scope_ref, :expires_at, :notes)
            """,
            values,
        )
        values["id"] = cur.lastrowid
    emit(values, args.json)


def cmd_approval_resolve(args: argparse.Namespace) -> None:
    ensure_db()
    status = validate_choice(args.status, HUMAN_GATE_STATUSES - {"pending"}, "status")
    values = {
        "id": args.id,
        "status": status,
        "resolved_by": args.resolved_by,
        "decision_notes": args.notes,
    }
    with connect() as conn:
        cur = conn.execute(
            """
            UPDATE human_gate
            SET status = :status,
                resolved_by = :resolved_by,
                decision_notes = :decision_notes,
                resolved_at = datetime('now')
            WHERE id = :id AND status = 'pending'
            """,
            values,
        )
        if cur.rowcount != 1:
            raise SystemExit("approval resolve failed: pending gate not found")
        row = conn.execute("SELECT * FROM human_gate WHERE id = ?", (args.id,)).fetchone()
    emit(row_dict(row), args.json)


def cmd_approval_check(args: argparse.Namespace) -> None:
    ensure_db()
    with connect() as conn:
        result = approval_validity(conn, args.id, args.scope, require_approval=True)
    result["id"] = args.id
    result["scope"] = args.scope
    emit(result, args.json)
    if not result["valid"] and args.fail_on_invalid:
        raise SystemExit(1)


def cmd_bench_run(args: argparse.Namespace) -> None:
    ensure_db()
    data = read_json_file(BENCHMARK_REGISTRY, {"cases": []})
    cases = data.get("cases", []) if isinstance(data, dict) else []
    if not isinstance(cases, list) or not cases:
        raise SystemExit("harness/benchmarks.json must contain at least one case")
    results: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        ns = argparse.Namespace(
            summary=case.get("summary", case.get("id", "benchmark case")),
            intent=case.get("intent", "modify"),
            work_type=case.get("work_type", "feature"),
            scope=case.get("scope", "module"),
            uncertainty=case.get("uncertainty", "medium"),
            reversibility=case.get("reversibility", "easy"),
            risk=case.get("risk", "medium"),
            lane=case.get("lane"),
            tag=case.get("tags", []),
            requires=case.get("requires", []),
        )
        decision = build_route_decision(ns, persist=False)
        expected_lane = case.get("expected_lane")
        expected_skills = case.get("expected_skills", [])
        missing_skills = [skill for skill in expected_skills if skill not in decision["skills"]]
        passed = (expected_lane is None or decision["lane"] == expected_lane) and not missing_skills
        results.append(
            {
                "id": case.get("id"),
                "passed": passed,
                "expected_lane": expected_lane,
                "actual_lane": decision["lane"],
                "expected_skills": expected_skills,
                "actual_skills": decision["skills"],
                "missing_expected_skills": missing_skills,
                "missing_capabilities": decision["missing_capabilities"],
            }
        )
    pass_count = sum(1 for item in results if item["passed"])
    fail_count = len(results) - pass_count
    quality_score = round((pass_count / max(1, len(results))) * 100, 2)
    total_skill_count = sum(len(item["actual_skills"]) for item in results)
    process_budget = sum(int(case.get("process_budget", 6)) for case in cases if isinstance(case, dict))
    cost_score = round(max(0, 100 - max(0, total_skill_count - process_budget) * 10), 2)
    adaptiveness_failures = sum(
        1 for item in results if item["expected_lane"] is not None and item["actual_lane"] != item["expected_lane"]
    )
    adaptiveness_score = round(max(0, 100 - adaptiveness_failures * 25), 2)
    required_gap_count = sum(len(item["missing_capabilities"]) for item in results)
    durability_score = round(max(0, 100 - required_gap_count * 5), 2)
    scores = {
        "quality": quality_score,
        "cost": cost_score,
        "adaptiveness": adaptiveness_score,
        "durability": durability_score,
        "total": round((quality_score + cost_score + adaptiveness_score + durability_score) / 4, 2),
        "notes": "v0.9 deterministic controller scores; agent-output scoring remains future work.",
    }
    payload = {
        "suite": data.get("suite", "local-route-benchmark") if isinstance(data, dict) else "local-route-benchmark",
        "pass_count": pass_count,
        "fail_count": fail_count,
        "scores": scores,
        "results": results,
    }
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO benchmark_run (suite, case_count, pass_count, fail_count, result_json, notes, score_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["suite"],
                len(results),
                pass_count,
                fail_count,
                json.dumps(results, ensure_ascii=False),
                args.notes,
                json.dumps(scores, ensure_ascii=False),
            ),
        )
        payload["benchmark_run_id"] = cur.lastrowid
    emit(payload, args.json)
    if fail_count and args.fail_on_regression:
        raise SystemExit(1)


def cmd_report_final(args: argparse.Namespace) -> None:
    report = build_final_report(args, persist=args.persist)
    emit(report, args.json)
    if report["status"] == "blocked" and args.fail_on_blocked:
        raise SystemExit(1)


def cmd_complete(args: argparse.Namespace) -> None:
    report = build_final_report(args, persist=True)
    if report["status"] == "blocked":
        with connect() as conn:
            conn.execute(
                "UPDATE story SET status = 'blocked', updated_at = datetime('now'), revision = revision + 1 WHERE id = ?",
                (args.story,),
            )
        emit(report, args.json)
        raise SystemExit(1)
    if report["status"] == "weak" and not args.allow_weak:
        emit(report, args.json)
        raise SystemExit(1)
    with connect() as conn:
        conn.execute(
            "UPDATE story SET status = 'completed', updated_at = datetime('now'), revision = revision + 1 WHERE id = ?",
            (args.story,),
        )
    report["completed"] = True
    emit(report, args.json)


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
    command_mode = adapter["command_mode"] or "shell"
    command_mode = validate_choice(command_mode, COMMAND_MODES, "command-mode")
    agent_command = render_template(adapter["command_template"], values)
    command_argv: list[str] | None = None
    command_argv_json: str | None = None
    if command_mode == "argv":
        if not adapter["command_argv_json"]:
            raise SystemExit(f"adapter {args.adapter} is argv mode but has no command_argv_json")
        command_argv = render_argv_template(adapter["command_argv_json"], values)
        command_argv_json = json.dumps(command_argv, ensure_ascii=False)
        agent_command = command_argv_json
    if command_mode == "shell" and "{prompt}" in adapter["command_template"] and not args.allow_raw_prompt:
        raise SystemExit("adapter template uses raw {prompt}; use {prompt_shell}, {prompt_file_shell}, or --allow-raw-prompt")
    run_args = argparse.Namespace(
        json=args.json,
        id=args.id,
        summary=args.summary,
        agent_command=agent_command,
        command_mode=command_mode,
        command_argv=command_argv,
        command_argv_json=command_argv_json,
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
        approval_id=args.approval_id,
        approval_scope=args.approval_scope,
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
    command_mode = validate_choice(getattr(args, "command_mode", "shell"), COMMAND_MODES, "command-mode")
    command_argv = getattr(args, "command_argv", None)
    command_argv_json = getattr(args, "command_argv_json", None)
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
               timeout_seconds, adapter_id, prompt, command_mode, command_argv_json, notes)
            VALUES
              (?, ?, ?, 'in_progress', ?, ?, ?, ?, ?, ?, ?, ?)
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
                command_mode,
                command_argv_json,
                args.notes,
            ),
        ).lastrowid

    approval_id = getattr(args, "approval_id", None)
    approval_scope = getattr(args, "approval_scope", None) or args.id
    approval_status: dict[str, Any] | None = None
    if lane in {"high_risk", "approval_required"} and not args.allow_high_risk:
        if approval_id is not None:
            with connect() as conn:
                approval_status = approval_validity(conn, approval_id, approval_scope, require_approval=True)
        if approval_status and approval_status["valid"]:
            pass
        else:
            reason = (
                approval_status["reason"]
                if approval_status
                else "high-risk lane requires --allow-high-risk or a valid --approval-id"
            )
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
                    (reason, run_id),
                )
                conn.execute(
                    """
                    INSERT INTO trace (summary, outcome, intake_id, story_id, friction, notes)
                    VALUES (?, 'blocked', ?, ?, 'needs human approval', ?)
                    """,
                    (args.summary, intake_id, args.id, f"lane={lane}; command not executed; {reason}"),
                )
            emit(
                {
                    "run_id": run_id,
                    "intake_id": intake_id,
                    "story_id": args.id,
                    "lane": lane,
                    "status": "needs_human",
                    "executed": False,
                    "reason": reason,
                    "approval": approval_status,
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
        if command_mode == "argv":
            if not command_argv:
                raise SystemExit("argv command mode requires command argv")
            agent_result = run_argv(command_argv, args.timeout)
        else:
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

    route = sub.add_parser("route", help="classify work and select workflow, skills, and capabilities")
    route.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    route.add_argument("--summary", required=True)
    route.add_argument("--intent", default="modify")
    route.add_argument("--work-type", default="feature")
    route.add_argument("--scope", default="module")
    route.add_argument("--uncertainty", default="medium")
    route.add_argument("--reversibility", default="easy")
    route.add_argument("--risk", default="medium")
    route.add_argument("--lane")
    route.add_argument("--tag", action="append", default=[])
    route.add_argument("--requires", action="append", default=[])
    route.add_argument("--persist", action="store_true")
    route.set_defaults(func=cmd_route)

    report = sub.add_parser("report", help="report commands")
    report_sub = report.add_subparsers(dest="report_command", required=True)
    report_final = report_sub.add_parser("final", help="build a final completion report")
    report_final.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    report_final.add_argument("--story", required=True)
    report_final.add_argument("--route-id", type=int)
    report_final.add_argument("--approval-id", type=int)
    report_final.add_argument("--scope")
    report_final.add_argument("--skipped-check", action="append", default=[])
    report_final.add_argument("--residual-risk")
    report_final.add_argument("--rollback")
    report_final.add_argument("--allow-stale-evidence", action="store_true")
    report_final.add_argument("--persist", action="store_true")
    report_final.add_argument("--fail-on-blocked", action="store_true")
    report_final.set_defaults(func=cmd_report_final)

    complete = sub.add_parser("complete", help="apply completion gates and complete a story")
    complete.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    complete.add_argument("--story", required=True)
    complete.add_argument("--route-id", type=int)
    complete.add_argument("--approval-id", type=int)
    complete.add_argument("--scope")
    complete.add_argument("--skipped-check", action="append", default=[])
    complete.add_argument("--residual-risk")
    complete.add_argument("--rollback")
    complete.add_argument("--allow-stale-evidence", action="store_true")
    complete.add_argument("--allow-weak", action="store_true")
    complete.set_defaults(func=cmd_complete)

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
    adapter_register.add_argument("--command-mode", default="shell")
    adapter_register.add_argument("--command-argv-json")
    adapter_register.add_argument("--availability", default="unknown")
    adapter_register.add_argument("--trust", default="project_declared")
    adapter_register.add_argument("--executable")
    adapter_register.add_argument("--version-command")
    adapter_register.add_argument("--notes")
    adapter_register.add_argument("--capabilities", help="comma-separated list of capabilities or JSON array")
    adapter_register.add_argument("--max-prompt-length", type=int, default=100000)
    adapter_register.add_argument("--supports-raw-prompt", action="store_true", default=False)
    adapter_register.add_argument("--supports-templates", action="store_true", default=True)
    adapter_register.add_argument("--supports-argv", action="store_true", default=True)
    adapter_register.add_argument("--verification-mode", default="shell")
    adapter_register.set_defaults(func=cmd_adapter_register)
    adapter_capability = adapter_sub.add_parser("capability", help="query adapter capabilities and limits")
    adapter_capability.add_argument("--adapter")
    adapter_capability.set_defaults(func=cmd_adapter_capability)
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
    adapter_run.add_argument("--prompt-template")
    adapter_run.add_argument("--var", dest="prompt_vars", action="append", default=[])
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
    adapter_run.add_argument("--approval-id", type=int)
    adapter_run.add_argument("--approval-scope")
    adapter_run.add_argument("--changed")
    adapter_run.add_argument("--notes")
    adapter_run.set_defaults(func=cmd_adapter_run)

    tool = sub.add_parser("tool", help="tool and capability registry commands")
    tool_sub = tool.add_subparsers(dest="tool_command", required=True)
    tool_register = tool_sub.add_parser("register", help="register or update a tool capability")
    tool_register.add_argument("--id", required=True)
    tool_register.add_argument("--capability", required=True)
    tool_register.add_argument("--command", required=True)
    tool_register.add_argument("--availability", default="unknown")
    tool_register.add_argument("--trust", default="project_declared")
    tool_register.add_argument("--notes")
    tool_register.set_defaults(func=cmd_tool_register)
    tool_seed = tool_sub.add_parser("seed", help="seed standard local/manual tool capabilities")
    tool_seed.set_defaults(func=cmd_tool_seed)

    approval = sub.add_parser("approval", help="human gate commands")
    approval_sub = approval.add_subparsers(dest="approval_command", required=True)
    approval_request = approval_sub.add_parser("request", help="request human approval for gated work")
    approval_request.add_argument("--story")
    approval_request.add_argument("--summary", required=True)
    approval_request.add_argument("--risk", default="high")
    approval_request.add_argument("--requested-by", default="harness")
    approval_request.add_argument("--scope")
    approval_request.add_argument("--ttl-minutes", type=int, default=60)
    approval_request.add_argument("--notes")
    approval_request.set_defaults(func=cmd_approval_request)
    approval_resolve = approval_sub.add_parser("resolve", help="resolve a pending human gate")
    approval_resolve.add_argument("--id", type=int, required=True)
    approval_resolve.add_argument("--status", required=True, choices=sorted(HUMAN_GATE_STATUSES - {"pending"}))
    approval_resolve.add_argument("--resolved-by", default="human")
    approval_resolve.add_argument("--notes")
    approval_resolve.set_defaults(func=cmd_approval_resolve)
    approval_check = approval_sub.add_parser("check", help="check approval validity for a scope")
    approval_check.add_argument("--id", type=int, required=True)
    approval_check.add_argument("--scope")
    approval_check.add_argument("--fail-on-invalid", action="store_true")
    approval_check.set_defaults(func=cmd_approval_check)

    bench = sub.add_parser("bench", help="benchmark harness commands")
    bench_sub = bench.add_subparsers(dest="bench_command", required=True)
    bench_run = bench_sub.add_parser("run", help="run local routing benchmark cases")
    bench_run.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    bench_run.add_argument("--fail-on-regression", action="store_true")
    bench_run.add_argument("--notes")
    bench_run.set_defaults(func=cmd_bench_run)

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
    run_once.add_argument("--approval-id", type=int)
    run_once.add_argument("--approval-scope")
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
        ("routes", "route_decision"),
        ("approvals", "human_gate"),
        ("benchmarks", "benchmark_run"),
        ("reports", "completion_report"),
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
