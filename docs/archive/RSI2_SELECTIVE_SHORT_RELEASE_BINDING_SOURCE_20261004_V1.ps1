param(
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{32}$')][string]$BindingTaskId,
 [Parameter(Mandatory)][string]$SepNovIndependentPath,
 [Parameter(Mandatory)][string]$DecFebIndependentPath,
 [Parameter(Mandatory)][string]$SepNovComparisonPath,
 [Parameter(Mandatory)][string]$DecFebComparisonPath,
 [string]$SepNovFinancialPlanPath,[string]$DecFebFinancialPlanPath
)
# UNRUN: bind only eight true closed0 roles. No exporter, Git or market call.
$ErrorActionPreference='Stop'
$root='D:\codex\coin';$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state'
$parent='61316ff1865437b8cc7a286e0e2aad95bdc67340'
$output='protocols/RSI2_SELECTIVE_SHORT_RELEASE_ACTUAL_BINDING_20261004_V1.json'
$exporter='.cache/d059_export_release.ps1'
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
function ClosedTask($id){
 if($id -notmatch '^[0-9a-f]{32}$'){throw 'Actual task identity required'}
 $file=Join-Path $state ('task-progress/task-'+$id+'.json');$t=SmallJson $file
 if($t.id -ne $id -or $t.status -cne 'completed' -or $t.exit_code -ne 0 -or -not $t.ended_at){throw ('Real closed0 task required '+$id)}
 @{path=('/home/xflops/coin-state/task-progress/task-'+$id+'.json');sha256=TaskDigest $file;task_id=$id;exit_code=0}
}
function Role($path,$expectedId='',$financialPlan=''){
 $file=ProjectPath $path;$r=SmallJson $file
 $id=if($r.binding){$r.binding.task_id}else{$r.task_id}
 if($expectedId -and $expectedId -ne $id){throw 'Actual role task differs'}
 $null=ClosedTask $id
 $ref=@{path=$file.Substring($root.Length+1).Replace('\','/');sha256=TaskDigest $file;task_id=$id}
 if($r.run_dir){$owner=StatePath $r.run_dir;if(-not (Test-Path -LiteralPath $owner -PathType Container)){throw 'Actual reported owner missing'};$ref.run_dir=$r.run_dir}
 if($financialPlan){$p=StatePath $financialPlan;$null=SmallJson $p;$sha=TaskDigest $p;if($r.binding.ACTUAL_BINDING_sha256 -ne $sha){throw 'Actual consumed financial plan bytes'};$ref.plan=@{path=$financialPlan;sha256=$sha}}
 $ref
}
if((git -C $root rev-parse HEAD).Trim() -ne $parent -or (Test-Path -LiteralPath (ProjectPath $output))){throw 'Exact parent and exclusive new binding'}
$metadata='reports/fast_research/RSI2_SELECTIVE_SHORT_INPUT_BINDING_20261004_V1.json'
$metadataValue=SmallJson (ProjectPath $metadata)
if((TaskDigest (ProjectPath $metadata)) -ne '55038ce0e03e41d591ba340a8662f24b17e5decca8e1b92c983fd52bc8396748' -or $metadataValue.status -ne 'READY_D059_FIXED_RSI2_SELECTIVE_SHORT_PROTOCOLS_NOT_MARKET_RESULTS' -or $metadataValue.parent_commit -ne $parent){throw 'Actual finalized D059 metadata required'}
$roles=@{METADATA=Role $metadata '3cc8726efe224fc3b754247848d37d41'}
$testPath='reports/fast_research/RSI2_SELECTIVE_SHORT_TARGET_SYNTHETIC_20261004_V1.json'
$test=SmallJson (ProjectPath $testPath);$testId='f1c412eb094d46268f096b6520c53b98'
$testProtocolPath='protocols/RSI2_SELECTIVE_SHORT_TARGET_SYNTHETIC_20261004_V1.json'
$testProtocol=SmallJson (ProjectPath $testProtocolPath)
if((TaskDigest (ProjectPath $testPath)) -ne '90cc20f412ff1797498e697ee59870d123093edf534b8fc33bde3c56d66a8b72' -or (TaskDigest (ProjectPath $testProtocolPath)) -ne '380ea657cda8bc1cb49b915bd35fc873e458813d59db5e7eef04ac975c79363a' -or $test.binding.task_id -ne $testId -or $test.binding.protocol_sha256 -ne (TaskDigest (ProjectPath $testProtocolPath)) -or $test.status -ne 'PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT' -or $test.test_exit_code -ne 0 -or $test.source_bytes_unchanged -ne $true -or $test.junit_counts.tests -ne 1 -or $test.junit_counts.errors -or $test.junit_counts.failures -or $test.junit_counts.skipped){throw 'One actual successful selective-short case required'}
$null=ClosedTask $testId;$junitPath=$test.run_dir+'/junit.xml';$junit=StatePath $junitPath
if((TaskDigest $junit) -ne $test.junit_sha256 -or (Get-Item -LiteralPath $junit).Length -gt 2000000){throw 'Actual small JUnit identity'}
$testFile='tests/test_rsi2_selective_short_pool.py';$testHash=$test.binding.source_hashes[$testFile]
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
$freezeId=$testProtocol.freeze_task_id;$freezeTask=ClosedTask $freezeId
$extra=@(@{role='TEST_FREEZE';id=$freezeId;exit=0;scope='PROSPECTIVE_SYNTHETIC_PROTOCOL_METADATA_FREEZE_NOT_MARKET_OR_QA';closed_task=$freezeTask;
 protocol=@{path=$testProtocolPath;sha256=TaskDigest (ProjectPath $testProtocolPath)}})
$plan=@{ready_to_execute=$true;parent_commit=$parent;exporter_sha256=TaskDigest (ProjectPath $exporter);
 roles=$roles;failures=@();extra_roles=$extra;binding_task_id=$BindingTaskId;binding_source_sha256=TaskDigest $PSCommandPath;
 own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED';market_arrays_read=$false;source_QA_calls=0;new_downloads=0;
 created_utc=[DateTimeOffset]::UtcNow.ToString('o')}
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($plan|ConvertTo-Json -Depth 20)+"`n")
if($roles.Count -ne 8 -or $bytes.Length -gt 2000000){throw 'Eight true closed0 roles and small final plan'}
$stream=[IO.File]::Open((ProjectPath $output),[IO.FileMode]::CreateNew)
try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
[pscustomobject]@{path=$output;sha256=TaskDigest (ProjectPath $output);bytes=$bytes.Length;closed_roles=$roles.Count;git_mutations=$false}
