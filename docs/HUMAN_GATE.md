# Human Gate

Humans own irreversible and external actions.

## Approval Required

Ask before:

- deploy;
- release;
- publish;
- delete;
- force push;
- production migration;
- secret operation;
- paid external API call;
- external side effect.

## Approval Request Format

```text
Action:
Reason:
Risk:
Scope:
Command:
Expected result:
Rollback or recovery:
Evidence already collected:
Approval needed:
```

## Rules

- Approval must be explicit.
- Approval applies to one bounded action.
- If the command, scope, or environment changes, ask again.
- Denied or expired approval means stop.
