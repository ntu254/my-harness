# CLI

`my-harness` v0.2 adds a small SQLite-backed CLI.

The CLI is intentionally narrow. It records intake, stories, evidence, traces,
and active work. It does not orchestrate agents or run dangerous actions.

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
harness intake add
harness story add
harness story update
harness evidence add
harness trace add
harness query active
harness query intakes
harness query stories
harness query evidence
harness query traces
```

Every command accepts `--json` at the top level:

```powershell
.\harness\harness.ps1 --json query active
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

## State Transition Safety

`story update` supports optimistic concurrency:

```powershell
.\harness\harness.ps1 story update --id MH-005 --status verifying --expected-revision 1
```

If another process has already updated the story, the command fails instead of
silently overwriting newer state.
