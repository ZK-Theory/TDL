$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun'

$root = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun'
$logDir = Join-Path $root 'results\trajectory_tda_integration\stage1\job_logs'
$controllerName = 'resume-jobs-06-07-2026-05-29'
$controllerStatusPath = Join-Path $logDir "$controllerName.status.json"
$controllerLogPath = Join-Path $logDir "$controllerName.log"
$startedController = Get-Date
$stepResults = @()

function Write-Utf8Json($Path, $Object) {
  $json = $Object | ConvertTo-Json -Depth 40
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $json, $utf8NoBom)
}

function Command-Text([object[]]$CommandArgs) {
  return ($CommandArgs | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' '
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
    poll_policy = 'Resume controller is sequential and unattended; inspect this status JSON hourly if desired.'
  })
}

function Invoke-Native([object[]]$CommandArgs, $StdoutPath, $StderrPath) {
  $oldErrorAction = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & $CommandArgs[0] @($CommandArgs[1..($CommandArgs.Count - 1)]) 1> $StdoutPath 2> $StderrPath
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $oldErrorAction
  return $exitCode
}

function Invoke-Validation($Job, $Index, [object[]]$CommandArgs) {
  $validationLog = Join-Path $logDir "$Job.validation-$Index.log"
  Add-Content -LiteralPath $validationLog -Value ("{0} | VALIDATION START | {1}" -f (Get-Date).ToString('o'), (Command-Text $CommandArgs)) -Encoding UTF8
  $oldErrorAction = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  $output = & $CommandArgs[0] @($CommandArgs[1..($CommandArgs.Count - 1)]) 2>&1
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $oldErrorAction
  foreach ($line in $output) {
    Add-Content -LiteralPath $validationLog -Value ([string]$line) -Encoding UTF8
  }
  Add-Content -LiteralPath $validationLog -Value ("{0} | VALIDATION END | exit_code={1}" -f (Get-Date).ToString('o'), $exitCode) -Encoding UTF8
  return [ordered]@{ command = (Command-Text $CommandArgs); exit_code = $exitCode; log = $validationLog }
}

function Invoke-Step($Job, [object[]]$CommandArgs, $OutputPath, $OutputPattern, [object[]]$ValidationCommands) {
  Write-ControllerStatus 'running' $Job
  $statusPath = Join-Path $logDir "$Job.status.json"
  $stdoutPath = Join-Path $logDir "$Job.stdout.log"
  $stderrPath = Join-Path $logDir "$Job.stderr.log"
  $phasePath = Join-Path $logDir "$Job.phase-status.log"
  $started = Get-Date
  $env:STAGE1_STATUS_FILE = $phasePath
  Add-Content -LiteralPath $phasePath -Value ("{0} | CONTROLLER LAUNCH | {1}" -f $started.ToString('s'), (Command-Text $CommandArgs)) -Encoding UTF8
  Write-Utf8Json $statusPath ([ordered]@{
    job = $Job
    status = 'running'
    started = $started.ToString('o')
    command = (Command-Text $CommandArgs)
    output = $OutputPath
    output_pattern = $OutputPattern
    stdout = $stdoutPath
    stderr = $stderrPath
    phase_status = $phasePath
    poll_policy = 'Resume controller; status updates when this step completes.'
  })

  $exitCode = Invoke-Native $CommandArgs $stdoutPath $stderrPath
  $finished = Get-Date
  $resolvedOutput = $OutputPath
  if (-not $resolvedOutput -and $OutputPattern) {
    $candidate = Get-ChildItem -Path $OutputPattern -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 1
    if ($candidate) { $resolvedOutput = $candidate.FullName }
  }
  $outputExists = $resolvedOutput -and (Test-Path -LiteralPath $resolvedOutput)
  if ($exitCode -ne 0 -or -not $outputExists) {
    $record = [ordered]@{
      job = $Job; status = 'failed'; started = $started.ToString('o'); finished = $finished.ToString('o')
      elapsed_seconds = [math]::Round(($finished - $started).TotalSeconds, 1)
      exit_code = $exitCode; output = $resolvedOutput; output_exists = $outputExists
      stdout = $stdoutPath; stderr = $stderrPath; phase_status = $phasePath
    }
    Write-Utf8Json $statusPath $record
    $script:stepResults += $record
    throw "$Job failed before validation (exit_code=$exitCode, output_exists=$outputExists)"
  }

  $validationResults = @()
  for ($i = 0; $i -lt $ValidationCommands.Count; $i++) {
    $validation = Invoke-Validation $Job ($i + 1) ([object[]]$ValidationCommands[$i])
    $validationResults += $validation
    if ($validation.exit_code -ne 0) {
      $record = [ordered]@{
        job = $Job; status = 'failed_validation'; started = $started.ToString('o'); finished = (Get-Date).ToString('o')
        elapsed_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)
        exit_code = $exitCode; output = $resolvedOutput; output_exists = $outputExists
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
    exit_code = $exitCode; output = $resolvedOutput; output_exists = $outputExists
    validations = $validationResults; stdout = $stdoutPath; stderr = $stderrPath; phase_status = $phasePath
  }
  Write-Utf8Json $statusPath $record
  $script:stepResults += $record
  Add-Content -LiteralPath $phasePath -Value ("{0} | CONTROLLER DONE | output={1}" -f (Get-Date).ToString('s'), $resolvedOutput) -Encoding UTF8
  return $record
}

Write-ControllerStatus 'running' 'initialising'
Add-Content -LiteralPath $controllerLogPath -Value ("{0} | resume controller started" -f $startedController.ToString('o')) -Encoding UTF8

try {
  Invoke-Step `
    'job-06-stratified-markov1-frozen-2026-05-29' `
    @('uv','run','--env-file','.env','python','-m','trajectory_tda.scripts.run_stratified_battery','--usoc-dir','C:\Users\steph\TDL\results\trajectory_tda_integration','--bhps-dir','C:\Users\steph\TDL\results\trajectory_tda_bhps','--n-perms','100','--landmarks','5000','--seed','42','--frozen-loadings','--output','results\trajectory_tda_integration\stratified_markov\stratified_markov1_W2_L5000_frozen_2026-05-29.json') `
    (Join-Path $root 'results\trajectory_tda_integration\stratified_markov\stratified_markov1_W2_L5000_frozen_2026-05-29.json') `
    $null `
    (,@('uv','run','pytest','tests/trajectory_tda/test_stratified_markov_contracts.py::test_stratified_markov1_output_json_validation_contract')) | Out-Null

  Invoke-Step `
    'job-07-frozen-comparison-2026-05-29' `
    @('uv','run','python','trajectory_tda/scripts/stage1/build_frozen_vs_provisional_comparison.py') `
    $null `
    (Join-Path $root 'results\trajectory_tda_integration\stage1\frozen_vs_provisional_comparison_*.json') `
    @(
      @('uv','run','pytest','tests/trajectory_tda/test_stage1_comparison_contracts.py::test_frozen_vs_provisional_comparison_json_validation_contract'),
      @('uv','run','python','.claude/hooks/contract_binding_check.py','--all-jsons')
    ) | Out-Null

  Write-ControllerStatus 'success' 'complete'
  Add-Content -LiteralPath $controllerLogPath -Value ("{0} | resume controller completed successfully" -f (Get-Date).ToString('o')) -Encoding UTF8
} catch {
  $message = $_.Exception.Message
  Write-ControllerStatus 'failed' 'failed' $message
  Add-Content -LiteralPath $controllerLogPath -Value ("{0} | resume controller failed | {1}" -f (Get-Date).ToString('o'), $message) -Encoding UTF8
  exit 1
}
