$ErrorActionPreference='Stop'
$root='D:/codex/coin';$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state';$sourceRoot="$state/carry-chronology-source-actual-20261003-v1";$work="$state/test-d031-source18-independent-audit-20261003-v1"
$producerName='reports/fast_research/CARRY_CHRONOLOGY_SOURCE_18_ACTUAL_20261003_V1.json';$protocolName='protocols/OFFICIAL_CARRY_CHRONOLOGY_SOURCE_20261003_V1.json';$qaName='scripts/investment/audit_carry_chronology_source.py'
$source=Get-Content -LiteralPath "$root/$producerName" -Raw | ConvertFrom-Json
if($source.status -ne 'OFFICIAL_CARRY_INPUT_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA' -or $source.completed_files -ne 18){throw 'Producer not complete18'}
$task=Get-Content -LiteralPath "$state/task-progress/task-$($source.binding.task_id).json" -Raw | ConvertFrom-Json
if($task.status -ne 'completed' -or $task.exit_code -ne 0){throw 'Actual producer not closed0'}
$small=[ordered]@{}
foreach($p in $source.binding.source_hashes.psobject.Properties){$small["/mnt/d/codex/coin/$($p.Name)"]=$p.Value}
foreach($name in @($producerName,$protocolName,$qaName,'reports/fast_research/CARRY_CHRONOLOGY_SOURCE_WRAPPER_LAUNCH_FAILURE_20261003_V1.json')){$small["/mnt/d/codex/coin/$name"]=(Get-FileHash -LiteralPath "$root/$name").Hash.ToLowerInvariant()}
$small['/home/xflops/coin-state/carry-chronology-source-actual-20261003-v1/RUN_BINDING.json']=(Get-FileHash -LiteralPath "$sourceRoot/RUN_BINDING.json").Hash.ToLowerInvariant()
$small['/home/xflops/coin-state/carry-chronology-source-actual-20261003-v1/RESOLVED_METADATA.json']=(Get-FileHash -LiteralPath "$sourceRoot/RESOLVED_METADATA.json").Hash.ToLowerInvariant()
$v=[ordered]@{status='FROZEN_BEFORE_INDEPENDENT_SOURCE_QA';created_utc=[DateTime]::UtcNow.ToString('o');checker_sha256=$small["/mnt/d/codex/coin/$qaName"];protocol_sha256=$small["/mnt/d/codex/coin/$protocolName"];producer_report_sha256=$small["/mnt/d/codex/coin/$producerName"];producer_complete_status=$source.status;producer_binding_key='binding';producer_task_id=$source.binding.task_id;producer_run_binding_path='/home/xflops/coin-state/carry-chronology-source-actual-20261003-v1/RUN_BINDING.json';producer_run_dir='/home/xflops/coin-state/carry-chronology-source-actual-20261003-v1';manifest_path='/home/xflops/coin-state/carry-chronology-source-actual-20261003-v1/RESOLVED_METADATA.json';manifest_objects_key='entries';audit_one_module_path='/mnt/d/codex/coin/scripts/research_v8/audit_funding_price_source.py';audit_one_module_sha256='edf2b7e8f7f74e392c422a126ae11d3755f915d11984b50014aa44df54dcd79c';small_input_hashes=$small;producer_host='session81115';producer_actual_exit=0}
if(Test-Path -LiteralPath "$work/ACTUAL_BINDING.json"){throw 'Refuse binding overwrite'}
[IO.File]::WriteAllText("$work/ACTUAL_BINDING.json",($v|ConvertTo-Json -Depth 14)+"`n",[Text.UTF8Encoding]::new($false))
Copy-Item -LiteralPath "$work/ACTUAL_BINDING.json" -Destination "$root/protocols/CARRY_CHRONOLOGY_SOURCE_INDEPENDENT_BINDING_20261003_V1.json"
Write-Output 'Binding frozen; no raw market file read or Python invoked'