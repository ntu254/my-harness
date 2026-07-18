# Completion Gates

v0.9 adds the stable-core gate layer required before v1.0.

Routing decides what should happen. Completion gates decide whether a task is
allowed to be closed.

## Final Report

Use:

```powershell
.\harness\harness.ps1 report final --json --story MH-123 --route-id 7 --persist
```

The report includes:

- story state
- route workflow and selected skills
- missing required capabilities
- missing optional capabilities
- approval validity
- evidence ids
- stale evidence
- skipped checks
- residual risk
- rollback info

The report status is:

- `pass`: complete evidence and no blocking gate
- `weak`: complete enough to continue, but optional proof or skipped checks exist
- `blocked`: required proof, approval, or fresh evidence is missing

## Complete

Use:

```powershell
.\harness\harness.ps1 complete --json --story MH-123 --route-id 7
```

`complete` persists a completion report and updates the story to `completed`
only when gates pass. Weak proof requires `--allow-weak`.

## Evidence Freshness

Evidence is stale when the current git head or dirty file set differs from the
state captured when evidence was recorded. Stale evidence blocks completion
unless explicitly allowed:

```powershell
.\harness\harness.ps1 complete --story MH-123 --allow-stale-evidence
```

That override should be rare and must be explained in residual risk.

## Approval Scope

Approvals are bounded by scope and expiry:

```powershell
.\harness\harness.ps1 approval request `
  --summary "Approve production migration" `
  --risk critical `
  --scope deploy-prod-2026-07-19 `
  --ttl-minutes 60

.\harness\harness.ps1 approval check --id 4 --scope deploy-prod-2026-07-19 --fail-on-invalid
```

High-risk runner commands can use a valid approval instead of
`--allow-high-risk`:

```powershell
.\harness\harness.ps1 run once `
  --id MH-DEPLOY `
  --summary "Run bounded migration" `
  --agent-command "python --version" `
  --verify-command "python -m py_compile cli\harness.py" `
  --work-type migration `
  --scope external_system `
  --risk critical `
  --reversibility irreversible `
  --approval-id 4 `
  --approval-scope deploy-prod-2026-07-19
```
