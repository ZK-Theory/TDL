[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ownerTdlRoot = Join-Path ([Environment]::GetFolderPath("UserProfile")) "TDL"

function Test-PytestInterpreter {
    param([Parameter(Mandatory = $true)][string]$Candidate)

    if (-not (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
        return $false
    }
    try {
        & $Candidate -c "import pytest" *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

$python = $null
$uvPath = $null
if ($env:TDL_PYTHON) {
    if (-not (Test-PytestInterpreter -Candidate $env:TDL_PYTHON)) {
        throw "TDL_PYTHON must name an existing Python interpreter with pytest importable: $($env:TDL_PYTHON)"
    }
    $python = (Resolve-Path -LiteralPath $env:TDL_PYTHON).Path
} else {
    $candidates = @(
        (Join-Path $repositoryRoot ".venv\Scripts\python.exe"),
        (Join-Path $ownerTdlRoot ".venv\Scripts\python.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-PytestInterpreter -Candidate $candidate) {
            $python = (Resolve-Path -LiteralPath $candidate).Path
            break
        }
    }
    if (-not $python) {
        $uv = Get-Command uv -ErrorAction SilentlyContinue
        if (-not $uv) {
            throw "WP6.6 certification requires a Python interpreter with pytest importable, or uv on PATH"
        }
        $uvPath = $uv.Source
        try {
            & $uvPath run --directory $repositoryRoot --group dev python -c "import pytest" *> $null
            $uvReady = $LASTEXITCODE -eq 0
        } catch {
            $uvReady = $false
        }
        if (-not $uvReady) {
            throw "WP6.6 certification could not provision pytest through uv run --group dev"
        }
    }
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
    if ($python) {
        Write-Host "WP6.6 certification Python: $python"
        & $python -m pytest -q `
            tests/research_system/integration/test_wp6_6_dossier_admission.py `
            -o "addopts=" -p no:cacheprovider -p no:randomly -p no:cov
    } else {
        Write-Host "WP6.6 certification Python: uv run --group dev python"
        & $uvPath run --directory $repositoryRoot --group dev python -m pytest -q `
            tests/research_system/integration/test_wp6_6_dossier_admission.py `
            -o "addopts=" -p no:cacheprovider -p no:randomly -p no:cov
    }
    if ($LASTEXITCODE -ne 0) {
        throw "WP6.6 real-dossier certification failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
    [Environment]::SetEnvironmentVariable("TDL_REQUIRE_REAL_DOSSIER", $previousRequireRealDossier, "Process")
}
