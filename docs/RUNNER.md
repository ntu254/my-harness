# Runner

`my-harness` v0.3 adds a small orchestration runner.

The runner handles one local task at a time. It creates intake, story, run,
evidence, and trace records around command execution.

## Command

```powershell
.\scripts\harness.ps1 run once `
  --id MH-006-SMOKE `
  --summary "Validate runner MVP" `
  --agent-command "python --version" `
  --verify-command "python -m py_compile cli\harness.py" `
  --work-type harness_improvement `
  --scope module `
  --risk low `
  --uncertainty low `
  --reversibility easy
```

## What It Records

- `intake`: request classification and lane
- `story`: lifecycle status and verify command
- `agent_run`: command, lane, exit codes, evidence ids, and log directory
- `evidence`: agent and verification command results
- `trace`: final outcome and handoff note

Runtime command logs are written under:

```text
harness/runs/
```

This directory is ignored by git.

## Lane Behavior

If no lane is passed, the runner classifies one:

- `tiny`: low-risk file work with low uncertainty and easy reversibility
- `normal`: ordinary local feature, bugfix, refactor, or maintenance work
- `high_risk`: high uncertainty, costly reversibility, infrastructure, or external-system work
- `approval_required`: critical or irreversible work, plus risky release or migration work against infrastructure or external systems

`high_risk` and `approval_required` runs are recorded but not executed unless
`--allow-high-risk` is passed.

## Exit Behavior

- Agent command pass + verify command pass: story becomes `completed`.
- Agent command fail: story becomes `failed`; verification is skipped.
- Verify command fail: story becomes `failed`.
- Guarded high-risk run without approval: story becomes `needs_human`.
