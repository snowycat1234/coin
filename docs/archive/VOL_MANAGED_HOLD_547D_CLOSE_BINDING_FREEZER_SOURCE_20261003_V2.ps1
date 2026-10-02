# UNRUN D034 close-binding factory: small existing JSON/code only, never price/ledger payloads.
$ErrorActionPreference='Stop'
if($PSVersionTable.PSVersion.Major -lt 7){throw 'Existing PowerShell7 required'}
Set-Location 'D:/codex/coin'
$Root='D:\codex\coin\';$State='\\wsl.localhost\hpc_linux\home\xflops\coin-state\'
$Archive='docs/archive/VOL_MANAGED_HOLD_547D_CLOSE_BINDING_FREEZER_SOURCE_20261003_V2.ps1'
$Helper='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
$HelperSha='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
$Proto='protocols/VOL_MANAGED_HOLD_547D_BYBIT_20261003_V2.json'
$ProtoSha='d60d7f0364a93e0918e1fe71f3c44d166a1a9c073e76dc0898e3fce09fa83303'
$Output='protocols/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_BINDING_20261003_V1.json'
function Native([string]$p){
 if($p.StartsWith('/home/xflops/coin-state/')){return $State+$p.Substring(24).Replace('/','\')}
 if($p.StartsWith('/mnt/d/codex/coin/')){return $Root+$p.Substring(18).Replace('/','\')}
 return [IO.Path]::GetFullPath($p)
}
function Small([string]$p){
 $p=Native $p;$item=Get-Item -LiteralPath $p
 if($item.PSIsContainer -or $item.Length -gt 2000000 -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Small ordinary metadata only'}
 if(-not ($item.FullName.StartsWith($Root,[StringComparison]::OrdinalIgnoreCase) -or $item.FullName.StartsWith($State,[StringComparison]::OrdinalIgnoreCase))){throw 'ROOT/STATE metadata only'}
 if($item.Extension -notin @('.py','.ps1','.json','.xml','.md','.toml','.lock','.sh') -and -not $item.Name.EndsWith('LICENSE')){throw 'No market or binary byte IO'}
 return $item.FullName
}
function Hash([string]$p){(Get-FileHash -LiteralPath (Small $p) -Algorithm SHA256).Hash.ToLowerInvariant()}
function Read([string]$p){Get-Content -LiteralPath (Small $p) -Raw | ConvertFrom-Json -AsHashtable}
function CheckTask([string]$id,[int]$code){
 if($id -notmatch '^[0-9a-f]{32}$'){throw 'Exact real task id'}
 $task=Read ($State+'task-progress\task-'+$id+'.json')
 if($task.id -ne $id -or ($task.exit_code -isnot [int] -and $task.exit_code -isnot [long]) -or $task.exit_code -ne $code -or $task.status -ne $(if($code -eq 0){'completed'}else{'failed'})){throw 'Actual terminal task/exit required'}
 if(-not [double]::IsFinite([double]$task.started_at) -or -not [double]::IsFinite([double]$task.ended_at) -or $task.ended_at -lt $task.started_at){throw 'Actual task times'}
 return $task
}
function Role([string]$path,[string]$status,[string]$work){
 $r=Read $path;if($r.status -ne $status){throw 'Actual expected report status'}
 $null=CheckTask $r.binding.task_id 0
 $entry=[ordered]@{report=$path;report_sha256=Hash $path;required_status=$status;expected_task_id=$r.binding.task_id}
 if($work){
  $rb=$work+'/RUN_BINDING.json';$b=Read $rb
  if($b.task_id -ne $r.binding.task_id -or ($r.Contains('run_binding_sha256') -and $r.run_binding_sha256 -ne (Hash $rb))){throw 'Actual existing RUN_BINDING identity/SHA'}
  $entry.run_binding=$rb;$entry.run_binding_sha256=Hash $rb
 }
 return @{entry=$entry;receipt=$r}
}
if(Test-Path -LiteralPath $Output){throw 'Exclusive new close protocol'}
if((Hash $Helper) -ne $HelperSha -or (Hash $Proto) -ne $ProtoSha){throw 'Exact held root-close/source protocol'}
$FactorySha=Hash $PSCommandPath;if((Hash $Archive) -ne $FactorySha){throw 'Archive identical factory before execution'}
$s=Read $Proto
if(($s.strategy_ids -join ',') -ne 'VOL_MANAGED_BUY_AND_HOLD' -or $s.planned_ledgers -ne 1 -or $s.maximum_new_owned_bytes -ne 280000000 -or $s.module_combined_STATE_budget_bytes -ne 300000000){throw 'Fixed VM-only and pre-array capacity'}
$roles=[ordered]@{};$receipts=@{}
$descriptions=@(
 @('SOURCE','reports/fast_research/PUBLIC_LONG_547D_SOURCE_REUSE_20261003_V1.json','PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_578D_CALENDAR','/home/xflops/coin-state/public-long-547d-source-reuse-actual-20261003-v1'),
 @('TINY','reports/fast_research/VOL_MANAGED_HOLD_547D_BOUNDARY_TINY_20261003_V2.json','PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT','/home/xflops/coin-state/test-vol-managed-hold-547d-boundary-20261003-v2'),
 @('RESEARCH','reports/fast_research/VOL_MANAGED_HOLD_547D_ACTUAL_20261003_V1.json','COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING','/home/xflops/coin-state/vol-managed-hold-547d-actual-20261003-v1'),
 @('INDEPENDENT','reports/fast_research/VOL_MANAGED_HOLD_547D_INDEPENDENT_AUDIT_20261003_V1.json','PASS_D034_SINGLE_VM_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR','/home/xflops/coin-state/d034-independent-20261003-v1'),
 @('COMPARISON','reports/fast_research/VOL_MANAGED_HOLD_547D_ECONOMIC_COMPARISON_20261003_V1.json','COMPLETE_D034_SAVED_SUMMARY_RISK_COST_COMPARISON_NOT_LONG_TERM_APR','/home/xflops/coin-state/d034-comparison-20261003-v1'))
foreach($d in $descriptions){$r=Role $d[1] $d[2] $d[3];$roles[$d[0]]=$r.entry;$receipts[$d[0]]=$r.receipt}
if($roles.SOURCE.report_sha256 -ne '64dc9474828b1707b21a7ed09b5719f202645cbc4ceb72007d9775d72d67fee2' -or $receipts.SOURCE.source_files -ne 38){throw 'Exact accepted source metadata, no new QA'}
if($receipts.TINY.binding.protocol_sha256 -ne $ProtoSha -or $receipts.RESEARCH.binding.protocol_sha256 -ne $ProtoSha -or $receipts.COMPARISON.binding.protocol_sha256 -ne $ProtoSha){throw 'Only actual corrected protocolV2'}
if($receipts.RESEARCH.completed_ledgers -ne 1 -or $receipts.INDEPENDENT.completed_ledgers_verified -ne 1 -or $receipts.COMPARISON.cases.Count -ne 4){throw 'Only one new account and saved comparison'}
$checker='docs/archive/VOL_MANAGED_HOLD_547D_USED_INDEPENDENT_SOURCES_20261003_V1/audit.py';$checkerSha='942f006885a6e2cc5476f697b6368e586c30fe68b0344af55833aa8f4c808d78'
$comparator='docs/archive/VOL_MANAGED_HOLD_547D_ECONOMIC_COMPARISON_SOURCE_20261003_V2.py';$comparatorSha='6e7bc5d00c21127df860f9c443d497e468f894402c7af88bfd70db4c451c7309'
if((Hash $checker) -ne $checkerSha -or $receipts.INDEPENDENT.binding.checker_sha256 -ne $checkerSha -or (Hash $comparator) -ne $comparatorSha -or $receipts.COMPARISON.binding.source_sha256 -ne $comparatorSha){throw 'Exact independently executed checker/comparator bytes'}
$roles.INDEPENDENT.source=@{path=$checker;sha256=$checkerSha};$roles.COMPARISON.source=@{path=$comparator;sha256=$comparatorSha}
$failurePath='reports/fast_research/VOL_MANAGED_HOLD_547D_BOUNDARY_TINY_20261003_V1.json'
$f=Read $failurePath;$failureSha=Hash $failurePath
if($f.status -ne 'FAIL_SIMPLE_STRATEGY_COMPARISON' -or $f.test_exit_code -ne 1 -or $f.market_inputs_read -ne $false -or $failureSha -ne 'a09f779f3dabdad7cfa8e60d2884ff21e2e82206850caab67b0361eb5938e21d'){throw 'Preserve actual V1 synthetic failure'}
$null=CheckTask $f.binding.task_id 1
$preserved=@(@{report=$failurePath;report_sha256=$failureSha;required_status=$f.status;expected_task_id=$f.binding.task_id;exit_code=1;host_result=@{session_id=7560;chunk_id='a429aa';exit_code=1};reason='Fixture-only daily group_by order; production already sorts; V1 not PASS'})
$project=@{}
function Add([string]$name,[string]$expected=''){
 if($name -eq 'state/dataset_lock.json'){throw 'Scientific private lock cannot enter portable project_files'}
 $h=Hash $name;if($expected -and $expected -ne $h){throw 'Frozen source changed'}
 if($project.Contains($name) -and $project[$name] -ne $h){throw 'Conflicting source pin'};$project[$name]=$h
}
foreach($name in $s.frozen_sources.Keys){if($name -ne 'state/dataset_lock.json'){Add $name $s.frozen_sources[$name]}}
if((Hash 'state/dataset_lock.json') -ne '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'){throw 'Strong separate private scientific lock'}
Add $Proto $ProtoSha;Add $Helper $HelperSha;Add $Archive $FactorySha;Add $checker $checkerSha;Add $comparator $comparatorSha
Add 'protocols/VOL_MANAGED_HOLD_547D_COMPARISON_BINDING_20261003_V1.json' 'ea8a7bc11669f1c47cfbb0d926a202261b2ccf6584c58bf17003510c8abc05cc'
Add 'docs/archive/VOL_MANAGED_HOLD_547D_AUDIT_BINDING_FREEZER_SOURCE_20261003_V1.ps1' '5245ca61da2d109da0a58e5d6f96061cf89e33bd0f322acbd93288400c2e9ae4'
$sync='reports/GITHUB_PUBLIC_LONG_547D_SYNC_VERIFIED_20261003_V1.json';$syncSha='de6938ee04e80baf54eb038edd29dc2b32e196d9c03f322d49d1dab8895d9663';Add $sync $syncSha
$verified=Read $sync
if($verified.status -ne 'ACKNOWLEDGED_PUSH_AND_EXACT_REMOTE_MAIN_VERIFIED' -or $verified.local_commit -ne $verified.remote_main -or $verified.local_commit -ne 'cc2f2df4d0b945ba9e50a7dd1fc5e56d70bbed58' -or $verified.actual_git_exit -ne 0){throw 'Exact accepted D033 sync proof'}
foreach($binding in $verified.task_bindings){$null=CheckTask $binding.task.id 0}
# Only this module's existing ordinary archives; no mutable status/doc freezing and no ROOT scan.
foreach($file in Get-ChildItem -LiteralPath 'docs/archive' -File -Filter 'VOL_MANAGED_HOLD*'){
 if($file.Extension -in @('.py','.ps1','.json','.md')){Add ('docs/archive/'+$file.Name)}
}
foreach($file in Get-ChildItem -LiteralPath 'docs/archive/VOL_MANAGED_HOLD_547D_USED_INDEPENDENT_SOURCES_20261003_V1' -File){Add ('docs/archive/VOL_MANAGED_HOLD_547D_USED_INDEPENDENT_SOURCES_20261003_V1/'+$file.Name)}
$owned=@('/home/xflops/coin-state/vol-managed-hold-547d-actual-20261003-v1','/home/xflops/coin-state/test-vol-managed-hold-547d-boundary-20261003-v1','/home/xflops/coin-state/test-vol-managed-hold-547d-boundary-20261003-v2','/home/xflops/coin-state/d034-independent-20261003-v1','/home/xflops/coin-state/d034-comparison-20261003-v1')
foreach($p in $owned){$item=Get-Item -LiteralPath (Native $p);if(-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Existing exact new owned directory only'}}
$files=@($project.Keys | Sort-Object | ForEach-Object {@{path=$_;sha256=$project[$_]}})
$value=[ordered]@{classification='CLOSED_SMALL_METADATA_ONLY_NOT_MARKET_REPLAY';ready_to_execute=$true;created_utc=[DateTime]::UtcNow.ToString('o');helper_sha256=$HelperSha;protocol=@{path=$Proto;sha256=$ProtoSha};roles=$roles;owned_STATE_directories=$owned;project_files=$files;preserved_failures=$preserved;maximum_owned_STATE_bytes=300000000;local_non_git_source_hashes=@{'state/dataset_lock.json'='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'};factory=@{archive=$Archive;sha256=$FactorySha;task_id=$env:COIN_TASK_ID;own_completion='LIVE_CALLER_NOT_CERTIFIED'};metadata_only=$true;market_or_ledger_arrays_read=$false;old_green_QA_or_accounts_repeated=$false;locked_consumed=$false;candidate_status='NO_QUALIFIED_CANDIDATE'}
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($value|ConvertTo-Json -Depth 30)+[Environment]::NewLine)
if($bytes.Length -gt 100000){throw 'Close binding maximum100KB'}
$stream=[IO.File]::Open((Join-Path $Root $Output),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write);try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
@{path=$Output;sha256=Hash $Output;closed_roles=5;preserved_failed_runs=1;factory_own_completion='LIVE_CALLER_NOT_CERTIFIED'}|ConvertTo-Json
