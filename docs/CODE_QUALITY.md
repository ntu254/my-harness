# Code Quality

Code quality is not a polish phase. It keeps future work cheap.

## Core Rule

```text
Make the next change easier unless doing so would overbuild the current one.
```

## Checks

- Names describe intent.
- Diff is scoped.
- No unrelated refactor.
- No abstraction without real pressure.
- Unknown input is parsed at boundaries.
- Business rules stay out of UI/controllers/adapters when possible.
- Errors recover, add context, or fail clearly.
- Tests prove behavior, not implementation trivia.
- Public contracts are not changed accidentally.

## Lane Expectations

Tiny:

- obvious code;
- minimal diff;
- one focused check.

Normal:

- maintainable structure;
- focused tests;
- clear error behavior.

High-risk:

- boundaries reviewed;
- security/data correctness reviewed;
- rollback or recovery considered;
- independent review when needed.
