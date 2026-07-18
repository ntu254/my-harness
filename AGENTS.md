# Agent Instructions

This repository uses `my-harness` v0.1.

Before acting, classify the request.

## Request Classes

- Read-only: answer, explain, review, diagnose, plan, or status. Inspect only
  the needed files. Do not modify repository files.
- Change: build, fix, edit, refactor, or write artifacts. Read the continuity
  state, classify the lane, make a scoped change, verify it, and update progress.
- Approval-required: deploy, release, publish, delete, force push, production
  migration, secret operation, or external side effect. Stop for explicit human
  approval before execution.

## Startup For Change Work

1. Confirm the repository root.
2. Read `harness/progress.md`.
3. Read `harness/features.json`.
4. Run `harness/init.ps1` on Windows or `harness/init.sh` on macOS/Linux.
5. Read `docs/INTAKE.md` and select the smallest safe lane.
6. Work on one active feature at a time unless the user explicitly asks for
   planning only.

## Completion Rules

- Do not claim completion without verification evidence.
- Do not weaken tests to make work appear complete.
- Keep changes inside the selected request scope.
- Record blockers instead of hiding unfinished work.
- Update `harness/progress.md` before ending significant change work.
- Keep `harness/features.json` truthful.

The app is what users touch. The harness is what agents touch.
