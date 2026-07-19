# Adapters

`my-harness` adds a small adapter contract for agent commands.

Adapters are command templates registered in SQLite and executed through the
same guarded runner path as `run once`. This keeps Claude, Codex, local scripts,
and mock adapters behind one lifecycle: intake, story, run, evidence, trace,
verification, and handoff.

## Register

```powershell
.\scripts\harness.ps1 adapter register `
  --id mock-python `
  --provider mock `
  --command-template "python --version" `
  --command-mode argv `
  --command-argv-json "[`"python`", `"--version`"]" `
  --availability present `
  --trust verified_local `
  --notes "local smoke adapter"
```

The command template may use simple placeholders:

- `{prompt}`
- `{prompt_shell}`
- `{story_id}`
- `{story_id_shell}`
- `{summary}`
- `{summary_shell}`
- `{adapter}`
- `{adapter_shell}`
- `{prompt_file}`
- `{prompt_file_shell}`

Prefer `{prompt_shell}` or `{prompt_file_shell}` over raw `{prompt}`. Templates
using raw `{prompt}` are rejected unless `--allow-raw-prompt` is passed.

## Presets

```powershell
.\scripts\harness.ps1 adapter preset list
.\scripts\harness.ps1 adapter preset all
```

Built-in presets:

- `mock-python`: local smoke adapter
- `codex-local`: Codex CLI shape, initially `unknown`
- `claude-local`: Claude CLI shape, initially `unknown`

Provider presets are intentionally marked `unknown` until local discovery or a
smoke run proves the executable and command flags on the current machine.

## Discovery

```powershell
.\scripts\harness.ps1 adapter discover --adapter mock-python
```

Discovery checks the adapter executable and records `availability`,
`trust_level`, `last_checked_at`, and `last_check_result`.

## Run

```powershell
.\scripts\harness.ps1 adapter run `
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

Prompt-file input:

```powershell
.\scripts\harness.ps1 adapter run `
  --adapter mock-python `
  --id MH-008-FILE `
  --summary "Validate prompt file input" `
  --prompt-file harness\prompts\MH-008.prompt.txt `
  --verify-command "python -m py_compile cli/harness.py"
```

Prompt-template input:

```powershell
.\scripts\harness.ps1 adapter run `
  --adapter mock-python `
  --id MH-009-TEMPLATE `
  --summary "Validate prompt template rendering" `
  --prompt-template templates\prompts\adapter-smoke.md `
  --var "task=Validate prompt template" `
  --var "context=v0.6 smoke" `
  --var "outcome=runner completes" `
  --verify-command "python -m py_compile cli/harness.py"
```

When `--prompt` is used, the harness writes a local prompt file under:

```text
harness/prompts/
```

That directory is ignored by git.

## Command Modes

Adapters can run in two modes:

- `shell`: render one command string and execute it through the shell.
- `argv`: render a JSON array of arguments and execute it with `shell=False`.

Prefer `argv` mode when possible. It avoids shell parsing for the agent command.
The built-in presets use `argv` mode.

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
.\scripts\harness.ps1 adapter register `
  --id codex-local `
  --provider codex `
  --command-template "codex exec --prompt-file {prompt_file_shell}" `
  --command-mode argv `
  --command-argv-json "[`"codex`", `"exec`", `"--prompt-file`", `"{prompt_file}`"]" `
  --availability unknown `
  --trust user_declared
```

Mark provider adapters as `unknown` until `harness check` or a direct smoke run
proves they are available on the local machine.
