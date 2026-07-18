# Adapters

`my-harness` v0.4 adds a small adapter contract for agent commands.

Adapters are command templates registered in SQLite and executed through the
same guarded runner path as `run once`. This keeps Claude, Codex, local scripts,
and mock adapters behind one lifecycle: intake, story, run, evidence, trace,
verification, and handoff.

## Register

```powershell
.\harness\harness.ps1 adapter register `
  --id mock-python `
  --provider mock `
  --command-template "python --version" `
  --availability present `
  --trust verified_local `
  --notes "local smoke adapter"
```

The command template may use simple placeholders:

- `{prompt}`
- `{story_id}`
- `{summary}`
- `{adapter}`

## Run

```powershell
.\harness\harness.ps1 adapter run `
  --adapter mock-python `
  --id MH-007 `
  --summary "Validate adapter contract" `
  --prompt "Implement the requested task" `
  --verify-command "python -m py_compile cli/harness.py" `
  --work-type harness_improvement `
  --scope module `
  --risk low `
  --uncertainty low `
  --reversibility easy
```

The adapter run creates a normal `agent_run` record. The run stores:

- `adapter_id`
- rendered `agent_command`
- original `prompt`
- verification command
- exit codes
- evidence ids
- log directory

## Availability Guard

Adapters with `availability` of `missing` or `inactive` do not run unless
`--allow-unavailable` is passed.

High-risk lane rules still apply. `high_risk` and `approval_required` adapter
runs also require `--allow-high-risk`.

## Future Provider Templates

The exact Claude and Codex command templates should be registered per machine,
because executable names, auth state, and CLI flags can vary.

Example shape:

```powershell
.\harness\harness.ps1 adapter register `
  --id codex-local `
  --provider codex `
  --command-template "codex exec --prompt ""{prompt}""" `
  --availability unknown `
  --trust user_declared
```

Mark provider adapters as `unknown` until `harness check` or a direct smoke run
proves they are available on the local machine.
