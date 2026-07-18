# Trace

v0.1 uses `harness/progress.md` as the human-readable trace surface.

For significant change work, record:

- date;
- goal;
- classification and lane;
- files read;
- files changed;
- verification executed;
- evidence;
- blockers;
- risks;
- best next step.

## Good Trace

```text
Goal: Validate tiny docs workflow.
Lane: tiny.
Changed: README.md.
Verification: harness/init.ps1 passed after edit.
Evidence: command output in session.
Risk: none.
Next: Run high-risk request simulation.
```

## Bad Trace

```text
done
```

Trace should report verified state, not optimism.
