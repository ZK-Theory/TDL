<#
.SYNOPSIS
    Run a sequence of native commands, stopping at the first nonzero exit code.

.DESCRIPTION
    Why (obs 142): PowerShell reports only the LAST native process's exit
    code. `commandA; commandB` where A fails and B succeeds returns B's
    (zero) exit code — a later success silently erases an earlier failure,
    and a validation bundle chained this way can report green while one of
    its checks actually failed. `$ErrorActionPreference = 'Stop'` does not
    fix this: it governs terminating PowerShell errors, not native-process
    exit codes.

    Pass each command as a scriptblock. Each is invoked in turn; `$LASTEXITCODE`
    (and `$?` for the rare non-native-exe block) is checked immediately after
    it runs, before any later command can overwrite it. The runner stops and
    exits with the first failing command's exit code.

.EXAMPLE
    .\tools\invoke_checked.ps1 -Commands @(
        { uv run ruff check . },
        { uv run pytest tests/tools }
    )

.NOTES
    Invoke this with `-File` (or `&` from within an already-running script/
    session), not `powershell.exe -Command "& '...\invoke_checked.ps1' ..."`
    from an external process. Windows PowerShell 5.1's `-Command` does not
    propagate an inner script's `exit N` as the outer process's exit code
    when the script is called via `&` from inside the command string — it
    collapses any failing exit to a generic 1, losing which step failed and
    its exact code (though it stays nonzero, so it will not resurrect the
    silent-success defect this script exists to prevent).
#>

param(
    [Parameter(Mandatory = $true)]
    [scriptblock[]]$Commands
)

$stepIndex = 0
foreach ($cmd in $Commands) {
    $stepIndex++
    $global:LASTEXITCODE = 0
    & $cmd
    $cmdletFailed = -not $?
    $nativeFailed = ($LASTEXITCODE -ne 0)
    if ($nativeFailed -or $cmdletFailed) {
        $code = if ($nativeFailed) { $LASTEXITCODE } else { 1 }
        Write-Error "invoke_checked: step $stepIndex failed (exit code $code) - stopping before later steps can mask it."
        exit $code
    }
}
exit 0
