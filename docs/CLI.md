# CLI

`my-harness` provides a small SQLite-backed CLI.

The CLI is intentionally narrow. It records intake, stories, evidence, traces,
active work, and single-task runner attempts. Guarded high-risk runs are
recorded but not executed without explicit approval.

## Start

Windows:

```powershell
.\harness\harness.ps1 init
```

macOS/Linux:

```bash
bash harness/harness.sh init
```

The default database is:

```text
harness/harness.db
```

This file is local runtime state and is ignored by git.

## Commands

```bash
harness init
harness check
harness intake add
harness story add
harness story update
harness evidence add
harness adapter register
harness adapter list
harness adapter run
harness trace add
harness run once
harness query active
harness query intakes
harness query stories
harness query evidence
harness query traces
harness query runs
harness query adapters
```

Every command accepts `--json` at the top level:

```powershell
.\harness\harness.ps1 --json query active
```

Run the standard checks:

```powershell
.\harness\harness.ps1 check --include-active --strict-active
```

## Example

```powershell
.\harness\harness.ps1 init

.\harness\harness.ps1 intake add `
  --intent modify `
  --work-type feature `
  --scope module `
  --risk medium `
  --lane normal `
  --summary "Add CLI MVP"

.\harness\harness.ps1 story add `
  --id MH-005 `
  --title "Implement CLI SQLite MVP" `
  --lane normal `
  --status in_progress

.\harness\harness.ps1 evidence add `
  --kind smoke `
  --target cli `
  --result pass `
  --command ".\harness\harness.ps1 query active" `
  --story MH-005
```

Runner example:

```powershell
.\harness\harness.ps1 run once `
  --id MH-006 `
  --summary "Implement runner MVP" `
  --agent-command "python --version" `
  --verify-command "python -m py_compile cli\harness.py" `
  --work-type harness_improvement `
  --scope module `
  --risk low `
  --uncertainty low `
  --reversibility easy
```

Adapter example:

```powershell
.\harness\harness.ps1 adapter register `
  --id mock-python `
  --provider mock `
  --command-template "python --version" `
  --availability present `
  --trust verified_local

.\harness\harness.ps1 adapter run `
  --adapter mock-python `
  --id MH-007 `
  --summary "Validate adapter contract" `
  --prompt "Implement the requested task" `
  --verify-command "python -m py_compile cli/harness.py"
```

## State Transition Safety

`story update` supports optimistic concurrency:

```powershell
.\harness\harness.ps1 story update --id MH-005 --status verifying --expected-revision 1
```

If another process has already updated the story, the command fails instead of
silently overwriting newer state.
