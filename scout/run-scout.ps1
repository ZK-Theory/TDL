# scout/run-scout.ps1 - weekly Scout gather via Codex CLI.
# Registered as a Windows Task Scheduler job (~20:00 local, weekly). Runs as the logged-in
# user so Codex uses the per-user auth in ~/.codex. Part of the TDL Discovery harness:
# docs/plans/strategy/Discovery-Harness-Plan-16-06-2026.md
#
# Uses Start-Process with file redirects (NOT a native-exe pipe + `*>>`): in Windows
# PowerShell 5.1, redirecting a native exe's stderr through the pipeline wraps each stderr
# line as a terminating NativeCommandError, so a single benign Codex log line aborts the
# run. Start-Process writes the streams straight to files and never does that.
#
# NOT yet scheduled - run this once interactively first to confirm Codex reaches the
# network and writes the inbox note under `-s workspace-write`. If network is blocked in
# that sandbox mode, switch to the $codexArgs line with the network override (confirm the
# exact key for your Codex version with `codex exec --help` / `codex doctor`).

$repo  = 'C:\Users\steph\TDL'
$codex = 'C:\Users\steph\AppData\Local\Programs\OpenAI\Codex\bin\codex.exe'  # version-stable symlink
$job   = Join-Path $repo 'scout\scout-weekly-job.md'

$logDir = Join-Path $repo 'scout\logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$stamp  = Get-Date -Format 'yyyy-MM-dd'
$outLog = Join-Path $logDir "scout-$stamp.out.log"
$errLog = Join-Path $logDir "scout-$stamp.err.log"

if (-not (Test-Path $codex)) { Write-Error "Codex CLI not found at $codex"; exit 2 }
if (-not (Test-Path $job))   { Write-Error "Scout job prompt not found at $job"; exit 2 }

# Gather only, no commits. workspace-write lets Codex create the inbox note; the repo's
# .codex/hooks.json still applies. Prompt is fed on stdin from the job file.
$codexArgs = @('exec', '--cd', $repo, '--sandbox', 'workspace-write', '-')
# 2026-06-16 test: workspace-write reached OpenAlex + arXiv fine - the override below is NOT needed.
# Network-enabled variant (only if a future run shows workspace-write blocks outbound HTTP):
# $codexArgs = @('exec','--cd',$repo,'--sandbox','workspace-write','-c','sandbox_workspace_write.network_access=true','-')

Write-Host "[$(Get-Date -Format o)] Scout run starting -> $outLog / $errLog"

$proc = Start-Process -FilePath $codex -ArgumentList $codexArgs `
  -RedirectStandardInput $job -RedirectStandardOutput $outLog -RedirectStandardError $errLog `
  -NoNewWindow -Wait -PassThru

Write-Host "[$(Get-Date -Format o)] Scout run finished (exit $($proc.ExitCode))"
exit $proc.ExitCode
