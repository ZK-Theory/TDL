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

if (-not $env:TDL_GATE6_ROOT_GRANT) {
    throw "TDL_GATE6_ROOT_GRANT must name the pre-created immutable capability-read-only root grant"
}
if (-not $env:TDL_GATE6_ENVELOPE_OUTPUT) {
    throw "TDL_GATE6_ENVELOPE_OUTPUT must name a new immutable eligibility-envelope output outside the dossier roots"
}

$python = $null
if ($env:TDL_PYTHON) {
    if (-not (Test-PytestInterpreter -Candidate $env:TDL_PYTHON)) {
        throw "TDL_PYTHON must name an existing Python interpreter with pytest importable: $($env:TDL_PYTHON)"
    }
    $python = (Resolve-Path -LiteralPath $env:TDL_PYTHON).Path
} else {
    foreach ($candidate in @(
        (Join-Path $repositoryRoot ".venv\Scripts\python.exe"),
        (Join-Path $ownerTdlRoot ".venv\Scripts\python.exe")
    )) {
        if (Test-PytestInterpreter -Candidate $candidate) {
            $python = (Resolve-Path -LiteralPath $candidate).Path
            break
        }
    }
}
if (-not $python) {
    throw "Gate 6 real-dossier certification requires TDL_PYTHON or a local Python interpreter with pytest"
}

if (-not $env:TDL_REPOSITORY_ROOT) {
    $env:TDL_REPOSITORY_ROOT = $ownerTdlRoot
}
if (-not $env:TDA_VAULT_ROOT) {
    $env:TDA_VAULT_ROOT = Join-Path $env:TDL_REPOSITORY_ROOT "vault"
}
$contractRoot = Join-Path $env:TDL_REPOSITORY_ROOT ".research-system\contracts\wp6-4"
$previousRequireRealDossier = [Environment]::GetEnvironmentVariable("TDL_REQUIRE_REAL_DOSSIER", "Process")
$env:TDL_REQUIRE_REAL_DOSSIER = "1"

Push-Location -LiteralPath $repositoryRoot
try {
    & (Join-Path $PSScriptRoot "certify_wp6_6_real_dossier.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "WP6.6 real-dossier certification failed with exit code $LASTEXITCODE"
    }
    & $python -m research_system.cli gate6 certify `
        --repository-root $repositoryRoot `
        --repository-contract-root $contractRoot `
        --vault-root $env:TDA_VAULT_ROOT `
        --root-grant $env:TDL_GATE6_ROOT_GRANT `
        --output $env:TDL_GATE6_ENVELOPE_OUTPUT
    if ($LASTEXITCODE -ne 0) {
        throw "Gate 6 eligibility-envelope certification failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
    [Environment]::SetEnvironmentVariable("TDL_REQUIRE_REAL_DOSSIER", $previousRequireRealDossier, "Process")
}
