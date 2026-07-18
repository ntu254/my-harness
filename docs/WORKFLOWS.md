# Workflows

## Read-Only

```text
classify -> read minimal context -> answer with evidence -> no repo mutation
```

Use for answer, explain, review, diagnose, plan, and status requests.

## Tiny Change

```text
classify -> read exact files -> edit -> one verification step -> update progress
```

Keep this lightweight. Do not create a story folder.

## Normal Work

```text
classify -> mini-spec or story -> plan-lite -> implement -> verify
-> quality check -> update state -> update progress
```

Use when behavior changes or the work spans more than one obvious edit.

## Bugfix

```text
reproduce -> root cause -> regression proof -> fix -> verify -> record evidence
```

If reproduction is impossible, record why and stop with a diagnosis instead of
guessing.

## Refactor

```text
baseline proof -> refactor -> same proof -> review diff
```

If behavior changes, reclassify as feature or bugfix.

## High-Risk Planning

```text
classify -> clarify -> high-risk story packet -> plan -> validation strategy
-> human checkpoint
```

Do not execute dangerous steps in v0.1 by default.

## Release Or External Action

```text
prepare evidence -> approval request -> execute approved action -> record result
```

The approval covers one bounded action only.
