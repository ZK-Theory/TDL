$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun'
$env:STAGE1_STATUS_FILE = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-01-usoc-headline-frozen-2026-05-28-v2.phase-status.log'
$statusPath = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-01-usoc-headline-frozen-2026-05-28-v2.status.json'
$logPath = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-01-usoc-headline-frozen-2026-05-28-v2.log'
$outputPath = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\usoc_headline_frozen_2026-05-28.json'
$started = Get-Date
[ordered]@{
  job = 'job-01-usoc-headline-frozen-2026-05-28-v2'
  status = 'running'
  started = $started.ToString('o')
  output = $outputPath
  command = 'uv run --env-file .env python trajectory_tda/scripts/stage1/run_usoc_headline.py --L 5000 --B 1000 --seed 42 --n-null-pairs 500 --n-jobs 4 --frozen-loadings'
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statusPath -Encoding UTF8
try {
  & uv run --env-file .env python trajectory_tda/scripts/stage1/run_usoc_headline.py --L 5000 --B 1000 --seed 42 --n-null-pairs 500 --n-jobs 4 --frozen-loadings *>&1 | Tee-Object -FilePath $logPath
  $exitCode = $LASTEXITCODE
  if ($exitCode -eq $null) { $exitCode = 0 }
  if ($exitCode -ne 0) { throw "uv exited with code $exitCode" }
  $finished = Get-Date
  [ordered]@{
    job = 'job-01-usoc-headline-frozen-2026-05-28-v2'
    status = 'success'
    started = $started.ToString('o')
    finished = $finished.ToString('o')
    elapsed_seconds = [math]::Round(($finished - $started).TotalSeconds, 1)
    output = $outputPath
    output_exists = (Test-Path -LiteralPath $outputPath)
    log = $logPath
    phase_status = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-01-usoc-headline-frozen-2026-05-28-v2.phase-status.log'
  } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statusPath -Encoding UTF8
} catch {
  $finished = Get-Date
  [ordered]@{
    job = 'job-01-usoc-headline-frozen-2026-05-28-v2'
    status = 'failed'
    started = $started.ToString('o')
    finished = $finished.ToString('o')
    elapsed_seconds = [math]::Round(($finished - $started).TotalSeconds, 1)
    output = $outputPath
    output_exists = (Test-Path -LiteralPath $outputPath)
    log = $logPath
    phase_status = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-01-usoc-headline-frozen-2026-05-28-v2.phase-status.log'
    error = $_.Exception.Message
  } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statusPath -Encoding UTF8
  throw
}
