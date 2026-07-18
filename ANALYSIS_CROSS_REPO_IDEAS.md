# Cross-Repository Ideas For my-harness

Date: 2026-07-19
Scope: repos under `E:\HESD`
Current `my-harness` baseline: v0.10

This file records reusable thinking from nearby repositories. It is not a copy
plan. The goal is to extract principles, contracts, and small implementation
slices that make `my-harness` safer, easier to resume, and easier to apply to
other repositories.

## Current Absorbed Ideas

`my-harness` already absorbed several core ideas:

- Durable continuity state from long-running agent harnesses:
  `AGENTS.md`, `harness/progress.md`, `harness/features.json`, startup checks,
  and end-of-session evidence.
- SQLite-backed state and optimistic story updates for resumable work.
- Single-task runner and adapter registry before multi-agent orchestration.
- Skill, tool, and capability routing with missing proof gaps.
- Human gates for approval-required work.
- Evidence freshness checks tied to git head and dirty state.
- Completion gates through `report final` and `complete`.
- Deterministic routing benchmarks.
- v0.10 schema contracts and CLI contract tests.

The remaining opportunities are less about adding more prose and more about
turning cross-repo lessons into enforceable contracts, adoption paths, and
tests.

## Lessons To Reuse

### 1. Project Packs From forge-harness

Useful idea: keep core portable and stack-agnostic; put product, architecture,
test commands, RBAC, and design context in a project-specific pack.

Current state:

- `my-harness` has portable core docs.
- It does not yet have a first-class adoption or project-pack command.

Recommended slice:

- Add `project-pack.template/` with `pack.yaml`, `PRODUCT.md`,
  `ARCHITECTURE.md`, `TESTING.md`, optional `DESIGN.md`, and optional
  `RBAC.md`.
- Add `harness adopt --target <repo>` later, after template rules are stable.

Why it matters:

- A harness becomes reusable across backend, frontend, CLI, infra, and AI
  projects without forking core rules.

### 2. Spec Pipeline From spec-kit

Useful idea: for ambiguous or high-risk product work, preserve traceability:

```text
Spec -> Plan -> Tasks -> Evidence -> Report
```

Current state:

- `my-harness` has spec clarification skill and templates.
- It does not yet have a command that creates numbered spec folders or enforces
  transformation trace.

Recommended slice:

- Add a lightweight `docs/SPEC_PIPELINE.md`.
- Later add `harness spec new` and `harness task extract`.

Why it matters:

- It avoids guessing BRD/PRD intent and gives future agents requirement lineage.

### 3. Skill Strictness From superpowers

Useful idea: skills should have triggers, preconditions, steps, outputs,
evidence requirements, and failure behavior. Strict skills are powerful, but
heavy if forced onto tiny tasks.

Current state:

- `harness/skills.json` selects skills by lane/work type.
- The schema is intentionally small.

Recommended slice:

- Extend skill contracts incrementally:
  `preconditions`, `steps`, `outputs`, `evidence_requirements`,
  `failure_behavior`.
- Keep tiny lane exempt from heavy skill packets unless risk demands it.

Why it matters:

- Skills become executable playbooks instead of labels.

### 4. Plugin And Provider Test Matrix From ponytail/superpowers

Useful idea: provider/plugin support needs contract tests, not faith.

Current state:

- v0.10 added CLI contract tests.
- Real provider adapters are still deferred.

Recommended slice:

- Add mock/replay provider CLIs before live Codex/Claude checks.
- Keep live provider checks release-gated or manual to avoid token/cost churn.

Why it matters:

- Provider integration should be testable without spending model tokens.

### 5. Repository Protocol Tests From repository-harness

Useful idea: installer, release, authority, and protocol behavior deserve
dedicated tests.

Current state:

- `harness check` now runs local CLI contracts.
- There is no installer or adoption protocol yet.

Recommended slice:

- Add `docs/INDEX.md` and ADRs first.
- Add adoption protocol tests when `harness adopt` exists.

Why it matters:

- Multi-repo use fails if install/update semantics are vague.

### 6. Code Quality As A Gate

Useful idea: code quality is not a polish phase. It is a cost-control system
for future changes.

Current state:

- `docs/CODE_QUALITY.md` defines quality expectations.
- Route selection can include `code-quality-review`.
- There is no deterministic code-quality check suite yet.

Recommended slice:

- Add deterministic checks for:
  scoped diff, no unrelated refactor, no broken JSON, no stale evidence,
  no missing verification on completed work.
- Use P0/P1/P2/P3 severity:
  P0 blocks, P1 needs human, P2 warns, P3 informs.

Why it matters:

- Common mistakes should be caught without LLM cost.

### 7. Design Quality From fk-skills/open-design

Useful idea: UI/design quality should be opt-in by task type and tied to proof,
not vague taste.

Current state:

- `docs/DESIGN_QUALITY.md` exists.
- UI routes require browser, accessibility, and visual proof capabilities.
- v0.10 tests assert UI proof blocking.

Recommended slice:

- Add a design fixture to benchmarks that catches missing empty/loading/error
  states or generic AI-slop.
- Add optional project design context package recognition:
  `DESIGN.md`, `tokens.css`, `components.manifest.json`.

Why it matters:

- UI tasks need richer proof without burdening backend or tiny tasks.

### 8. Decision Inheritance

Useful idea: progress logs tell what happened; ADRs explain why.

Current state:

- `harness/progress.md` is strong.
- Decisions are not isolated.

Recommended slice:

- Add `docs/decisions/ADR-001-state-store.md`.
- Link future policy shifts to ADRs instead of burying them in session logs.

Why it matters:

- Future agents can preserve architectural intent without chat history.

## Priority Backlog

### Next Small Slice

1. Add `docs/INDEX.md`.
2. Add first ADR for SQLite state store and durable evidence.
3. Keep cross-repo analysis current with v0.10.

### v0.11 Candidate

1. Add project-pack template.
2. Add docs for adoption workflow.
3. Add tests that assert required docs/index/ADR files exist.

### v0.12 Candidate

1. Extend skill schema with executable playbook fields.
2. Add compatibility checks so old minimal skills still work during transition.
3. Add tests for skill schema evolution.

### v1.0 Readiness Candidate

1. Add deterministic quality checks with severity.
2. Add design-quality benchmark fixture.
3. Add schema validation using a real JSON Schema validator or an internal
   minimal validator.
4. Add release checklist and changelog.

## What Not To Copy

- Do not copy large daemon, web UI, plugin marketplace, or multi-agent systems
  before the single-agent controller is stable.
- Do not force spec folders, project packs, or UI craft rules onto tiny tasks.
- Do not run real provider smoke tests on every local check.
- Do not let `AGENTS.md` become a giant manual. Keep root guidance short and
  link to durable docs.

## Decision

Keep the cross-repo ideas as a curated backlog. Promote an idea into the
verified capability surface only after it has:

1. a scoped implementation,
2. repeatable verification,
3. recorded evidence in `harness/features.json` or `harness/progress.md`,
4. and a passing `harness check`.
