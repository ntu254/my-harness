# Routing, Skills, And Capabilities

v0.8 restores the planned orchestration layer that sits before execution:

`CLASSIFY -> SELECT WORKFLOW -> PLAN SKILLS -> RESOLVE CAPABILITIES -> APPLY GATES`

The main user-facing command is:

```powershell
.\harness\harness.ps1 route --json --summary "Fix parser bug" --work-type bugfix --scope module --risk medium
```

The route decision returns:

- `lane`: tiny, normal, high_risk, or approval_required
- `workflow`: the operating workflow for the task
- `skills`: selected skill ids from `harness/skills.json`
- `required_capabilities`: capabilities required by those skills
- `available_tools`: matching tool or adapter records
- `candidate_tools`: matching records that are still unknown or missing
- `missing_capabilities`: proof gaps to handle before trusting execution
- `proof_policy`: pass, warn, or block
- `human_gate_required`: whether explicit approval is required

Seed local/manual capabilities with:

```powershell
.\harness\harness.ps1 tool seed
```

Register project-specific tools with:

```powershell
.\harness\harness.ps1 tool register --id pnpm-test --capability test-runner --command "pnpm test" --availability present
```

The route command is intentionally deterministic in v0.8. Later versions can add scoring, project profiles, agent selection, and learned routing weights without changing the basic contract.
