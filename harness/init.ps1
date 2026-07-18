$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

Write-Host "==> Repository root: $root"

$required = @(
  "AGENTS.md",
  "README.md",
  "harness.yaml",
  "harness/features.json",
  "harness/progress.md",
  "docs/INTAKE.md",
  "docs/WORKFLOWS.md",
  "docs/VERIFICATION.md",
  "docs/HUMAN_GATE.md"
)

$missing = @()
foreach ($path in $required) {
  if (-not (Test-Path $path)) {
    $missing += $path
  }
}

if ($missing.Count -gt 0) {
  Write-Error ("Missing required files: " + ($missing -join ", "))
}

Get-Content "harness/features.json" -Raw | ConvertFrom-Json | Out-Null

python "cli/harness.py" init | Out-Null

Write-Host "==> Required files present"
Write-Host "==> features.json parses"
Write-Host "==> harness SQLite state initialized"
Write-Host "==> Next: read harness/progress.md and classify the requested work"
