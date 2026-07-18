# Checks

`harness check` is the standard quality gate command.

```powershell
.\harness\harness.ps1 check --include-active --strict-active
```

## What It Checks

- required repository files exist
- schema migrations apply
- `harness/features.json` parses
- `cli/harness.py` compiles
- `git diff --check` passes
- active story queue is empty when `--strict-active` is used

## JSON Output

```powershell
.\harness\harness.ps1 --json check --include-active --strict-active
```

The command exits non-zero if any check fails.

## Migration Discipline

Schema files live in:

```text
state/schema/
```

Each file must start with a numeric version, for example:

- `001-init.sql`
- `002-adapters.sql`
- `003-adapter-discovery.sql`

`harness init` and `harness check` apply only missing versions and record them
in the `schema_version` table.
