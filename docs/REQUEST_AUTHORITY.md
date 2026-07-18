# Request Authority

Request authority determines what an agent may do.

## Classes

| Class | Examples | Repository mutation |
| --- | --- | --- |
| Read-only | answer, explain, review, diagnose, plan, status | No |
| Change | build, fix, edit, refactor, write docs/code | Yes, after lane selection |
| Approval-required | deploy, release, publish, delete, force push, migration | Only after explicit human approval |

## Authority Order

1. Platform and safety rules.
2. Current explicit user instruction.
3. Human approval for one bounded action.
4. Security and permission policy.
5. Approved spec or product contract.
6. Story or task contract.
7. Repository-level instructions.
8. Directory-level instructions.
9. Skill or workflow defaults.
10. Existing implementation behavior.

## Conflict Rules

- Safety policy beats a user request to do unsafe work.
- A generated file loses to its canonical source.
- A plan that conflicts with actual code must be revised or reported as drift.
- A request to skip verification can downgrade the result to partial, but it
  cannot create a completed state when project policy requires proof.
