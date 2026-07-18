# Design Quality

Use this only for frontend, UI, product, or visual work.

## Context

Before meaningful UI work, identify:

- user and product goal;
- existing design system or conventions;
- brand/product voice;
- anti-references;
- accessibility and responsive expectations.

If `PRODUCT.md` or `DESIGN.md` exists in a target repo, read it. If neither
exists and the task is visual, record the missing context.

## UX Review Is Not Technical Check

UX review asks:

- Is the primary action clear?
- Is hierarchy strong?
- Is cognitive load reasonable?
- Are empty, loading, error, and success states clear?
- Does the UI feel like this product, not a generic template?

Technical UI check asks:

- contrast;
- keyboard access;
- responsive behavior;
- text overflow;
- performance;
- theming/token consistency.

## Completion

UI work should not be marked complete until relevant states and viewport risks
are considered, even if the code compiles.
