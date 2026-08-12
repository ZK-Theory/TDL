[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ownerTdlRoot = Join-Path ([Environment]::GetFolderPath("UserProfile")) "TDL"
$python = if ($env:TDL_PYTHON) {
    $env:TDL_PYTHON
} elseif (Test-Path -LiteralPath (Join-Path $repositoryRoot ".venv\Scripts\python.exe") -PathType Leaf) {
    Join-Path $repositoryRoot ".venv\Scripts\python.exe"
} else {
    Join-Path $ownerTdlRoot ".venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "WP6.6 certification requires $python"
}

if (-not $env:TDL_REPOSITORY_ROOT) {
    $env:TDL_REPOSITORY_ROOT = $ownerTdlRoot
}
if (-not $env:TDA_VAULT_ROOT) {
    $env:TDA_VAULT_ROOT = Join-Path $env:TDL_REPOSITORY_ROOT "vault"
}
$previousRequireRealDossier = [Environment]::GetEnvironmentVariable("TDL_REQUIRE_REAL_DOSSIER", "Process")
$env:TDL_REQUIRE_REAL_DOSSIER = "1"

Push-Location -LiteralPath $repositoryRoot
try {
    & $python -m pytest -q `
        tests/research_system/integration/test_wp6_6_dossier_admission.py `
        -o "addopts=" -p no:cacheprovider -p no:randomly -p no:cov
    if ($LASTEXITCODE -ne 0) {
        throw "WP6.6 real-dossier certification failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
    [Environment]::SetEnvironmentVariable("TDL_REQUIRE_REAL_DOSSIER", $previousRequireRealDossier, "Process")
}
