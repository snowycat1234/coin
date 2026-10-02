# UNRUN D035 metadata factory; root must finalize the new adapter/test SHA before invocation.
param([switch]$RootFinalized,[string]$AdapterSha256='PENDING_ROOT_FINAL_SHA',[string]$TestSha256='PENDING_ROOT_FINAL_SHA')
$ErrorActionPreference='Stop'
if(-not $RootFinalized -or $AdapterSha256 -notmatch '^[0-9a-f]{64}$' -or $TestSha256 -notmatch '^[0-9a-f]{64}$'){throw 'Explicit root-finalized held source/test required; no provisional protocols'}
if($PSVersionTable.PSVersion.Major -lt 7){throw 'Existing PowerShell7 required'}
Set-Location 'D:/codex/coin'
$Root='D:\codex\coin\';$State='\\wsl.localhost\hpc_linux\home\xflops\coin-state\'
$Archive='docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD_PROTOCOL_FREEZER_SOURCE_20261003_V2.ps1'
$Adapter='scripts/investment/vol_managed_two_period_adapter.py';$Test='tests/test_vol_managed_two_period_adapter.py'
$Common='scripts/investment/compare_simple_strategies.py';$OldCommon='bff0fe43a4a46406668a8a7bbe1d298397437a31d6ec623480abff2b2006131e';$CurrentCommon='3dfa0e3176791980de51e5bc990b1998f93eb24c02bdc1261a074eab92fb52f1'
$FinancialAST='39ffd9142be81285b3a6b460c73b1c7799c7621a1c34a2f1faa845d290608b73'
$CoreSha='ee333d4e5cbadb489e5d467619d0872f78ccb2d86d8b5f46eacc69cb63f9829a'
$Smoke='reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_BOUNDARY_TINY_20261003_V1.json'
function Native([string]$p){
 if($p.StartsWith('/home/xflops/coin-state/')){return $State+$p.Substring(24).Replace('/','\')}
 if($p.StartsWith('/mnt/d/codex/coin/')){return $Root+$p.Substring(18).Replace('/','\')}
 return [IO.Path]::GetFullPath($p)
}
function Hash([string]$p){
 $item=Get-Item -LiteralPath (Native $p)
 if($item.PSIsContainer -or $item.Length -gt 2000000 -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or -not ($item.FullName.StartsWith($Root,[StringComparison]::OrdinalIgnoreCase) -or $item.FullName.StartsWith($State,[StringComparison]::OrdinalIgnoreCase))){throw 'Small ordinary metadata/code bytes only'}
 if($item.Extension -notin @('.json','.py','.ps1','.xml','.md','.toml','.lock','.sh') -and -not $item.Name.EndsWith('LICENSE')){throw 'No market/binary byte hash'}
 return (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Read([string]$p){$null=Hash $p;Get-Content -LiteralPath (Native $p) -Raw|ConvertFrom-Json -AsHashtable}
function Canon($value){
 if($value -is [Collections.IDictionary]){$ordered=[ordered]@{};foreach($key in @($value.Keys|Sort-Object)){$ordered[$key]=Canon $value[$key]};return $ordered}
 if($value -is [Collections.IEnumerable] -and $value -isnot [string]){return ,@($value|ForEach-Object {Canon $_})}
 return $value
}
function ClosedReport([string]$path,[string]$expectedSha,[string]$status){
 if((Hash $path) -ne $expectedSha){throw 'Immutable accepted report SHA'}
 $r=Read $path;if($r.status -ne $status -or $r.binding.task_id -notmatch '^[0-9a-f]{32}$'){throw 'Accepted report with true task identity required'}
 $task=Read ($State+'task-progress\task-'+$r.binding.task_id+'.json')
 if($task.id -ne $r.binding.task_id -or $task.status -ne 'completed' -or ($task.exit_code -isnot [int] -and $task.exit_code -isnot [long]) -or $task.exit_code -ne 0){throw 'True closed0 prior native task only'}
 return $r
}
$factorySha=Hash $PSCommandPath
if((Hash $Archive) -ne $factorySha -or (Hash $Adapter) -ne $AdapterSha256 -or (Hash $Test) -ne $TestSha256 -or (Hash $Common) -ne $CurrentCommon -or (Hash 'src/quant/backtest.py') -ne $CoreSha){throw 'Exact held root sources and preserved core'}
$proofs=@(
 @('reports/fast_research/VOL_MANAGED_HOLD_547D_ACTUAL_20261003_V1.json','b56cb8c2ddaf87487acf5e417301135474b982f7cd1dd8572886dea699c4ece6','COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING'),
 @('reports/fast_research/VOL_MANAGED_HOLD_547D_INDEPENDENT_AUDIT_20261003_V1.json','46951463ecf0c910dc3bdf8953437afa0bc0fd2e15650627639855670a5ea2c1','PASS_D034_SINGLE_VM_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR'),
 @('reports/fast_research/VOL_MANAGED_HOLD_547D_ROOT_ACCEPTANCE_20261003_V1.json','32f166e0287dc63365872bca1c3a4787d899ff1e7fb784fa8db6219300e8b1c0','PASS_ROOT_D034_547D_SINGLE_VM_SAVED_SUMMARY_METADATA_NOT_NATIVE_OR_LONG_TERM_APR'))
$prior=@{};foreach($p in $proofs){$prior[$p[0]]=ClosedReport $p[0] $p[1] $p[2]}
if($prior[$proofs[0][0]].fee_derivation.derived_AST_SHA256 -ne $FinancialAST -or $prior[$proofs[0][0]].binding.source_hashes[$Common] -ne $CurrentCommon){throw 'Accepted current common/native financial AST proof'}
$cases=@(
 @{id='CONT122';days=122;parent='protocols/BYBIT_SPOT_2H_122D_V2.json';parentSha='11a667b18ec6c3f779214c28fc0bcfe805319ee8b89e62097f6ee3aa52659192';actual='reports/fast_research/BYBIT_SPOT_2H_122D_ACTUAL_20261002_V2.json';actualSha='53447ac3722829cb5c4db12f5b469b100edb20c05bbb6e9c83f29bce5138bee3';scope='JUL_NOV_2025';months=@('2025-07','2025-08','2025-09','2025-10','2025-11');sourceDays=153;sourceStatus='PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_153D_CALENDAR';rows=440640;pqSha='116448ddf2f2705804aae8b4129515fcbecf5a4d3d3201b9bfd1793a684c5d38';pqBytes=13685003;ipcBytes=42471691;inputDays=153;budget=75000000;start='2025-08-01';end='2025-12-01'},
 @{id='CONT90';days=90;parent='protocols/BYBIT_SPOT_2H_90D_V2.json';parentSha='8505eec0f6406d7725962856455e3dfdbefda6139503f5e2d7856443383ca457';actual='reports/fast_research/BYBIT_SPOT_2H_90D_ACTUAL_20261002_V2.json';actualSha='329f9f923ed4fd8223e2e267a200c2e67036c8ce4f82a7fef0027efdd3b7960a';scope='OCT2025_FEB2026';months=@('2025-10','2025-11','2025-12','2026-01','2026-02');sourceDays=151;sourceStatus='PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_151D_CALENDAR';rows=348480;pqSha='96adcfe79bb73f11bcdc924e83b43d51f6381c7b43977be90504f968b3bd0905';pqBytes=10745548;ipcBytes=33588651;inputDays=121;budget=60000000;start='2025-12-01';end='2026-03-01'})
$union=@{};$parents=@{};$native=@{};$sourceProofs=@{}
foreach($c in $cases){
 if((Hash $c.parent) -ne $c.parentSha){throw 'Exact accepted native parent protocol'}
 $s=Read $c.parent;$parents[$c.id]=$s;$a=ClosedReport $c.actual $c.actualSha 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING';$native[$c.id]=$a
 if($a.binding.protocol_sha256 -ne $c.parentSha -or $a.fee_derivation.derived_AST_SHA256 -ne $FinancialAST -or -not $a.all_planned_ledgers_complete -or $a.completed_ledgers -ne 3 -or -not $a.source_bytes_unchanged -or $a.minute_source.rows -ne $c.rows -or $a.minute_source.invalid_minutes -ne 0 -or $a.minute_source.sha256 -ne $c.pqSha){throw 'Actual accepted native derivative/protocol identity'}
 if($s.folds.Count -ne 1 -or $s.folds[0].id -ne $c.id -or $s.folds[0].period_start -ne $c.start -or $s.folds[0].period_end_exclusive -ne $c.end -or $s.warmup_days -ne 31 -or $s.common_config.initial_cash -ne 10000 -or $s.common_config.per_symbol_cap -ne .3 -or $s.common_config.gross_cap -ne .6){throw 'Only original fixed development period/warmup/capital/risk'}
 # Legacy source acceptance has no actual task id; preserve its real status/SHA, never retrofit one.
 if((Hash $s.source_receipt) -ne $s.source_receipt_sha256){throw 'Old accepted source metadata SHA'}
 $source=Read $s.source_receipt
 if($source.status -ne $c.sourceStatus -or $source.days_per_symbol -ne $c.sourceDays -or $source.source_files -ne 10){throw 'Accepted source universe, not new QA'}
 $sourceProofs[$c.id]=@{path=$s.source_receipt;sha256=$s.source_receipt_sha256;status=$source.status;task_id='UNKNOWN_LEGACY_NOT_RETROFITTED';fresh_QA=$false}
 # File stat only. Do not rehash or read any saved market derivative before the new protocol.
 $pq=Get-Item -LiteralPath (Native $a.minute_source.path);$ipc=Get-Item -LiteralPath (Native ($a.minute_source.path.Substring(0,$a.minute_source.path.LastIndexOf('/'))+'/'+$c.id+'-minute-input.arrow'))
 if($pq.Length -ne $c.pqBytes -or $ipc.Length -ne $c.ipcBytes -or ($pq.Attributes -band [IO.FileAttributes]::ReparsePoint) -or ($ipc.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Exact observed derivative sizes'}
 foreach($name in $s.frozen_sources.Keys){
  $old=$s.frozen_sources[$name];$now=Hash $name
  if($name -eq $Common){if($old -ne $OldCommon -or $now -ne $CurrentCommon){throw 'Only explicit old-to-accepted-current common transition'}}elseif($old -ne $now){throw "Other parent pin mismatch: $name"}
  if($union.Contains($name) -and $union[$name] -ne $now){throw 'Conflicting shared source union'};$union[$name]=$now
 }
 $union[$c.parent]=$c.parentSha;$union[$c.actual]=$c.actualSha;$union[$s.source_receipt]=$s.source_receipt_sha256
}
foreach($p in $proofs){$union[$p[0]]=$p[1]}
$utilityPins=@{
 'scripts/investment/public_long_development_adapter.py'='15ea3a089f39149d9d669fa3425fa35821c2c01b3cce1c15f751fd1723a9406f'
 'scripts/investment/public_donchian_hybrid.py'='80e4b24319becacefb0d6c9551473e3d4214cf3167ae45f5ac8ff7f559c27d68'
 'scripts/investment/bulk_fixed_targets.py'='d750b99449cba479544a6003d455bedba2776959c48c09342252828ef413d58f'
 'scripts/research_v8/benchmark_targets.py'='cb3158116494c41b6649f80dc4013b3c1ff9e495773b3ae298d9d5b6e9d46652'
 'scripts/research_v8/benchmark_targets_v2.py'='72235137633847101af57e658f8a50ea50494e1a63de663784754d72fef81a82'
 'scripts/research_v8/labels_v3.py'='cedc8fff7cca288bb318b272e3718ac9cb1df6edc6be924e6112d1af9cb5d078'
 'scripts/research_v8/public_donchian_adapter.py'='169d7ba6ebde24be5ce4730c5e741ed281a0155e4cadc22f1bb2bedccb4093c2'
 'scripts/investment/bybit_spot_adapter.py'='8c8852bf70813ada5720c210f50c9038a5ecaadee1b4f38b77a71aa9e8b038ca'
}
foreach($name in $utilityPins.Keys){if((Hash $name) -ne $utilityPins[$name]){throw 'Exact reusable namespace utility/module dependency'};$union[$name]=$utilityPins[$name]}
$union[$Adapter]=$AdapterSha256;$union[$Test]=$TestSha256;$union[$Archive]=$factorySha
$economicRules=@{VOL_MANAGED_BUY_AND_HOLD='Original .3/.3 gross reference basket, all available completed daily return prefix EWMA span7/min7 adjustFalse unbiased, same past seed and cap multiplier; original30day/min20 common risk retained';entry_and_capital='Original first intent and independent10k per period; no warmup cash or trades, no resets inside period';execution='Original minute latency/lot/previous-volume capacity and terminal marked remainder; native received-asset settlement unchanged';selection='Only fixed VM at36bp, no fitting/HPO/threshold change, no winner-month or account stitching'}
$outputs=@()
foreach($c in $cases){
 # Deep clone; the two accepted parent protocols remain byte-identical and are historical proofs.
 $s=($parents[$c.id]|ConvertTo-Json -Depth 40)|ConvertFrom-Json -AsHashtable
 foreach($key in @('reused_target_inputs','reused_reference_report','paired_control_reference','additional_target_acceptance','preceding_failure','smoke_pytest_expression')){$s.Remove($key)}
 $s.contract_id='VOL_MANAGED_HOLD_'+$c.days+'D_BYBIT_20261003_V1';$s.classification='PREVIOUSLY_SEEN_NATIVE_FEE_PROXY_VM_SCREENING_NOT_UNSEEN';$s.primary_reference='VOL_MANAGED_BUY_AND_HOLD';$s.strategy_ids=@('VOL_MANAGED_BUY_AND_HOLD');$s.planned_ledgers=1
 $s.namespace_parent_protocol=@{path=$c.parent;sha256=$c.parentSha};$s.parent_protocol=@{path=$c.parent;sha256=$c.parentSha;role='Exact historical date/source/capital/fee parent; current common explicit transition and one36bp subset'}
 $s.frozen_sources=@{};foreach($name in $union.Keys){$s.frozen_sources[$name]=$union[$name]}
 $s.costs.spread_bps=@(8);$s.costs.nominal_roundtrip_bps=@(36);$s.strategy_rules=$economicRules
 $s.source_scope=$c.scope;$s.source_calendar=$c.months;$s.source_days_per_symbol=$c.sourceDays
 $s.reused_minute_input=@{report_path=$c.actual;report_sha256=$c.actualSha;path=$native[$c.id].minute_source.path;sha256=$c.pqSha}
 $s.reused_input_metadata=@{source_days_per_symbol=$c.sourceDays;actual_derivative_days_per_symbol=$c.inputDays;actual_derivative_rows=$c.rows;parquet_bytes=$c.pqBytes;ipc_bytes=$c.ipcBytes;market_bytes_read_or_rehashed_during_freeze=$false;original_Parquet_reader_and_new_Parquet_IPC_copy_semantics_preserved=$true}
 $s.source_acceptance_history=$sourceProofs[$c.id];$s.common_source_transition=@{path=$Common;historical_sha256=$OldCommon;active_sha256=$CurrentCommon;old_parent_source_map_not_rewritten=$true;current_common_prior_actual=$proofs[0][0];current_common_prior_independent=$proofs[1][0];current_common_prior_root=$proofs[2][0];native_financial_AST_sha256=$FinancialAST;core_sha256=$CoreSha;change='Accepted thin source/date/report support; new VM onecost private cost-loop adapter, no fee or financial kernel rewrite'}
 $s.required_smoke_receipt=$Smoke;$s.smoke_test_path=$Test;$s.shared_single_smoke_scope='One fresh case under122 child jointly covers both metadata namespaces; original native shared-code/economic filter accepts90 separately verified source/period'
 $s.maximum_wall_seconds=900;$s.maximum_new_owned_bytes=$c.budget;$s.maximum_per_process_RSS_bytes=3500000000;$s.independent_maximum_wall_seconds=600
 $s.module_combined_STATE_budget_bytes=150000000;$s.module_subbudgets=@{research122=75000000;research90=60000000;synthetic=10000000;independent_root_metadata=5000000;source=0};$s.fixed_budget_before_market_IO=@{original_input_copies122=56156694;original_input_copies90=44334199;combined_original_inputs=100490893;new_outputs_measurement='NOT_YET_RUN'}
 $s.research_output_path='reports/fast_research/VOL_MANAGED_HOLD_'+$c.days+'D_ACTUAL_20261003_V1.json';$s.research_run_dir='/home/xflops/coin-state/vol-managed-hold-'+$c.days+'d-actual-20261003-v1';$s.production_entrypoint=$Adapter
 $s.market_models_fit=0;$s.orders_sent=0;$s.GPU=0;$s.locked_consumed=$false;$s.candidate_status='NO_QUALIFIED_CANDIDATE';$s.created_before_new_market_economics_utc=[DateTime]::UtcNow.ToString('o');$s.actual_freeze_git_commit=(& git rev-parse HEAD).Trim()
 $s.saved_comparison_references=@{native_2h=@{path=$c.actual;sha256=$c.actualSha};role='Saved accepted same-period36bp controls only; future comparison may add pinnedhybrid/CASH without replay'}
 $s.local_non_git_source_hashes=@{'state/dataset_lock.json'='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'}
 $s.limitations=@($s.limitations)+@('Independent122d/90d development accounts, not stitched or unseen; sustainableAPR not established.','Same risk rules do not imply equal realized risk. VM baseline original all-past EWMA and native common risk both retained.','Legacy source receipts have no taskid; only original acceptanceSHA/status and true closed native derivative evidence reused, no newQA.','Oldcommon bff source history is retained; current3dfa support already accepted, native financial AST39ffd and coreee333 unchanged.','Single shared new synthetic acceptance is not reused old green; selected period source/derivative/date remains independently guarded.')
 $outputs+=@{path='protocols/'+$s.contract_id+'.json';spec=$s}
}
foreach($key in @('common_config','costs','strategy_rules','environment','fee_settlement','fee_profile_path','fee_profile_sha256','market_type','frozen_sources')){if(((Canon $outputs[0].spec[$key])|ConvertTo-Json -Depth 40 -Compress) -ne ((Canon $outputs[1].spec[$key])|ConvertTo-Json -Depth 40 -Compress)){throw "Shared synthetic interface differs: $key"}}
foreach($out in $outputs){if(Test-Path -LiteralPath $out.path){throw 'Exclusive new child protocol paths'}}
foreach($out in $outputs){$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($out.spec|ConvertTo-Json -Depth 40)+[Environment]::NewLine);if($bytes.Length -gt 200000){throw 'Small protocol only'};$f=[IO.File]::Open((Join-Path $Root $out.path),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write);try{$f.Write($bytes,0,$bytes.Length)}finally{$f.Dispose()}}
@($outputs|ForEach-Object {@{path=$_.path;sha256=Hash $_.path;strategy='VOL_MANAGED_BUY_AND_HOLD';planned_ledgers=1;old_source_QA_repeated=$false;new_market_IO_during_freeze=$false}})|ConvertTo-Json
