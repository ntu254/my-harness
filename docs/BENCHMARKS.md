# Benchmark Harness

v0.8 adds a small deterministic benchmark harness for route decisions.

Run it with:

```powershell
.\harness\harness.ps1 bench run --json --fail-on-regression
```

Benchmark cases live in `harness/benchmarks.json`. Each case describes a task shape and expected route output:

- expected lane
- expected skills
- optional tags
- optional extra required capabilities

The benchmark does not run external AI agents. It validates the controller itself: classification, workflow selection, skill selection, and gate behavior. This keeps the first benchmark version fast and stable, while leaving room for later agent-quality benchmarks.

v0.9 also records deterministic controller scores:

- `quality`: fixture pass ratio
- `cost`: process overhead against fixture process budgets
- `adaptiveness`: lane selection accuracy
- `durability`: missing proof/capability pressure

These scores are not yet a substitute for real agent-output evaluation. They are
the first stable sensor for whether the harness is getting heavier or weaker as
the controller evolves.
