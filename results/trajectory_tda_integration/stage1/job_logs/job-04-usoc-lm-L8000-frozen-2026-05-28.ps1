$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun'
$env:STAGE1_STATUS_FILE = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-04-usoc-lm-L8000-frozen-2026-05-28.phase-status.log'
$statusPath = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-04-usoc-lm-L8000-frozen-2026-05-28.status.json'
$stdoutPath = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-04-usoc-lm-L8000-frozen-2026-05-28.stdout.log'
$stderrPath = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-04-usoc-lm-L8000-frozen-2026-05-28.stderr.log'
$outputPath = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\lm_sensitivity_L8000_frozen_2026-05-28.json'
$started = Get-Date
$commandText = 'uv run --env-file .env python trajectory_tda/scripts/stage1/run_lm_sensitivity.py --L 8000 --B 1000 --seed 42 --n-null-pairs 500 --n-jobs 4 --frozen-loadings'
[ordered]@{
  job = 'job-04-usoc-lm-L8000-frozen-2026-05-28'
  status = 'running'
  started = $started.ToString('o')
  output = $outputPath
  stdout = $stdoutPath
  stderr = $stderrPath
  phase_status = $env:STAGE1_STATUS_FILE
  command = $commandText
  poll_policy = 'Use status JSON as completion signal; poll every 30 minutes, shortening when phase-status reaches aggregation/DONE or output appears.'
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statusPath -Encoding UTF8
$exitCode = $null
$errorMessage = $null
try {
  $oldErrorAction = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & uv run --env-file .env python trajectory_tda/scripts/stage1/run_lm_sensitivity.py --L 8000 --B 1000 --seed 42 --n-null-pairs 500 --n-jobs 4 --frozen-loadings 1> $stdoutPath 2> $stderrPath
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $oldErrorAction
} catch {
  $ErrorActionPreference = 'Stop'
  $errorMessage = $_.Exception.Message
  if ($null -eq $exitCode) { $exitCode = 1 }
}
$finished = Get-Date
$outputExists = Test-Path -LiteralPath $outputPath
$status = if ($exitCode -eq 0 -and $outputExists) { 'success' } else { 'failed' }
[ordered]@{
  job = 'job-04-usoc-lm-L8000-frozen-2026-05-28'
  status = $status
  started = $started.ToString('o')
  finished = $finished.ToString('o')
  elapsed_seconds = [math]::Round(($finished - $started).TotalSeconds, 1)
  exit_code = $exitCode
  error = $errorMessage
  output = $outputPath
  output_exists = $outputExists
  stdout = $stdoutPath
  stderr = $stderrPath
  phase_status = $env:STAGE1_STATUS_FILE
  command = $commandText
  poll_policy = 'Use status JSON as completion signal; poll every 30 minutes, shortening when phase-status reaches aggregation/DONE or output appears.'
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statusPath -Encoding UTF8
if ($status -ne 'success') { exit 1 }
