# Release And Install

This document describes how to test historical `my-harness` versions and how to
prepare the npm-style launcher.

## Version Tags

Each verified milestone should have a Git tag. Existing milestone commits:

| Version | Commit | Capability |
| --- | --- | --- |
| `v0.1.0` | `f118763` | v0.1 acceptance validation |
| `v0.2.0` | `9b6db5a` | SQLite CLI MVP |
| `v0.3.0` | `4c31ed7` | `run once` local runner |
| `v0.4.0` | `967680c` | schema migrations and adapter checks |
| `v0.5.0` | `14694f6` | adapter presets and prompt files |
| `v0.6.0` | `9b3c942` | argv adapter execution |
| `v0.7.0` | `84b5490` | adapter capability taxonomy |
| `v0.8.0` | `36be3af` | routing, skills, tools, human gates, benchmarks |
| `v0.9.0` | `db42659` | final report, completion gates, evidence freshness |
| `v0.10.0` | `29eca48` | schema contracts and CLI contract tests |

Create or backfill tags:

```powershell
git tag -a v0.2.0 9b6db5a -m "v0.2.0"
git push origin v0.2.0
```

Push all local version tags when they are verified:

```powershell
git push origin --tags
```

Do not move a published tag. If a tag is wrong, create a new patch tag such as
`v0.10.1` and document the correction.

## Test A Version With Git

```powershell
git clone --branch v0.2.0 --depth 1 https://github.com/ntu254/my-harness.git my-harness-v0.2
cd my-harness-v0.2
.\harness\harness.ps1 --json init
.\harness\harness.ps1 check
```

This is the most faithful way to inspect an old milestone because it runs the
exact files that existed at that tag.

## Test A Version With The Launcher

After the launcher exists on GitHub, run it through `npx` from the repository:

```powershell
npx github:ntu254/my-harness install --version v0.2.0 --target .\my-harness-v0.2
cd .\my-harness-v0.2
.\harness\harness.ps1 --json init
```

After publishing the package to npm:

```powershell
npx @ntu254/my-harness install --version v0.2.0 --target .\my-harness-v0.2
```

The install command refuses to write into a non-empty target directory. Use a
new directory for version testing.

## Run The Current Packaged CLI

From this repository:

```powershell
node .\bin\my-harness.js --json init
node .\bin\my-harness.js check --include-active --strict-active
```

With npm after publish:

```powershell
npx @ntu254/my-harness --json init
npx @ntu254/my-harness check --include-active --strict-active
```

The launcher sets `MY_HARNESS_WORKSPACE` to the current directory. The Python
CLI reads code, schemas, and built-in registries from the installed package, but
writes runtime state to:

```text
<current-directory>/harness/harness.db
<current-directory>/harness/prompts/
<current-directory>/harness/runs/
```

Set `MY_HARNESS_DB` when you need a custom database path.

## Publish To npm

Only publish after `harness check` passes and the release tag exists.

```powershell
npm pack --dry-run
npm publish --access public
```

Recommended package strategy:

- publish patch versions for launcher/package fixes, for example `0.10.1`;
- keep Git tags immutable;
- keep historical source testing through Git tags;
- do not promise npm packages for old milestones unless that package was
  actually published at the time.

## Release Checklist

Before a new version is announced:

- `harness.yaml` version is updated.
- `package.json` version matches the release package.
- `README.md` describes the user-visible capability surface.
- `harness/features.json` has evidence.
- `harness/progress.md` records verification.
- `.\harness\harness.ps1 check --include-active --strict-active` passes.
- `npm pack --dry-run` shows only intended files.
- Git tag and GitHub release notes point to the acceptance evidence.
