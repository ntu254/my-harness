# Progress Log

## Current Verified State

- Repository root: `E:/HESD/my-harness`
- Standard startup path:
  - Windows: `.\harness\init.ps1`
  - POSIX: `bash harness/init.sh`
- Standard verification path: run the startup path and any workflow-specific
  evidence listed in `harness/features.json`.
- Active feature: none. `MH-001`, `MH-002`, `MH-004`, `MH-005`, `MH-006`, `MH-007`, and `MH-008` are passing.
- Current blockers: none recorded.

## Best Next Step

Plan v0.6 real provider smoke gates, prompt template files, and shell-free
adapter execution on top of the validated preset/discovery layer.

## Session Log

### Session 001

- Date: 2026-07-19
- Goal: Scaffold `my-harness` v0.1 continuity package.
- Completed: initial docs, state files, scripts, and templates created.
- Verification executed:
  - `.\harness\init.ps1`
  - `python -m json.tool harness\features.json`
  - `rg --files`
- Evidence recorded: `harness/features.json` records scaffold validation.
- Commit: `a442d0a` pushed to `origin/main`.
- Updated files or artifacts: v0.1 scaffold.
- Known risks: POSIX script has not been run in a POSIX shell in this session.
- Best next step: validate `MH-002` tiny-change workflow.

### Session 002

- Date: 2026-07-19
- Goal: Close v0.1 acceptance criteria before planning v0.2.
- Completed:
  - Test A cold start validation.
  - Test B tiny documentation edit validation.
  - Test D high-risk request simulation.
  - Test E handoff readiness review.
- Verification executed:
  - `.\harness\init.ps1`
  - `python -m json.tool harness\features.json`
  - `git diff --check`
- Evidence recorded:
  - `harness/v0.1-acceptance.md`
  - `harness/features.json`
- Commit: acceptance closure pushed to `origin/main`; use `git log --oneline -2`
  for the exact current history.
- Updated files or artifacts:
  - `README.md`
  - `harness/v0.1-acceptance.md`
  - `harness/features.json`
  - `harness/progress.md`
- Known risks: POSIX script still has not been run in a POSIX shell in this session.
- Best next step: plan v0.2 CLI/SQLite MVP.

### Session 003

- Date: 2026-07-19
- Goal: Implement v0.2 CLI/SQLite MVP.
- Completed:
  - Added `cli/harness.py`.
  - Added SQLite schema at `state/schema/001-init.sql`.
  - Added Windows and POSIX CLI wrappers.
  - Added `docs/CLI.md`.
  - Updated startup scripts to initialize local SQLite state.
- Verification executed:
  - `.\harness\init.ps1`
  - `python -m json.tool harness\features.json`
  - `python -m py_compile cli\harness.py`
  - `.\harness\harness.ps1 intake add ...`
  - `.\harness\harness.ps1 story add --id MH-005 ...`
  - `.\harness\harness.ps1 evidence add ...`
  - `.\harness\harness.ps1 trace add ...`
  - `.\harness\harness.ps1 query active`
  - `.\harness\harness.ps1 --json query stories`
  - `.\harness\harness.ps1 story update --expected-revision ...`
  - `git diff --check`
- Evidence recorded:
  - `harness/v0.2-acceptance.md`
  - `harness/features.json`
  - local runtime DB: `harness/harness.db` (ignored by git)
- Commit: recorded in the latest `origin/main` history after push.
- Updated files or artifacts:
  - `README.md`
  - `harness.yaml`
  - `harness/features.json`
  - `harness/progress.md`
  - `harness/init.ps1`
  - `harness/init.sh`
  - `harness/harness.ps1`
  - `harness/harness.sh`
  - `harness/v0.2-acceptance.md`
  - `cli/harness.py`
  - `state/schema/001-init.sql`
  - `docs/CLI.md`
- Known risks: POSIX wrapper not executed in a POSIX shell in this session.
- Best next step: design v0.3 orchestration runner, including task execution
  lifecycle, agent command adapter, tool policy, and resumable handoff.

### Session 004

- Date: 2026-07-19
- Goal: Implement v0.3 single-task orchestration runner.
- Completed:
  - Added `agent_run` state table.
  - Added `harness run once`.
  - Added automatic lane classification.
  - Added guarded execution for `high_risk` and `approval_required` lanes.
  - Added command log capture under ignored runtime state.
  - Added runner docs and v0.3 plan.
- Verification executed:
  - `.\harness\init.ps1`
  - `python -m json.tool harness\features.json`
  - `python -m py_compile cli\harness.py`
  - `.\harness\harness.ps1 run once --help`
  - `.\harness\harness.ps1 --json run once --id MH-006 ...`
  - `.\harness\harness.ps1 --json run once --id MH-006-GUARD ...`
  - `.\harness\harness.ps1 --json query runs`
  - `.\harness\harness.ps1 --json query stories`
  - `git diff --check`
- Evidence recorded:
  - `harness/v0.3-plan.md`
  - `harness/v0.3-acceptance.md`
  - `harness/features.json`
  - local runtime DB: `harness/harness.db` (ignored by git)
  - local runtime logs: `harness/runs/` (ignored by git)
- Commit: recorded in the latest `origin/main` history after push.
- Updated files or artifacts:
  - `.gitignore`
  - `README.md`
  - `docs/CLI.md`
  - `docs/RUNNER.md`
  - `harness.yaml`
  - `harness/features.json`
  - `harness/progress.md`
  - `harness/v0.3-plan.md`
  - `harness/v0.3-acceptance.md`
  - `cli/harness.py`
  - `state/schema/001-init.sql`
- Known risks:
  - POSIX wrapper not executed in a POSIX shell in this session.
  - No provider-specific Claude/Codex adapter yet.
  - Schema migration is still simple `CREATE TABLE IF NOT EXISTS` evolution.
- Best next step: design v0.4 adapter contract, migration runner, and automated
  check command.

### Session 005

- Date: 2026-07-19
- Goal: Implement v0.4 adapter contract, migration discipline, and check command.
- Completed:
  - Added versioned schema loading from `state/schema/*.sql`.
  - Added `state/schema/002-adapters.sql`.
  - Added `agent_adapter` registry state.
  - Added `adapter register`, `adapter list`, and `adapter run`.
  - Added `harness check`.
  - Added adapter/check docs and v0.4 plan.
- Verification executed:
  - `.\harness\harness.ps1 --json init`
  - `.\harness\harness.ps1 check --include-active --strict-active`
  - `python -m py_compile cli\harness.py`
  - `.\harness\harness.ps1 adapter run --help`
  - `.\harness\harness.ps1 --json adapter register --id mock-python ...`
  - `.\harness\harness.ps1 --json adapter run --adapter mock-python --id MH-007 ...`
  - `.\harness\harness.ps1 --json query adapters`
  - `.\harness\harness.ps1 --json query runs`
  - inactive adapter rejection smoke
  - `git diff --check`
- Evidence recorded:
  - `harness/v0.4-plan.md`
  - `harness/v0.4-acceptance.md`
  - `harness/features.json`
  - local runtime DB: `harness/harness.db` (ignored by git)
  - local runtime logs: `harness/runs/` (ignored by git)
- Commit: recorded in the latest `origin/main` history after push.
- Updated files or artifacts:
  - `README.md`
  - `docs/ADAPTERS.md`
  - `docs/CHECKS.md`
  - `docs/CLI.md`
  - `harness.yaml`
  - `harness/features.json`
  - `harness/progress.md`
  - `harness/v0.4-plan.md`
  - `harness/v0.4-acceptance.md`
  - `cli/harness.py`
  - `state/schema/002-adapters.sql`
- Known risks:
  - POSIX wrapper not executed in a POSIX shell in this session.
  - Real Claude/Codex adapter presets are not included yet.
  - Schema migration has forward-only apply behavior and no rollback.
- Best next step: design v0.5 provider presets, prompt-file rendering, adapter
  capability discovery, and a safer command-template quoting policy.

### Session 006

- Date: 2026-07-19
- Goal: Implement v0.5 provider presets, prompt-file rendering, and adapter discovery.
- Completed:
  - Added `state/schema/003-adapter-discovery.sql`.
  - Added adapter presets for `mock-python`, `codex-local`, and `claude-local`.
  - Added `adapter preset`.
  - Added `adapter discover`.
  - Added `adapter run --prompt-file`.
  - Added runtime prompt-file generation under `harness/prompts/`.
  - Added shell-quoted placeholders and raw prompt guard.
- Verification executed:
  - `.\harness\harness.ps1 --json init`
  - `python -m py_compile cli\harness.py`
  - `.\harness\harness.ps1 adapter preset list`
  - `.\harness\harness.ps1 --json adapter preset all`
  - `.\harness\harness.ps1 --json adapter discover --adapter mock-python`
  - `.\harness\harness.ps1 --json adapter run --adapter mock-python --id MH-008 ...`
  - `Test-Path harness\prompts\MH-008.prompt.txt`
  - `.\harness\harness.ps1 --json adapter run --adapter mock-python --id MH-008-FILE --prompt-file ...`
  - raw `{prompt}` guard rejection smoke
  - `.\harness\harness.ps1 --json check --include-active --strict-active`
- Evidence recorded:
  - `harness/v0.5-plan.md`
  - `harness/v0.5-acceptance.md`
  - `harness/features.json`
  - local runtime DB: `harness/harness.db` (ignored by git)
  - local runtime logs: `harness/runs/` (ignored by git)
  - local runtime prompts: `harness/prompts/` (ignored by git)
- Commit: recorded in the latest `origin/main` history after push.
- Updated files or artifacts:
  - `.gitignore`
  - `README.md`
  - `docs/ADAPTERS.md`
  - `docs/CHECKS.md`
  - `docs/CLI.md`
  - `harness.yaml`
  - `harness/features.json`
  - `harness/progress.md`
  - `harness/v0.5-plan.md`
  - `harness/v0.5-acceptance.md`
  - `cli/harness.py`
  - `state/schema/003-adapter-discovery.sql`
- Known risks:
  - POSIX wrapper not executed in a POSIX shell in this session.
  - Codex and Claude presets are not provider-smoked yet.
  - Command templates still execute through a shell.
- Best next step: design v0.6 provider smoke gates, prompt template files, and
  shell-free adapter execution for safer command construction.
