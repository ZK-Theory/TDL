$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun'

$root = 'C:\Users\steph\TDL\.apm\worktrees\run-headline-batch-frozen-pca-rerun'
$logDir = Join-Path $root 'results\trajectory_tda_integration\stage1\job_logs'
$controllerName = 'resume-jobs-06-08-2026-05-29'
$controllerStatusPath = Join-Path $logDir "$controllerName.status.json"
$controllerLogPath = Join-Path $logDir "$controllerName.log"
$startedController = Get-Date
$script:stepResults = @()

$usocPartial = Join-Path $root 'results\trajectory_tda_integration\stratified_markov\.partial\stratified_markov1_W2_L5000_frozen_usoc_2026-05-29.json'
$bhpsPartial = Join-Path $root 'results\trajectory_tda_integration\stratified_markov\.partial\stratified_markov1_W2_L5000_frozen_bhps_2026-05-29.json'
$stratifiedFinal = Join-Path $root 'results\trajectory_tda_integration\stratified_markov\stratified_markov1_W2_L5000_frozen_2026-05-29.json'
$comparisonOutput = Join-Path $root 'results\trajectory_tda_integration\stage1\frozen_vs_provisional_comparison_2026-05-29.json'

function Write-Utf8Json($Path, $Object) {
  $json = $Object | ConvertTo-Json -Depth 60
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
    poll_policy = 'Poll this status JSON hourly unless a step status reaches aggregation/DONE or a target output appears.'
    job_map = [ordered]@{
      job_06 = 'USoc stratified Markov-1 frozen partial'
      job_07 = 'BHPS stratified Markov-1 frozen partial plus final combined stratified JSON assembly'
      job_08 = 'Frozen-vs-provisional comparison JSON and contract validation'
    }
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
  $record = [ordered]@{ command = (Command-Text $CommandArgs); exit_code = $exitCode; log = $validationLog }
  if ($exitCode -ne 0) {
    throw "$Job validation failed: $($record.command)"
  }
  return $record
}

function Set-LastStepValidations($StatusPath, [object[]]$ValidationRecords) {
  if ($script:stepResults.Count -eq 0) { return }
  $lastIndex = $script:stepResults.Count - 1
  $record = $script:stepResults[$lastIndex]
  $record['validations'] = $ValidationRecords
  $script:stepResults[$lastIndex] = $record
  Write-Utf8Json $StatusPath $record
}

function Invoke-Step($Job, [object[]]$CommandArgs, $OutputPath) {
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
    stdout = $stdoutPath
    stderr = $stderrPath
    phase_status = $phasePath
    poll_policy = 'Step status updates when this command completes.'
  })

  $exitCode = Invoke-Native $CommandArgs $stdoutPath $stderrPath
  Remove-Item Env:\STAGE1_STATUS_FILE -ErrorAction SilentlyContinue
  $finished = Get-Date
  $outputExists = Test-Path -LiteralPath $OutputPath
  $status = if ($exitCode -eq 0 -and $outputExists) { 'success' } else { 'failed' }
  $record = [ordered]@{
    job = $Job
    status = $status
    started = $started.ToString('o')
    finished = $finished.ToString('o')
    elapsed_seconds = [math]::Round(($finished - $started).TotalSeconds, 1)
    exit_code = $exitCode
    output = $OutputPath
    output_exists = $outputExists
    stdout = $stdoutPath
    stderr = $stderrPath
    phase_status = $phasePath
  }
  Write-Utf8Json $statusPath $record
  $script:stepResults += $record
  if ($status -ne 'success') {
    throw "$Job failed before validation (exit_code=$exitCode, output_exists=$outputExists)"
  }
  Add-Content -LiteralPath $phasePath -Value ("{0} | CONTROLLER DONE | output={1}" -f (Get-Date).ToString('s'), $OutputPath) -Encoding UTF8
  return [ordered]@{ record = $record; status_path = $statusPath }
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $usocPartial) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $comparisonOutput) | Out-Null
Write-ControllerStatus 'running' 'initialising'
Add-Content -LiteralPath $controllerLogPath -Value ("{0} | corrected resume controller started" -f $startedController.ToString('o')) -Encoding UTF8

try {
  $job06 = 'job-06-usoc-stratified-markov1-frozen-2026-05-29'
  Invoke-Step `
    $job06 `
    @('uv','run','--env-file','.env','python','-m','trajectory_tda.scripts.run_stratified_battery','--dataset','usoc','--usoc-dir','C:\Users\steph\TDL\results\trajectory_tda_integration','--bhps-dir','C:\Users\steph\TDL\results\trajectory_tda_bhps','--n-perms','100','--landmarks','5000','--seed','42','--frozen-loadings','--output',$usocPartial) `
    $usocPartial | Out-Null

  $job07 = 'job-07-bhps-stratified-markov1-frozen-2026-05-29'
  $job07Step = Invoke-Step `
    $job07 `
    @('uv','run','--env-file','.env','python','-m','trajectory_tda.scripts.run_stratified_battery','--dataset','bhps','--usoc-dir','C:\Users\steph\TDL\results\trajectory_tda_integration','--bhps-dir','C:\Users\steph\TDL\results\trajectory_tda_bhps','--n-perms','100','--landmarks','5000','--seed','42','--frozen-loadings','--output',$bhpsPartial) `
    $bhpsPartial
  $job07Validations = @()
  $job07Validations += Invoke-Validation $job07 1 @('uv','run','python','-m','trajectory_tda.scripts.stage1.assemble_stratified_markov_partials','--usoc-partial',$usocPartial,'--bhps-partial',$bhpsPartial,'--output',$stratifiedFinal)
  $job07Validations += Invoke-Validation $job07 2 @('uv','run','pytest','tests/trajectory_tda/test_stratified_markov_contracts.py::test_stratified_markov1_output_json_validation_contract')
  Set-LastStepValidations $job07Step['status_path'] $job07Validations

  $job08 = 'job-08-frozen-comparison-2026-05-29'
  $job08Step = Invoke-Step `
    $job08 `
    @('uv','run','python','trajectory_tda/scripts/stage1/build_frozen_vs_provisional_comparison.py','--output',$comparisonOutput) `
    $comparisonOutput
  $job08Validations = @()
  $job08Validations += Invoke-Validation $job08 1 @('uv','run','pytest','tests/trajectory_tda/test_stage1_comparison_contracts.py::test_frozen_vs_provisional_comparison_json_validation_contract')
  $job08Validations += Invoke-Validation $job08 2 @('uv','run','python','.claude/hooks/contract_binding_check.py','--all-jsons')
  Set-LastStepValidations $job08Step['status_path'] $job08Validations

  Write-ControllerStatus 'success' 'complete'
  Add-Content -LiteralPath $controllerLogPath -Value ("{0} | corrected resume controller completed successfully" -f (Get-Date).ToString('o')) -Encoding UTF8
} catch {
  $message = $_.Exception.Message
  Write-ControllerStatus 'failed' 'failed' $message
  Add-Content -LiteralPath $controllerLogPath -Value ("{0} | corrected resume controller failed | {1}" -f (Get-Date).ToString('o'), $message) -Encoding UTF8
  exit 1
}
