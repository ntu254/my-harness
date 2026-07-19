# ADR-001: SQLite State Store With Durable Repository Artifacts

Date: 2026-07-19
Status: accepted

## Context

`my-harness` needs to support long-running coding-agent work. A later session
must be able to answer what was requested, what changed, what was verified,
what is blocked, and what the next safe step is.

The harness also needs state transitions that are hard to fake accidentally:
story revisions, evidence records, route decisions, human approvals, benchmark
runs, and completion reports.

## Options

1. Markdown-only state.
2. JSON files only.
3. JSONL event log.
4. SQLite runtime database plus durable checked-in summaries.

## Decision

Use SQLite for local runtime/queryable state and checked-in repository artifacts
for durable continuity:

- SQLite: `harness/harness.db`, ignored by git.
- Feature truth: `harness/features.json`.
- Session truth: `harness/progress.md`.
- Agent startup truth: `AGENTS.md`.
- Version evidence: `harness/v*-acceptance.md`.

## Consequences

Benefits:

- Queries and joins stay simple as the harness gains routes, approvals,
  evidence, reports, and benchmark runs.
- Optimistic story revisions can detect stale concurrent updates.
- Runtime state can be regenerated or ignored without polluting git history.
- Checked-in summaries keep handoff readable without requiring the local DB.

Costs:

- Schema migrations must remain forward-compatible.
- Runtime DB state is local and cannot be treated as the only source of truth.
- Evidence must be summarized into durable files before ending significant work.

## Guardrails

- Do not commit `harness/harness.db` or runtime prompt/run folders.
- Do not mark a feature complete only because SQLite contains a record.
- Completion evidence must be fresh and recorded in durable artifacts when it
  matters for future sessions.
- If SQLite complexity stops paying for itself, revisit this ADR before v1.0.

## Related Artifacts

- `harness/features.json`
- `harness/progress.md`
- `docs/CONTRACTS.md`
- `docs/GATES.md`
- `migrations/*.sql`
