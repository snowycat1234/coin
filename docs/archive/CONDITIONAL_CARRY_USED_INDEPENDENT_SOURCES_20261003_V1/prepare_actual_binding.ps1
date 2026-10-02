$ErrorActionPreference='Stop'
$root='D:\codex\coin'
$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state'
$work=Join-Path $state 'test-conditional-carry-independent-audit-20261003-v1'
try {
  $protocol='protocols/CONDITIONAL_CARRY_ACCOUNT_122D_20261003_V1.json'
  $actual='reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_122D_ACTUAL_20261003_V1.json'
  $spec=Get-Content -LiteralPath (Join-Path $root $protocol) -Raw -Encoding UTF8 | ConvertFrom-Json
  $report=Get-Content -LiteralPath (Join-Path $root $actual) -Raw -Encoding UTF8 | ConvertFrom-Json
  $smoke=Get-Content -LiteralPath (Join-Path $root $spec.required_smoke_receipt) -Raw -Encoding UTF8 | ConvertFrom-Json
  $reader='docs/archive/BASIS_RISK_USED_INDEPENDENT_SOURCES_20261003_V1/audit.py'
  $small=[ordered]@{}
  foreach($entry in $spec.frozen_sources.PSObject.Properties) {
    $digest=(Get-FileHash -LiteralPath (Join-Path $root $entry.Name) -Algorithm SHA256).Hash.ToLowerInvariant()
    if($digest -ne $entry.Value){throw ('Frozen source mismatch: '+$entry.Name)}
    $small['/mnt/d/codex/coin/'+$entry.Name]=$digest
  }
  foreach($name in @($protocol,$actual,$spec.required_smoke_receipt,$reader)) {
    $small['/mnt/d/codex/coin/'+$name]=(Get-FileHash -LiteralPath (Join-Path $root $name) -Algorithm SHA256).Hash.ToLowerInvariant()
  }
  $tasks=@($report.binding.task_id,$smoke.binding.task_id)
  foreach($id in $tasks) {
    $path=Join-Path $state ('task-progress/task-'+$id+'.json')
    $task=Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    if($task.id -ne $id -or $task.status -ne 'completed' -or $task.exit_code -ne 0 -or !$task.pid -or !$task.start_ticks){throw ('Task not actual completed0: '+$id)}
    $small['/home/xflops/coin-state/task-progress/task-'+$id+'.json']=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
  }
  $runFile=Join-Path $state 'conditional-carry-account-122d-actual-20261003-v1/RUN_BINDING.json'
  $small['/home/xflops/coin-state/conditional-carry-account-122d-actual-20261003-v1/RUN_BINDING.json']=(Get-FileHash -LiteralPath $runFile -Algorithm SHA256).Hash.ToLowerInvariant()
  $binding=[ordered]@{
    created_utc=[DateTime]::UtcNow.ToString('o')
    checker_sha256=(Get-FileHash -LiteralPath (Join-Path $work 'audit.py') -Algorithm SHA256).Hash.ToLowerInvariant()
    protocol_path=$protocol;actual_report_path=$actual;actual_task_id=$report.binding.task_id
    actual_host_session=10927;actual_exit_code=0
    price_reader_path='/mnt/d/codex/coin/'+$reader
    price_reader_sha256=$small['/mnt/d/codex/coin/'+$reader]
    small_inputs=$small
    cash_absolute_tolerance_USDT='1e-7';ratio_absolute_tolerance='1e-10'
    own_memory_budget_bytes=512000000;wall_seconds_budget=600
    exact_invocation='bash scripts/with_task_progress.sh --title 条件carry连续账户独立账本审计 -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 CUDA_VISIBLE_DEVICES=-1 /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python /home/xflops/coin-state/test-conditional-carry-independent-audit-20261003-v1/audit.py'
    scope='ONE_NEW_ACCOUNT_ORIGINAL32_PARQUETS_NO_RAW_ZIP_CRC_API_OR_SIMULATE_ACCOUNT'
  }
  $target=Join-Path $work 'ACTUAL_BINDING.json'
  if(Test-Path -LiteralPath $target){throw 'New binding already exists'}
  [IO.File]::WriteAllText($target,($binding|ConvertTo-Json -Depth 10)+"`n",[Text.UTF8Encoding]::new($false))
  Get-FileHash -LiteralPath $target -Algorithm SHA256 | Select-Object Hash
  $binding | Select-Object checker_sha256,actual_task_id,price_reader_sha256 | ConvertTo-Json
} catch {
  $fail=Join-Path $work 'BINDING_PREPARATION_FAILURE_20261003_V1.json'
  if(!(Test-Path -LiteralPath $fail)){[IO.File]::WriteAllText($fail,(@{status='FAIL_METADATA_BEFORE_PYTHON_OR_ARRAYS';reason=$_.Exception.Message;actual_exit_code=1}|ConvertTo-Json)+"`n",[Text.UTF8Encoding]::new($false))}
  throw
}