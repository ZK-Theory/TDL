$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun'
$root = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun'
$logDir = Join-Path $root 'results\trajectory_tda_integration\stage1\job_logs'
$controllerName = 'overnight-jobs-05-07-2026-05-29'
$controllerStatusPath = Join-Path $logDir "$controllerName.status.json"
$controllerLogPath = Join-Path $logDir "$controllerName.log"
$startedController = Get-Date
$stepResults = @()

function Write-Utf8Json($Path, $Object) {
  $json = $Object | ConvertTo-Json -Depth 40
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $json, $utf8NoBom)
}

function Write-ControllerStatus($Status, $CurrentStep, $ErrorMessage = $null) {
  Write-Utf8Json $controllerStatusPath ([ordered]@{
    controller = $controllerName
    status = $Status
    started = $startedController.ToString('o')
    updated = (Get-Date).ToString('o')
    current_step = $CurrentStep
    steps = $script:stepResults
    error = $ErrorMessage
    log = $controllerLogPath
    poll_policy = 'Controller is sequential and unattended; inspect this status JSON hourly if desired.'
  })
}

function Append-Line($Path, $Line) {
  Add-Content -LiteralPath $Path -Value $Line -Encoding UTF8
}

function Command-Text($CommandArgs) {
  return ($CommandArgs | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' '
}

function Find-Output($OutputDir, $OutputPattern, $Started, $FixedOutput) {
  if ($FixedOutput -and (Test-Path -LiteralPath $FixedOutput)) {
    return (Get-Item -LiteralPath $FixedOutput).FullName
  }
  $candidate = Get-ChildItem -LiteralPath $OutputDir -Filter $OutputPattern -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -ge $Started } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($candidate) { return $candidate.FullName }
  return $null
}

function Invoke-Validation($Job, $Index, $CommandArgs) {
  $validationLog = Join-Path $logDir "$Job.validation-$Index.log"
  Append-Line $validationLog ("{0} | VALIDATION START | {1}" -f (Get-Date).ToString('o'), (Command-Text $CommandArgs))
  $oldErrorAction = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & $CommandArgs[0] @($CommandArgs[1..($CommandArgs.Count - 1)]) 1>> $validationLog 2>&1
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $oldErrorAction
  Append-Line $validationLog ("{0} | VALIDATION END | exit_code={1}" -f (Get-Date).ToString('o'), $exitCode)
  return [ordered]@{ command = (Command-Text $CommandArgs); exit_code = $exitCode; log = $validationLog }
}

function Invoke-Step($Job, $CommandArgs, $OutputDir, $OutputPattern, $FixedOutput, $ValidationCommands) {
  Write-ControllerStatus 'running' $Job
  $statusPath = Join-Path $logDir "$Job.status.json"
  $stdoutPath = Join-Path $logDir "$Job.stdout.log"
  $stderrPath = Join-Path $logDir "$Job.stderr.log"
  $phasePath = Join-Path $logDir "$Job.phase-status.log"
  $started = Get-Date
  $env:STAGE1_STATUS_FILE = $phasePath
  Append-Line $phasePath ("{0} | CONTROLLER LAUNCH | {1}" -f $started.ToString('s'), (Command-Text $CommandArgs))
  Write-Utf8Json $statusPath ([ordered]@{
    job = $Job
    status = 'running'
    started = $started.ToString('o')
    command = (Command-Text $CommandArgs)
    output = $FixedOutput
    output_pattern = (Join-Path $OutputDir $OutputPattern)
    stdout = $stdoutPath
    stderr = $stderrPath
    phase_status = $phasePath
    poll_policy = 'Unattended sequential controller; status updates when this step completes.'
  })

  $oldErrorAction = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & $CommandArgs[0] @($CommandArgs[1..($CommandArgs.Count - 1)]) 1> $stdoutPath 2> $stderrPath
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $oldErrorAction

  $finished = Get-Date
  $outputPath = Find-Output $OutputDir $OutputPattern $started $FixedOutput
  $outputExists = $null -ne $outputPath
  if ($exitCode -ne 0 -or -not $outputExists) {
    $record = [ordered]@{
      job = $Job; status = 'failed'; started = $started.ToString('o'); finished = $finished.ToString('o')
      elapsed_seconds = [math]::Round(($finished - $started).TotalSeconds, 1)
      exit_code = $exitCode; output = $outputPath; output_exists = $outputExists
      stdout = $stdoutPath; stderr = $stderrPath; phase_status = $phasePath
    }
    Write-Utf8Json $statusPath $record
    $script:stepResults += $record
    throw "$Job failed before validation (exit_code=$exitCode, output_exists=$outputExists)"
  }

  $validationResults = @()
  for ($i = 0; $i -lt $ValidationCommands.Count; $i++) {
    $validation = Invoke-Validation $Job ($i + 1) $ValidationCommands[$i]
    $validationResults += $validation
    if ($validation.exit_code -ne 0) {
      $record = [ordered]@{
        job = $Job; status = 'failed_validation'; started = $started.ToString('o'); finished = (Get-Date).ToString('o')
        elapsed_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)
        exit_code = $exitCode; output = $outputPath; output_exists = $outputExists
        validations = $validationResults; stdout = $stdoutPath; stderr = $stderrPath; phase_status = $phasePath
      }
      Write-Utf8Json $statusPath $record
      $script:stepResults += $record
      throw "$Job validation failed: $($validation.command)"
    }
  }

  $finishedWithValidation = Get-Date
  $record = [ordered]@{
    job = $Job; status = 'success'; started = $started.ToString('o'); finished = $finishedWithValidation.ToString('o')
    elapsed_seconds = [math]::Round(($finishedWithValidation - $started).TotalSeconds, 1)
    exit_code = $exitCode; output = $outputPath; output_exists = $outputExists
    validations = $validationResults; stdout = $stdoutPath; stderr = $stderrPath; phase_status = $phasePath
  }
  Write-Utf8Json $statusPath $record
  $script:stepResults += $record
  Append-Line $phasePath ("{0} | CONTROLLER DONE | output={1}" -f (Get-Date).ToString('s'), $outputPath)
  return $record
}

Write-ControllerStatus 'running' 'initialising'
Append-Line $controllerLogPath ("{0} | controller started" -f $startedController.ToString('o'))

try {
  Invoke-Step `
    'job-05-bhps-length-truncate-frozen-2026-05-29' `
    @('uv','run','--env-file','.env','python','trajectory_tda/scripts/stage1/run_bhps_length_matched.py','--strategy','truncate','--L','5000','--B','1000','--seed','42','--n-null-pairs','500','--n-jobs','4','--frozen-loadings') `
    (Join-Path $root 'results\trajectory_tda_bhps\stage1') `
    'bhps_length_matched_truncate_frozen_*.json' `
    $null `
    @(@('uv','run','pytest','tests/trajectory_tda/test_stage1_output_json_validation.py::test_stage1_output_jsons_validate_against_aggregate_schema')) | Out-Null

  Invoke-Step `
    'job-06-stratified-markov1-frozen-2026-05-29' `
    @('uv','run','--env-file','.env','python','-m','trajectory_tda.scripts.run_stratified_battery','--usoc-dir','C:\Users\steph\TDL\results\trajectory_tda_integration','--bhps-dir','C:\Users\steph\TDL\results\trajectory_tda_bhps','--n-perms','100','--landmarks','5000','--seed','42','--frozen-loadings','--output','results\trajectory_tda_integration\stratified_markov\stratified_markov1_W2_L5000_frozen_2026-05-29.json') `
    (Join-Path $root 'results\trajectory_tda_integration\stratified_markov') `
    'stratified_markov1_W2_L5000_frozen_*.json' `
    (Join-Path $root 'results\trajectory_tda_integration\stratified_markov\stratified_markov1_W2_L5000_frozen_2026-05-29.json') `
    @(@('uv','run','pytest','tests/trajectory_tda/test_stratified_markov_contracts.py::test_stratified_markov1_output_json_validation_contract')) | Out-Null

  Invoke-Step `
    'job-07-frozen-comparison-2026-05-29' `
    @('uv','run','python','trajectory_tda/scripts/stage1/build_frozen_vs_provisional_comparison.py') `
    (Join-Path $root 'results\trajectory_tda_integration\stage1') `
    'frozen_vs_provisional_comparison_*.json' `
    $null `
    @(
      @('uv','run','pytest','tests/trajectory_tda/test_stage1_comparison_contracts.py::test_frozen_vs_provisional_comparison_json_validation_contract'),
      @('uv','run','python','.claude/hooks/contract_binding_check.py','--all-jsons')
    ) | Out-Null

  Write-ControllerStatus 'success' 'complete'
  Append-Line $controllerLogPath ("{0} | controller completed successfully" -f (Get-Date).ToString('o'))
} catch {
  $message = $_.Exception.Message
  Write-ControllerStatus 'failed' 'failed' $message
  Append-Line $controllerLogPath ("{0} | controller failed | {1}" -f (Get-Date).ToString('o'), $message)
  exit 1
}
