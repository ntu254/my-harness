# Documentation Index

Start here when you need to understand or operate `my-harness` without chat
history.

## Entry Points

- `AGENTS.md`: root operating instructions for coding agents.
- `README.md`: capability timeline and startup commands.
- `harness/progress.md`: verified session history, risks, and next step.
- `harness/features.json`: source of truth for feature status and evidence.

## Core Concepts

- `docs/HARNESS.md`: harness purpose and operating model.
- `docs/INTAKE.md`: request classification and lane selection.
- `docs/REQUEST_AUTHORITY.md`: authority hierarchy and request classes.
- `docs/CONTEXT_RULES.md`: context selection and reading boundaries.
- `docs/WORKFLOWS.md`: workflow expectations by task shape.
- `docs/VERIFICATION.md`: proof and freshness rules.
- `docs/HUMAN_GATE.md`: approval-required behavior.

## CLI And Runtime

- `docs/CLI.md`: command reference.
- `docs/RUNNER.md`: single-task runner.
- `docs/ADAPTERS.md`: adapter registration, discovery, and execution.
- `docs/ROUTING.md`: skill/tool/capability routing.
- `docs/GATES.md`: final report and completion gates.
- `docs/CHECKS.md`: standard baseline checks.
- `docs/CONTRACTS.md`: schema and CLI command contracts.
- `docs/RELEASE_INSTALL.md`: Git tags, historical version testing, npx launcher,
  and npm publish checklist.
- `docs/BENCHMARKS.md`: route benchmark fixtures and scoring.
- `docs/HARNESS_ENGINEERING_ADOPTION.md`: lessons absorbed from
  `harness-engineering` and how they map to future project-pack work.
- `docs/TRACE.md`: trace and evidence recording.

## Quality

- `docs/CODE_QUALITY.md`: maintainability and review expectations.
- `docs/DESIGN_QUALITY.md`: UI/design proof expectations.

## Decisions

- `docs/decisions/ADR-001-state-store.md`: why `my-harness` uses SQLite plus
  durable repository artifacts.

## Planning And Evidence

- `harness/v0.1-acceptance.md` through `harness/v0.10-acceptance.md`:
  version acceptance evidence.
- `harness/v0.3-plan.md` through `harness/v0.10-plan.md`: scoped version
  plans.
- `ANALYSIS_CROSS_REPO_IDEAS.md`: curated cross-repo ideas and backlog.

## Rule

If a new durable doc becomes part of the expected startup or verification path,
add it here and include it in `harness check` when appropriate.
