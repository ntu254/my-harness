# my-harness

`my-harness` is a lightweight control layer for AI coding agents such as Codex,
Claude, and local mock runners.

It helps an agent classify work, select the right workflow, resolve required
skills and tools, run local adapter commands, collect evidence, enforce gates,
and leave durable state so the next session can continue without guessing.

```text
Use the smallest process that safely proves the work.
```

## Current Status

Current repository version: `0.11.0`.

This is ready for personal, single-repository harness work. It is not yet a
team/org harness, a real multi-agent scheduler, or a fully published npm
package.

Verified surface:

- `v0.1-v0.3`: continuity artifacts, request lanes, SQLite CLI, single-task
  runner.
- `v0.4-v0.7`: schema migrations, adapter registry, prompt rendering, argv
  execution, adapter capabilities.
- `v0.8-v0.9`: deterministic routing, tool resolver, human approvals,
  benchmark fixtures, final report and completion gates.
- `v0.10-v0.10.4`: schema contracts, CLI regression tests, GitHub/npx launcher,
  release/install docs, adapter and route contract coverage, and
  harness-engineering artifact lifecycle guidance.
- `v0.11.0`: adapter contract enforcement, schema validation checks, MIT
  license metadata, optional adapter conformance, and packaged validation module.

Baseline verification currently runs `17` unittest contract tests through
`harness check`.

## Requirements

- Python 3.10+ available as `python`, `python3`, or `py -3`.
- Git for historical version install.
- Node.js 18+ only when using the `npx`/launcher path.
- Windows PowerShell, macOS, or Linux shell.

No Python package install is required for the core CLI. The controller uses the
Python standard library and SQLite.

## Quick Start

Windows:

```powershell
git clone https://github.com/ntu254/my-harness.git
cd my-harness
.\scripts\init.ps1
.\scripts\harness.ps1 check --include-active --strict-active
.\scripts\harness.ps1 query active
```

macOS/Linux:

```bash
git clone https://github.com/ntu254/my-harness.git
cd my-harness
bash scripts/init.sh
bash scripts/harness.sh check --include-active --strict-active
bash scripts/harness.sh query active
```

Run the package launcher from the repository:

```powershell
node .\bin\my-harness.js --json init
node .\bin\my-harness.js check --include-active --strict-active
```

## Try A Specific Version

Use Git when you want the exact source at a historical milestone:

```powershell
git clone --branch v0.2.0 --depth 1 https://github.com/ntu254/my-harness.git my-harness-v0.2
cd my-harness-v0.2
.\scripts\harness.ps1 --json init
```

Use the GitHub `npx` launcher when you want a convenient installer experience:

```powershell
npx --yes github:ntu254/my-harness#v0.11.0 install --version v0.2.0 --target .\my-harness-v0.2
```

Check the launcher version:

```powershell
npx --yes github:ntu254/my-harness#v0.11.0 --package-version
```

The npm package name is reserved in metadata as `@ntu254/my-harness`, but this
package has not been published to npm yet. Until npm publish happens, use the
GitHub `npx` form above.

License: MIT.

## Core Features

### Request Lanes

`my-harness` classifies work into four lanes:

| Lane | Use For | Behavior |
| --- | --- | --- |
| `tiny` | Small, reversible file edits | Minimal process and fast proof |
| `normal` | Ordinary features, fixes, maintenance | Route, execute, verify, record evidence |
| `high_risk` | Costly, uncertain, infrastructure-sensitive work | Plan-gated flow with stronger proof |
| `approval_required` | Irreversible, external, critical, release/deploy/delete work | Requires human approval before execution |

### Durable State

The harness keeps two kinds of state:

- Git-tracked durable artifacts: `AGENTS.md`, `harness/features.json`,
  `harness/progress.md`, docs, plans, acceptance evidence.
- Ignored local runtime state: `harness/harness.db`, `harness/runs/`,
  `harness/prompts/`.

The local SQLite database records intake, stories, evidence, traces, adapter
runs, tools, approvals, route decisions, completion reports, and benchmark
runs.

### CLI And SQLite

Common commands:

```powershell
.\scripts\harness.ps1 --json init
.\scripts\harness.ps1 --json query active
.\scripts\harness.ps1 check --include-active --strict-active
```

Record work manually:

```powershell
.\scripts\harness.ps1 --json intake add --intent modify --work-type bugfix --scope module --uncertainty medium --reversibility easy --risk medium --lane normal --summary "Fix parser bug"
.\scripts\harness.ps1 --json story add --id BUG-001 --title "Fix parser bug" --lane normal
.\scripts\harness.ps1 --json evidence add --kind test --target BUG-001 --result pass --command "python -m unittest" --story BUG-001
.\scripts\harness.ps1 --json trace add --summary "Parser bug fixed" --outcome completed --story BUG-001 --evidence 1
```

### Routing And Capability Resolution

The deterministic router selects workflow, skills, required capabilities,
available tools, proof policy, and human-gate status:

```powershell
.\scripts\harness.ps1 tool seed
.\scripts\harness.ps1 route --json --summary "Fix login regression" --work-type bugfix --scope module --risk medium
```

UI/design work intentionally requires stronger proof:

```powershell
.\scripts\harness.ps1 route --json --summary "Update dashboard component" --work-type feature --scope module --risk medium --tag ui
```

Irreversible or critical work routes to approval:

```powershell
.\scripts\harness.ps1 route --json --summary "Deploy production migration" --work-type migration --scope external_system --risk critical --reversibility irreversible
```

### Adapter Execution

Built-in adapter presets:

- `mock-python`: local smoke adapter that never calls an external model.
- `codex-local`: local Codex CLI preset, availability depends on the user's
  machine.
- `claude-local`: local Claude CLI preset, availability depends on the user's
  machine.

Install and inspect presets:

```powershell
.\scripts\harness.ps1 --json adapter preset all
.\scripts\harness.ps1 --json adapter capability
.\scripts\harness.ps1 adapter discover
.\scripts\harness.ps1 --json adapter conformance
```

Run a task through an adapter:

```powershell
.\scripts\harness.ps1 --json adapter run --adapter mock-python --id SMOKE-001 --summary "Adapter smoke" --prompt "Say hello" --verify-command "python --version" --timeout 30
```

Adapter safety rules:

- `argv` mode is preferred where possible.
- Raw `{prompt}` shell templates are blocked unless explicitly allowed.
- Prompt files and run logs are written to ignored runtime directories.
- Provider conformance is available as an optional local command. It checks
  adapter metadata, executable discovery, and version commands without making
  CI depend on Codex or Claude being installed.

### Human Approval Gates

Request, resolve, and check scoped approval:

```powershell
.\scripts\harness.ps1 --json approval request --summary "Deploy production migration" --risk critical --scope deploy-prod --ttl-minutes 60
.\scripts\harness.ps1 --json approval resolve --id 1 --status approved
.\scripts\harness.ps1 --json approval check --id 1 --scope deploy-prod
```

Approval is scoped and expires. A valid approval for one scope does not unlock a
different scope.

### Completion Gates

Completion is a gate, not a status edit:

```powershell
.\scripts\harness.ps1 report final --json --story BUG-001 --route-id 1 --persist
.\scripts\harness.ps1 complete --json --story BUG-001 --route-id 1
```

The gate checks evidence freshness, required proof gaps, optional proof gaps,
approval validity, git head, and dirty state.

### Benchmarks

Run deterministic route fixtures:

```powershell
.\scripts\harness.ps1 bench run --json --fail-on-regression
```

Benchmark scores currently evaluate the controller: route selection, skill
selection, proof policy, cost shape, adaptiveness, and durability. They do not
yet score real AI output quality.

## Project Layout

```text
AGENTS.md                     Agent entrypoint and operating rules
README.md                     This file
harness.yaml                  Manifest and current version
cli/harness.py                Python stdlib CLI
bin/my-harness.js             Node launcher for npx/GitHub use
harness/features.json         Feature state and verification evidence
harness/progress.md           Session log and current verified state
scripts/*.ps1, *.sh           Local startup and CLI wrappers
migrations/*.sql              SQLite migrations
docs/releases/*.md            Version plans, acceptance evidence, and status notes
schemas/*.schema.json         JSON contract schemas
tests/test_*.py               CLI, adapter, route, and gate contract tests
docs/                         Durable operating documentation
templates/                    Reusable work/story/spec templates
```

Start with [docs/INDEX.md](docs/INDEX.md) when you need deeper documentation.

## Verification

Standard local verification:

```powershell
python -m unittest discover -s tests -p "test_*.py"
npm run check
.\scripts\harness.ps1 check --include-active --strict-active
npm pack --dry-run
```

`harness check` validates required files, JSON parseability, schema parseability,
Python compilation, CLI contract tests, launcher syntax, whitespace, and active
story state.

## Version Timeline

| Version | Capability |
| --- | --- |
| `v0.1.0` | Continuity package, manual lanes, progress/features state |
| `v0.2.0` | SQLite CLI for intake, story, evidence, trace, query |
| `v0.3.0` | `run once` local orchestration with high-risk blocking |
| `v0.4.0` | Schema migrations, adapter registry/run, `check` |
| `v0.5.0` | Adapter presets, prompt files, executable discovery |
| `v0.6.0` | Argv adapter execution and prompt templates |
| `v0.7.0` | Adapter capability taxonomy and verification metadata |
| `v0.8.0` | Route command, skill/tool resolver, human gates, benchmarks |
| `v0.9.0` | Final report, completion gate, evidence freshness, benchmark scores |
| `v0.10.0` | Schema contracts and CLI contract tests |
| `v0.10.1` | GitHub/npx launcher and release/install docs |
| `v0.10.2` | Quieter historical tag install checkout |
| `v0.10.3` | Adapter and route contract coverage after professional review |
| `v0.10.4` | Harness-engineering adoption guidance and artifact lifecycle routing |
| `v0.11.0` | Adapter contract enforcement, schema validation checks, MIT license, optional conformance |

## What Is Deferred

- No npm registry publish yet.
- No `harness adopt --target <repo>` project-pack adoption command yet.
- No mandatory Claude/Codex provider gate in baseline CI yet.
- No live UI variant mode.
- No autonomous multi-agent scheduler.
- No real AI-output benchmark scoring yet.
- No team/org policy-pack system yet.

These are intentionally deferred until the single-agent controller, authority
boundaries, and public command contracts are stable.

## Roadmap

Next planned slices:

- `v0.11`: authority and protocol hardening, including read-only discovery and
  public command manifest.
- `v0.12`: project adoption and project-pack boundary.
- `v0.13`: negative tests and deterministic drift audit.
- `v1.0`: stable personal harness readiness.
- `v1.1+`: provider adapters, richer skill evals, plugins, hooks, and
  orchestration after the core is proven.

See `harness/progress.md`, `harness/features.json`, and `docs/INDEX.md` for the
current verified state and durable planning context.

## Operating Rule

A task is not complete just because files changed. Completion requires evidence
appropriate to the change surface and durable handoff state for the next
session.
