$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun'
$env:STAGE1_STATUS_FILE = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-02-bhps-headline-frozen-2026-05-28.phase-status.log'
$statusPath = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-02-bhps-headline-frozen-2026-05-28.status.json'
$stdoutPath = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-02-bhps-headline-frozen-2026-05-28.stdout.log'
$stderrPath = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-02-bhps-headline-frozen-2026-05-28.stderr.log'
$outputPath = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_bhps\stage1\bhps_headline_frozen_2026-05-28.json'
$started = Get-Date
[ordered]@{
  job = 'job-02-bhps-headline-frozen-2026-05-28'
  status = 'running'
  started = $started.ToString('o')
  output = $outputPath
  stdout = $stdoutPath
  stderr = $stderrPath
  phase_status = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-02-bhps-headline-frozen-2026-05-28.phase-status.log'
  command = 'uv run --env-file .env python trajectory_tda/scripts/stage1/run_bhps_headline.py --L 5000 --B 1000 --seed 42 --n-null-pairs 500 --n-jobs 4 --frozen-loadings'
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statusPath -Encoding UTF8
$proc = Start-Process -FilePath 'uv' -ArgumentList @('run','--env-file','.env','python','trajectory_tda/scripts/stage1/run_bhps_headline.py','--L','5000','--B','1000','--seed','42','--n-null-pairs','500','--n-jobs','4','--frozen-loadings') -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru -NoNewWindow
$proc.WaitForExit()
$finished = Get-Date
$status = if ($proc.ExitCode -eq 0 -and (Test-Path -LiteralPath $outputPath)) { 'success' } else { 'failed' }
[ordered]@{
  job = 'job-02-bhps-headline-frozen-2026-05-28'
  status = $status
  started = $started.ToString('o')
  finished = $finished.ToString('o')
  elapsed_seconds = [math]::Round(($finished - $started).TotalSeconds, 1)
  exit_code = $proc.ExitCode
  output = $outputPath
  output_exists = (Test-Path -LiteralPath $outputPath)
  stdout = $stdoutPath
  stderr = $stderrPath
  phase_status = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun\results\trajectory_tda_integration\stage1\job_logs\job-02-bhps-headline-frozen-2026-05-28.phase-status.log'
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statusPath -Encoding UTF8
if ($status -ne 'success') { exit 1 }
