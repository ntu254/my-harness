# Verification

Completion requires evidence appropriate to the change surface.

## Proof Matrix

| Change surface | Minimum v0.1 evidence |
| --- | --- |
| Docs-only | Manual review, markdown check if available |
| Harness rules | Scenario walkthrough against a test task |
| Feature state | `features.json` parses and reflects actual status |
| Bugfix | Reproduction or failing evidence, then passing evidence |
| UI | Browser/screenshot/a11y note when browser work exists |
| High-risk | Plan, risk list, human checkpoint, no execution |

## Freshness

Evidence is fresh only when it was collected after the relevant change.

If files change after verification:

- rerun the check; or
- mark the evidence stale; or
- explain why changed files are unrelated.

## Weak Evidence

Agent confidence is not evidence.

Weak evidence may be acceptable for tiny work when clearly explained. Normal
work should not be marked complete with weak evidence. High-risk work cannot be
completed with weak evidence.

## Final Completion Gate

Before saying complete:

- required behavior is implemented;
- required verification ran or skip reason is explicit;
- evidence is fresh;
- blockers and residual risk are recorded;
- progress state is updated.
