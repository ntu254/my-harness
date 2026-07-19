# Harness Engineering Adoption

This document records what `my-harness` absorbs from
`E:\HESD\harness-engineering`.

The source repo is a skill pack and artifact workflow. `my-harness` is a
CLI/state/protocol controller. The right move is to absorb its operating model
as contracts, skills, checks, and future adoption-pack behavior, not to copy the
whole skill tree.

## Reusable Ideas

### Artifact Lifecycle

`harness-engineering` models non-trivial software work as:

```text
spec -> research/spike -> plan -> implement -> review -> verify-release -> learn -> archive
```

`my-harness` should keep this adaptive:

- tiny lane: no required spec/plan ceremony;
- normal lane: lightweight artifact lifecycle when work is multi-file,
  product-shaping, or ambiguous;
- high-risk and approval-required lanes: stronger planning, review, rollback,
  and GO/NO-GO evidence.

### Bootstrap And Adoption

Useful adoption behavior from `he-bootstrap`:

- create files only when missing;
- preserve user-authored files;
- use one managed `AGENTS.md` block instead of overwriting the whole file;
- validate the structure after bootstrap;
- treat templates as compatibility contracts.

For `my-harness`, this maps to `v0.12` project adoption:

```text
harness adopt --target <repo> --dry-run
harness adopt --target <repo> --mode merge
harness adopt --target <repo> --mode override --approval <id>
```

The first implementation should not auto-commit. It should report planned
changes, write only in approved modes, and keep backups for overrides.

### Spec And Plan Contracts

`he-spec` and `he-plan` treat Markdown as contract-bearing artifacts with:

- YAML frontmatter;
- stable slug;
- stable requirement/progress IDs;
- required sections;
- measurable success criteria;
- append-only revision notes;
- concrete validation commands.

For `my-harness`, this should become a cross-platform artifact checker, likely
implemented in Python rather than Bash/JQ:

```text
harness artifact check --kind spec --path docs/specs/<slug>-spec.md
harness artifact check --kind plan --path docs/plans/active/<slug>-plan.md
harness check --artifact-contracts
```

### Domain Docs Registry

The domain-doc registry idea is valuable for project packs:

| Domain | Purpose |
| --- | --- |
| `SECURITY.md` | threat model, auth, sensitive data |
| `DATA.md` | data model, migrations, integrity rules |
| `FRONTEND.md` | frontend stack and component conventions |
| `DESIGN.md` | visual and interaction standards |
| `PRODUCT_SENSE.md` | users, outcomes, product heuristics |
| `RELIABILITY.md` | failure modes and operational guardrails |
| `OBSERVABILITY.md` | logs, metrics, traces, health checks |

These docs should be optional and route-triggered. Backend/tiny work should not
load frontend/design docs by default.

### Review Fanout

`he-review` splits review into:

- correctness;
- architecture/invariants;
- security;
- data integrity/privacy;
- simplicity.

`my-harness` should not force full fanout on every task. It should use lane and
risk:

- tiny: focused correctness/code-quality check;
- normal: correctness plus code-quality, with extra dimensions when touched
  surfaces require them;
- high-risk/approval-required: security/data/rollback review becomes mandatory
  when applicable.

### Verify/Release GO/NO-GO

`he-verify-release` strengthens the existing completion gate:

- default to `NO-GO` when evidence is missing or uncertain;
- require rollback for risky release/migration work;
- include post-release checks;
- record a written decision with evidence.

This maps directly to future `report final` and `complete` improvements.

### Learn Loop

`he-learn` turns friction into durable updates:

```text
learning -> docs/runbook/domain-doc -> mechanical guardrail -> archived plan
```

This should inform `my-harness` self-improvement after v1.0, but only through
human-governed proposals and deterministic audit findings.

### Browser Evidence

`he-video` and `agent-browser` provide a strong UI proof model:

- capture failure before fixing;
- capture resolution after fixing;
- use the same scenario ID and flow;
- keep raw artifacts temporary;
- promote only minimal evidence when needed.

This should become an optional UI proof policy for `design-quality-review`, not
a default requirement for non-UI work.

## What Not To Copy

- Do not copy the full skill tree into `my-harness`.
- Do not require full spec/plan/review/release/learn for tiny tasks.
- Do not make `bash`, `jq`, GitHub Actions, or macOS-only tools core
  requirements.
- Do not auto-commit during adoption.
- Do not deploy all domain docs into every target repo unless the project pack
  asks for them.
- Do not treat mock-free testing as a universal rule. `my-harness` still needs
  mock/replay provider tests to avoid token and credential costs.

## Current Absorption In v0.10.4

- Added `artifact-lifecycle` skill for non-trivial feature/migration/release
  and harness-improvement work.
- Added `release-readiness` skill for release and migration work.
- Kept tiny-lane routing unchanged.
- Documented future project-pack, artifact-check, review, verify, and learn
  improvements.

## Future Implementation Slices

| Slice | Improvement |
| --- | --- |
| `v0.11` | authority/protocol still comes first |
| `v0.12` | project-pack adoption with managed block and no auto-commit |
| `v0.13` | Python artifact contract checks for specs/plans/docs drift |
| `v1.0` | stable personal harness with optional artifact lifecycle |
| `v1.2` | worktree isolation and review fanout for non-trivial work |
| `v1.4` | human-governed learn loop/self-improvement |
