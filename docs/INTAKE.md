# Intake

Classify change work before editing files.

## Classification Fields

```yaml
intent: read | analyze | plan | modify | execute
work_type: feature | bugfix | refactor | maintenance | migration | release | incident | harness_improvement
scope: file | module | repository | infrastructure | external_system
uncertainty: low | medium | high
reversibility: easy | costly | irreversible
risk: low | medium | high | critical
lane: tiny | normal | high_risk | approval_required
confidence: 0.0-1.0
```

## Lanes

### Tiny

Use for low-risk, narrow, obvious work:

- typo or copy edit;
- small docs update;
- narrow rename;
- simple fix with obvious verification.

Rules:

- No story folder.
- At most one short progress note.
- At most one main verification step.
- No decision record unless there is a real tradeoff.

### Normal

Use for bounded work with product or code behavior:

- small feature;
- bugfix;
- refactor with preserved behavior;
- maintenance with limited blast radius.

Rules:

- Use a mini-spec or story when behavior changes.
- Record expected evidence.
- Run focused verification.
- Update feature state and progress.

### High-Risk

Use when the work touches:

- auth or authorization;
- data model or migration;
- public API;
- security boundary;
- external provider;
- payment;
- broad repository scope;
- weak proof around important behavior.

Rules:

- Clarify before implementation.
- Create a high-risk story packet.
- Define validation strategy.
- Pause for human checkpoint when direction is ambiguous.

### Approval-Required

Use for:

- deploy;
- release;
- publish;
- delete;
- force push;
- production migration;
- secret operation;
- external side effect.

Rules:

- Prepare approval request.
- Do not execute until approval is explicit and scoped.

## Low Confidence

If classification confidence is low:

- read-only requests may continue with stated assumptions;
- low-risk changes should ask one clarifying question or downgrade to plan-only;
- any hard-gate signal escalates to high-risk or approval-required.
