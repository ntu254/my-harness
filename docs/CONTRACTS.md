# Contracts

The harness treats command output and registry files as contracts. Documentation
can explain intent, but stable automation depends on machine-readable shapes and
tests.

## Schema Contracts

JSON schema contracts live in:

```text
schemas/
```

Current contracts:

- `schemas/skill.schema.json`: shape of `harness/skills.json`.
- `schemas/benchmark.schema.json`: shape of `harness/benchmarks.json`.
- `schemas/route-decision.schema.json`: expected `route --json` output shape.
- `schemas/final-report.schema.json`: expected `report final --json` and
  `complete --json` output shape.

These schemas are intentionally small. They define the stable thin waist for
agents and scripts without pretending that every field is final forever.

## CLI Contract Tests

Command contract tests live in:

```text
tests/
```

The v0.10 tests use a temporary `MY_HARNESS_DB` so they do not mutate the local
runtime database. They cover:

- UI route proof blocking when browser/accessibility/visual proof is missing.
- Approval scope success and mismatch behavior.
- Completion blocking without evidence and passing with fresh evidence.
- Benchmark score output.

Run directly:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

The standard check command also runs these tests:

```powershell
.\harness\harness.ps1 check --include-active --strict-active
```

## Rule

If a public command output shape changes, update the schema, tests,
documentation, and progress evidence in the same change.
