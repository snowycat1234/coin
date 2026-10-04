param(
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{32}$')][string]$BindingTaskId,
 [Parameter(Mandatory)][string]$SepNovIndependentPath,
 [Parameter(Mandatory)][string]$DecFebIndependentPath,
 [Parameter(Mandatory)][string]$SepNovComparisonPath,
 [Parameter(Mandatory)][string]$DecFebComparisonPath,
 [string]$SepNovFinancialPlanPath,[string]$DecFebFinancialPlanPath
)
# UNRUN: build only after all ten roles have real closed0 tasks. No exporter/Git call.
$ErrorActionPreference='Stop'
$root='D:\codex\coin';$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state'
$parent='713618686ac2208f52e9b15fe072a9d5149b25b9'
$output='protocols/RSI2_DAILY_RELEASE_ACTUAL_BINDING_20261004_V1.json'
$exporter='.cache/d058_export_release.ps1'
function TaskDigest($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function ProjectPath($p){
 if($p.StartsWith('/mnt/d/codex/coin/')){$p=$p.Substring(18)}
 if([IO.Path]::IsPathRooted($p) -or $p -match '(^|[/\\])\.\.([/\\]|$)' -or $p -eq 'state/dataset_lock.json'){throw 'Public ROOT metadata path only'}
 Join-Path $root $p
}
function StatePath($p){
 if(-not $p.StartsWith('/home/xflops/coin-state/') -or $p -match '(^|/)\.\.(/|$)'){throw 'Explicit STATE metadata only'}
 Join-Path $state $p.Substring(24)
}
function SmallJson($p){
 $f=Get-Item -LiteralPath $p
 if($f.LinkType -or $f.Extension -ne '.json' -or $f.Length -gt 2000000){throw 'Small ordinary JSON only'}
 Get-Content -LiteralPath $p -Raw | ConvertFrom-Json -AsHashtable -DateKind String
}
function ClosedTask($id,$exit=0){
 if($id -notmatch '^[0-9a-f]{32}$'){throw 'Actual task identity required'}
 $file=Join-Path $state ('task-progress/task-'+$id+'.json');$t=SmallJson $file
 $status=if($exit -eq 0){'completed'}else{'failed'}
 if($t.id -ne $id -or $t.status -cne $status -or $t.exit_code -ne $exit -or -not $t.ended_at){throw ('Real closed task required '+$id)}
 @{path=('/home/xflops/coin-state/task-progress/task-'+$id+'.json');sha256=TaskDigest $file;task_id=$id;exit_code=$exit}
}
function Role($path,$expectedId='',$financialPlan=''){
 $file=ProjectPath $path;$r=SmallJson $file
 $id=if($r.binding){$r.binding.task_id}else{$r.task_id}
 if($expectedId -and $expectedId -ne $id){throw 'Actual role task differs'}
 $null=ClosedTask $id
 $ref=@{path=$file.Substring($root.Length+1).Replace('\','/');sha256=TaskDigest $file;task_id=$id}
 if($r.run_dir){$owner=StatePath $r.run_dir;if(-not (Test-Path -LiteralPath $owner -PathType Container)){throw 'Actual reported owner missing'};$ref.run_dir=$r.run_dir}
 if($financialPlan){$p=StatePath $financialPlan;$null=SmallJson $p;$ref.plan=@{path=$financialPlan;sha256=TaskDigest $p}}
 $ref
}
if((git -C $root rev-parse HEAD).Trim() -ne $parent -or (Test-Path -LiteralPath (ProjectPath $output))){throw 'Exact parent and exclusive new binding'}
$metadata='reports/fast_research/RSI2_DAILY_INPUT_BINDING_20261004_V1.json'
$metadataValue=SmallJson (ProjectPath $metadata)
if($metadataValue.status -ne 'READY_D058_TWO_UNCHANGED_SOURCE_QUARTERS_RSI2_DAILY_PROTOCOLS_NOT_MARKET_RESULTS' -or $metadataValue.parent_commit -ne $parent){throw 'Actual finalized D058 metadata required'}
$roles=@{METADATA=Role $metadata;
 WARMUP_SOURCE=Role 'reports/fast_research/RSI2_JANUARY_DAILY_WARMUP_SOURCE_20261004_V1.json' 'd31d9d24338b410297b47cfd9afdcfa7';
 WARMUP_ACCEPTANCE=Role 'reports/fast_research/RSI2_JANUARY_DAILY_WARMUP_ACCEPTANCE_20261004_V1.json' 'c6bbe307f5d840d9b798167da0b49d14'}
$testPath='reports/fast_research/RSI2_DAILY_POOL_TARGET_SYNTHETIC_20261004_V2.json'
$test=SmallJson (ProjectPath $testPath);$testId='a9d97f3cf2674d93a448fd74b9720313'
if($test.binding.task_id -ne $testId -or $test.status -ne 'PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT' -or $test.test_exit_code -ne 0 -or $test.source_bytes_unchanged -ne $true -or $test.junit_counts.tests -ne 1 -or $test.junit_counts.errors -or $test.junit_counts.failures -or $test.junit_counts.skipped){throw 'One actual successful target case required'}
$null=ClosedTask $testId;$junitPath=$test.run_dir+'/junit.xml';$junit=StatePath $junitPath
if((TaskDigest $junit) -ne $test.junit_sha256 -or (Get-Item -LiteralPath $junit).Length -gt 2000000){throw 'Actual small JUnit identity'}
$testFile='tests/test_rsi2_daily_pool_target.py';$testHash=$test.binding.source_hashes[$testFile]
if((TaskDigest (ProjectPath $testFile)) -ne $testHash){throw 'Consumed target test source changed'}
$roles.TARGET_TESTS=@{task_id=$testId;path=$testPath;sha256=TaskDigest (ProjectPath $testPath);
 junit=@{path=$junitPath;sha256=$test.junit_sha256};source_hashes=@{$testFile=$testHash}}
foreach($period in @('SEPNOV91','DECFEB90')){
 $p=$metadataValue.protocols[$period];$protocol=ProjectPath $p.path
 if((TaskDigest $protocol) -ne $p.sha256){throw 'Actual generated protocol bytes changed'}
 $roles[$period+'_MARKET']=Role $p.output_path
 if($roles[$period+'_MARKET'].run_dir -ne $p.run_dir){throw 'Actual market directory differs from frozen metadata'}
}
$roles.SEPNOV91_INDEPENDENT=Role $SepNovIndependentPath '' $SepNovFinancialPlanPath
$roles.DECFEB90_INDEPENDENT=Role $DecFebIndependentPath '' $DecFebFinancialPlanPath
$roles.SEPNOV91_COMPARISON=Role $SepNovComparisonPath
$roles.DECFEB90_COMPARISON=Role $DecFebComparisonPath
$failureId='d1d7216b334941febeb3df8f3d1adfcf';$failureTask=ClosedTask $failureId 1
$failedPath='reports/fast_research/RSI2_DAILY_POOL_TARGET_STARTUP_FAILURE_20261004_V1.json'
$failed=SmallJson (ProjectPath $failedPath)
if($failed.binding.task_id -ne $failureId -or $failed.tests_executed -ne 0 -or $failed.market_arrays_read -ne $false){throw 'Preserved startup failure identity/scope'}
$financialStartupId='a72208bb4ad54274acb3c338ec8256c7';$financialStartupTask=ClosedTask $financialStartupId 2
$sourceGuardId='894bce1071f94e95af55df0597a88361';$sourceGuardTask=ClosedTask $sourceGuardId 1
$sourceGuardPath='reports/fast_research/RSI2_DAILY_SEPNOV91_INDEPENDENT_20261004_V1.json'
$sourceGuardReport=SmallJson (ProjectPath $sourceGuardPath)
if($sourceGuardReport.binding.task_id -ne $sourceGuardId -or $sourceGuardReport.status -ne 'FAIL_CONFIGURED_N_PERPETUAL_RECORDED_ACCOUNTING' -or $sourceGuardReport.completed_cases_verified -ne 0){throw 'Preserved financial source-guard failure identity/scope'}
$sourceGuardPlanPath=$sourceGuardReport.run_dir+'/ACTUAL_BINDING.json';$sourceGuardPlan=StatePath $sourceGuardPlanPath
$null=SmallJson $sourceGuardPlan
if((TaskDigest $sourceGuardPlan) -ne $sourceGuardReport.binding.ACTUAL_BINDING_sha256){throw 'Failed V1 real input plan identity'}
$oldChecker='docs/archive/RSI2_DAILY_PRE_MARKET_FINANCIAL_CHECKER_SOURCE_20261004_V1.py'
if((TaskDigest (ProjectPath $oldChecker)) -ne $sourceGuardReport.binding.checker_sha256){throw 'Preserved executed pre-mark financial source bytes'}
$extra=@()
foreach($row in @(
 @{role='SOURCE_AST';id='bddc5cc71e2a494b92fc73adbfbb23fa';scope='AST_COMPILE_ONLY_NO_FUNCTIONS_OR_ARRAYS'},
 @{role='SOURCE_METADATA_PROBE';id='4bbb9b55055847a0b289fe36182aa6be';scope='RUNTIME_PATH_IDENTITY_DIAGNOSTIC_NOT_MARKET_OR_SOURCE_QA'})){
 $closed=ClosedTask $row.id;$extra+=@{role=$row.role;id=$row.id;exit=0;scope=$row.scope;closed_task=$closed}
}
$plan=@{ready_to_execute=$true;parent_commit=$parent;exporter_sha256=TaskDigest (ProjectPath $exporter);
 roles=$roles;failures=@(@{role='TARGET_STARTUP_FAILURE';id=$failureId;exit=1;scope='STARTUP_BEFORE_PROTOCOL_STATE_OR_TEST_ZERO_CASES';
 report=@{path=$failedPath;sha256=TaskDigest (ProjectPath $failedPath)};closed_task=$failureTask},
 @{role='FINANCIAL_ARGUMENT_STARTUP_FAILURE';id=$financialStartupId;exit=2;closed_task=$financialStartupTask;
 scope='ARGPARSE_MISSING_PROTOCOL_AND_ACTUAL_BEFORE_MAIN_ZERO_FINANCIAL_CALLS_ZERO_ARRAYS_NO_REPORT_OR_RUN_WRITTEN';
 host=@{session_id=37145;final_chunk_id='7ec158';exit_code=1};
 inner_task_exit_code=2;host_exit_scope='WRAPPER_HOST_STATUS_DISTINCT_FROM_INNER_ARGPARSE_TASK_EXIT';
 financial_calls=0;arrays_read=$false;report_written=$false;run_binding_written=$false},
 @{role='FINANCIAL_SOURCE_GUARD_FAILURE';id=$sourceGuardId;exit=1;closed_task=$sourceGuardTask;
 scope='PINNED_RS_TXT_SOURCE_METADATA_REJECTED_BEFORE_INPUT_READER_ZERO_FINANCIAL_CALLS';
 host=@{session_id=44050;final_chunk_id='bf8050';exit_code=1};financial_calls=0;input_reader_called=$false;
 report=@{path=$sourceGuardPath;sha256=TaskDigest (ProjectPath $sourceGuardPath)};
 plan=@{path=$sourceGuardPlanPath;sha256=TaskDigest $sourceGuardPlan};
 executed_source=@{path=$oldChecker;sha256=$sourceGuardReport.binding.checker_sha256}});extra_roles=$extra;
 binding_task_id=$BindingTaskId;binding_source_sha256=TaskDigest $PSCommandPath;
 own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED';market_arrays_read=$false;source_QA_calls=0;new_downloads=0;
 created_utc=[DateTimeOffset]::UtcNow.ToString('o')}
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($plan|ConvertTo-Json -Depth 20)+"`n")
if($roles.Count -ne 10 -or $bytes.Length -gt 2000000){throw 'Ten true closed0 roles and small final plan'}
$stream=[IO.File]::Open((ProjectPath $output),[IO.FileMode]::CreateNew)
try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
[pscustomobject]@{path=$output;sha256=TaskDigest (ProjectPath $output);bytes=$bytes.Length;closed_roles=$roles.Count;git_mutations=$false}
