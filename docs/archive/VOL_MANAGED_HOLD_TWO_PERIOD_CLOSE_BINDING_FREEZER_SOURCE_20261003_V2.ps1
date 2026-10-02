# UNRUN D035 close-binding factory; small real completed metadata only, never arrays/QA.
$ErrorActionPreference='Stop'
if($PSVersionTable.PSVersion.Major -lt 7){throw 'Existing PowerShell7 required'}
Set-Location 'D:/codex/coin'
$Root='D:\codex\coin\';$State='\\wsl.localhost\hpc_linux\home\xflops\coin-state\'
$Archive='docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD_CLOSE_BINDING_FREEZER_SOURCE_20261003_V2.ps1'
$Helper='docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD_ROOT_CLOSE_SOURCE_20261003_V2.py';$HelperSha='7df90cab981f4230c981cf2360cf4e1b45988a1db443a25ddb1c97936b40f8dd'
$Checker='docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD_INDEPENDENT_SOURCE_20261003_V3.py';$CheckerSha='0e4e4bcdb042e5d6818f471ae3c551896f0787f94aac04783e9c05f729f27bd2'
$Comparator='docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD_ECONOMIC_COMPARISON_SOURCE_20261003_V4.py';$ComparatorSha='f7fd24afd9654cea51de9da8a228b1ccdd2337f1e61b0039a2810f2089b87495'
$Output='protocols/VOL_MANAGED_HOLD_TWO_PERIOD_ROOT_CLOSE_BINDING_20261003_V1.json'
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
function Read([string]$p){Get-Content -LiteralPath (Small $p) -Raw|ConvertFrom-Json -AsHashtable}
function CheckTask([string]$id,[int]$code){
 if($id -notmatch '^[0-9a-f]{32}$'){throw 'Exact real task id'}
 $task=Read ($State+'task-progress\task-'+$id+'.json')
 if($task.id -ne $id -or ($task.exit_code -isnot [int] -and $task.exit_code -isnot [long]) -or $task.exit_code -ne $code -or $task.status -ne $(if($code -eq 0){'completed'}else{'failed'})){throw 'Actual terminal task/exit required'}
 if(-not [double]::IsFinite([double]$task.started_at) -or -not [double]::IsFinite([double]$task.ended_at) -or $task.ended_at -lt $task.started_at){throw 'Actual task times'}
 return $task
}
function Role([string]$path,[string]$status,[string]$work){
 $r=Read $path;if($r.status -ne $status){throw 'Actual expected report status'};$null=CheckTask $r.binding.task_id 0
 $rb=$work+'/RUN_BINDING.json';$b=Read $rb;$rbSha=Hash $rb
 if($b.task_id -ne $r.binding.task_id -or ($r.Contains('run_binding_sha256') -and $r.run_binding_sha256 -ne $rbSha)){throw 'Actual existing RUN_BINDING identity/SHA'}
 return @{entry=[ordered]@{report=$path;report_sha256=Hash $path;required_status=$status;expected_task_id=$r.binding.task_id;run_binding=$rb;run_binding_sha256=$rbSha};receipt=$r}
}
if(Test-Path -LiteralPath $Output){throw 'Exclusive new close protocol'}
$FactorySha=Hash $PSCommandPath
foreach($pair in @(@($Archive,$FactorySha),@($Helper,$HelperSha),@($Checker,$CheckerSha),@($Comparator,$ComparatorSha))){if((Hash $pair[0]) -ne $pair[1]){throw 'Exact pre-read held ROOT sources'}}
$protocols=[ordered]@{CONT122=@{path='protocols/VOL_MANAGED_HOLD_122D_BYBIT_20261003_V1.json';sha256='9ec8e182a933bb3e16b32fb8dc9391431fcca6a2bab034e37903bd7c83aff2c5'};CONT90=@{path='protocols/VOL_MANAGED_HOLD_90D_BYBIT_20261003_V1.json';sha256='5c95df3ae7800b5cb72879643b5bfbf8f9104f26c3a9ac927f94a7e701bbb136'}}
$specs=@{};foreach($fold in $protocols.Keys){$p=$protocols[$fold];if((Hash $p.path) -ne $p.sha256){throw 'Exact frozen child protocols'};$specs[$fold]=Read $p.path}
$roles=[ordered]@{};$receipts=@{};$descriptions=@(
 @('TINY','reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_BOUNDARY_TINY_20261003_V1.json','PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT','/home/xflops/coin-state/test-vol-managed-hold-two-period-boundary-20261003-v1'),
 @('RESEARCH122','reports/fast_research/VOL_MANAGED_HOLD_122D_ACTUAL_20261003_V1.json','COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING','/home/xflops/coin-state/vol-managed-hold-122d-actual-20261003-v1'),
 @('RESEARCH90','reports/fast_research/VOL_MANAGED_HOLD_90D_ACTUAL_20261003_V1.json','COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING','/home/xflops/coin-state/vol-managed-hold-90d-actual-20261003-v1'),
 @('INDEPENDENT','reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_INDEPENDENT_AUDIT_20261003_V2.json','PASS_D035_TWO_VM_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR','/home/xflops/coin-state/d035-independent-20261003-v2'),
 @('COMPARISON','reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_ECONOMIC_COMPARISON_20261003_V1.json','COMPLETE_D035_TWO_PERIOD_SAVED_SUMMARY_RISK_COST_COMPARISON_NOT_LONG_TERM_APR','/home/xflops/coin-state/d035-comparison-20261003-v1'))
foreach($d in $descriptions){$r=Role $d[1] $d[2] $d[3];$roles[$d[0]]=$r.entry;$receipts[$d[0]]=$r.receipt}
if($receipts.INDEPENDENT.binding.checker_sha256 -ne $CheckerSha -or $receipts.COMPARISON.binding.source_sha256 -ne $ComparatorSha){throw 'Actually executed checker/comparator source'}
$roles.INDEPENDENT.source=@{path=$Checker;sha256=$CheckerSha};$roles.COMPARISON.source=@{path=$Comparator;sha256=$ComparatorSha}
if($receipts.RESEARCH122.completed_ledgers -ne 1 -or $receipts.RESEARCH90.completed_ledgers -ne 1 -or $receipts.INDEPENDENT.completed_ledgers_verified -ne 2 -or $receipts.COMPARISON.cases.Count -ne 8 -or $receipts.COMPARISON.pairs.Count -ne 4){throw 'Exact two new accounts and saved eight-case/four-pair scope'}
if($receipts.TINY.binding.protocol_sha256 -ne $protocols.CONT122.sha256 -or $receipts.RESEARCH122.binding.protocol_sha256 -ne $protocols.CONT122.sha256 -or $receipts.RESEARCH90.binding.protocol_sha256 -ne $protocols.CONT90.sha256){throw 'Only selected frozen protocols, one new tiny under122'}
# The failed first audit is retained separately; it never satisfies a successful role.
$failedPath='reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_INDEPENDENT_AUDIT_20261003_V1.json';$failedSha='fdc4cb0683cc224943ca4ec7bbe018f452f21bb77221c230cf86f38f359a1bcc'
if((Hash $failedPath) -ne $failedSha){throw 'Actual failed audit report bytes preserved'};$failedReceipt=Read $failedPath
$failedTaskId='9d00f027d29047afb026b2790e65151a';$null=CheckTask $failedTaskId 1
if($failedReceipt.status -ne 'FAIL_D035_TWO_VM_INDEPENDENT_AUDIT' -or $failedReceipt.binding.task_id -ne $failedTaskId -or $failedReceipt.completed_ledgers_verified -ne 0 -or $failedReceipt.runtime_inputs.Count -ne 0 -or $failedReceipt.error_type -ne 'KeyError' -or $failedReceipt.error -ne "'source_scope'"){throw 'Retain actual metadata failure and zero checked financial ledgers'}
$failedRB='/home/xflops/coin-state/d035-independent-20261003-v1/RUN_BINDING.json';$failedRBSha='c5fa56e4610229183cb20c8d27e826a24db9184528a751fa118465105c374327'
if((Hash $failedRB) -ne $failedRBSha -or $failedReceipt.run_binding_sha256 -ne $failedRBSha -or (Read $failedRB).task_id -ne $failedTaskId){throw 'Failed actual RUN_BINDING preserved'}
$failedCode='docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD_INDEPENDENT_SOURCE_20261003_V2.py';$failedCodeSha='752c1015144bff614147ec445a4fcf62ff64f4d89b7a7074e93718c5ab9447d4'
if((Hash $failedCode) -ne $failedCodeSha -or $failedReceipt.binding.checker_sha256 -ne $failedCodeSha){throw 'Failed used checker exact byte identity'}
$failedRoles=[ordered]@{INDEPENDENT_V1=[ordered]@{report=$failedPath;report_sha256=$failedSha;required_status='FAIL_D035_TWO_VM_INDEPENDENT_AUDIT';required_exit_code=1;expected_task_id=$failedTaskId;run_binding=$failedRB;run_binding_sha256=$failedRBSha;source=@{path=$failedCode;sha256=$failedCodeSha}}}
$project=@{}
function Add([string]$name,[string]$expected=''){
 if($name -eq 'state/dataset_lock.json'){throw 'Private scientific lock cannot enter portable project_files'}
 $h=Hash $name;if($expected -and $expected -ne $h){throw 'Frozen source changed'}
 if($project.Contains($name) -and $project[$name] -ne $h){throw 'Conflicting public source union'};$project[$name]=$h
}
foreach($fold in $protocols.Keys){
 $p=$protocols[$fold];$s=$specs[$fold];Add $p.path $p.sha256
 if(($s.strategy_ids -join ',') -ne 'VOL_MANAGED_BUY_AND_HOLD' -or $s.planned_ledgers -ne 1 -or $s.module_combined_STATE_budget_bytes -ne 150000000){throw 'Only preregistered VM150MB module'}
 foreach($name in $s.frozen_sources.Keys){if($name -ne 'state/dataset_lock.json'){Add $name $s.frozen_sources[$name]}}
 # The two legacy sources never had a task id; only preserved accepted metadata/status.
 if((Hash $s.source_receipt) -ne $s.source_receipt_sha256){throw 'Legacy source identity'};$source=Read $s.source_receipt
 $days=$(if($fold -eq 'CONT122'){153}else{151});$status='PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_'+$days+'D_CALENDAR'
 if($source.status -ne $status -or $source.source_files -ne 10 -or $source.days_per_symbol -ne $days){throw 'Existing accepted source scope, not new QA'}
}
$lockSha='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
if((Hash 'state/dataset_lock.json') -ne $lockSha){throw 'Strong separate private lock guard'}
Add $Archive $FactorySha;Add $Helper $HelperSha;Add $Checker $CheckerSha;Add $Comparator $ComparatorSha;Add $failedPath $failedSha;Add $failedCode $failedCodeSha
$sync='reports/GITHUB_VOL_MANAGED_HOLD_547D_SYNC_VERIFIED_20261003_V1.json';Add $sync '409d0e7735235fb577779379536dc1af0d4071e2eb3004324b03f507fc71a9f9'
$verified=Read $sync;if($verified.status -ne 'ACKNOWLEDGED_PUSH_AND_EXACT_REMOTE_MAIN_VERIFIED' -or $verified.local_commit -ne $verified.remote_main -or $verified.actual_git_exit -ne 0){throw 'Accepted previous D034 sync proof'}
foreach($binding in $verified.task_bindings){$null=CheckTask $binding.task.id 0}
# Restrict enumeration to this module's existing ordinary ROOT archives; never all archives or ROOT.
foreach($file in Get-ChildItem -LiteralPath 'docs/archive' -File -Filter 'VOL_MANAGED_HOLD_TWO_PERIOD*'){if($file.Extension -in @('.py','.ps1','.json','.xml','.md')){Add ('docs/archive/'+$file.Name)}}
$actualBindings=@(@($receipts.INDEPENDENT.binding.actual_manifest_path,$receipts.INDEPENDENT.binding.actual_manifest_sha256),@($receipts.COMPARISON.binding.comparison_binding_path,$receipts.COMPARISON.binding.comparison_binding_sha256),@($failedReceipt.binding.actual_manifest_path,$failedReceipt.binding.actual_manifest_sha256))
foreach($pair in $actualBindings){
 if((Hash $pair[0]) -ne $pair[1]){throw 'Actual invoked small manifest/binding changed'};$native=Native $pair[0]
 if($native.StartsWith($Root,[StringComparison]::OrdinalIgnoreCase)){Add ($native.Substring($Root.Length).Replace('\','/')) $pair[1]}
 else{if(@($project.Keys|Where-Object {$_ -like 'docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD*.json' -and $project[$_] -eq $pair[1]}).Count -lt 1){throw 'Archive exact STATE actual-binding JSON under TWO_PERIOD prefix before portable close; no private path in Git'}}
}
$owned=@($descriptions|ForEach-Object {$_[3]})+@('/home/xflops/coin-state/d035-independent-20261003-v1');foreach($p in $owned){$item=Get-Item -LiteralPath (Native $p);if(-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Existing exact six owned directories including preserved failed audit'}}
$files=@($project.Keys|Sort-Object|ForEach-Object {@{path=$_;sha256=$project[$_]}})
$value=[ordered]@{classification='CLOSED_SMALL_METADATA_ONLY_NOT_MARKET_REPLAY';ready_to_execute=$true;created_utc=[DateTime]::UtcNow.ToString('o');helper_sha256=$HelperSha;protocols=$protocols;roles=$roles;failed_roles=$failedRoles;owned_STATE_directories=$owned;project_files=$files;maximum_owned_STATE_bytes=150000000;local_non_git_source_hashes=@{'state/dataset_lock.json'=$lockSha};factory=@{archive=$Archive;sha256=$FactorySha;task_id=$env:COIN_TASK_ID;own_completion='LIVE_CALLER_NOT_CERTIFIED'};legacy_source_task_ids='UNKNOWN_NOT_RETROFITTED';metadata_only=$true;market_or_ledger_arrays_read=$false;old_green_QA_or_accounts_repeated=$false;locked_consumed=$false;candidate_status='NO_QUALIFIED_CANDIDATE'}
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($value|ConvertTo-Json -Depth 35)+[Environment]::NewLine);if($bytes.Length -gt 100000){throw 'Close binding maximum100KB'}
$stream=[IO.File]::Open((Join-Path $Root $Output),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write);try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
@{path=$Output;sha256=Hash $Output;closed_roles=5;preserved_failed_roles=1;source_tasks_fabricated=0;factory_own_completion='LIVE_CALLER_NOT_CERTIFIED'}|ConvertTo-Json
