# UNEXECUTED exact D034 metadata freezer. Final source and capacity authorized before any new arrays.
$AdapterPath='scripts/investment/public_long_vol_managed_adapter.py'
$AdapterSha256='cdaaebe4889d7eddc4dd950f003eb73342080ffe4b844342d3e4f3d2b36f2088'
$TestPath='tests/test_public_long_vol_managed_adapter_v2.py'
$TestSha256='01b801cd8c9d614e1fce88c14377777a65507b5a2c12f541e09c1390121e2b2e'
$ResearchOwnedBytes=280000000L
$ModuleOwnedBytes=300000000L
$FreezerArchivePath='docs/archive/VOL_MANAGED_HOLD_547D_PROTOCOL_FREEZER_SOURCE_20261003_V2.ps1'
$FinalBudgetApproved=$true
# Exact original parent and new held source hashes below are metadata-only; parent archives source, then invokes once.
$ErrorActionPreference='Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Existing bundled PowerShell7 required; no installation' }
Set-Location 'D:/codex/coin'
if (-not $FinalBudgetApproved -or $ResearchOwnedBytes -gt $ModuleOwnedBytes -or ($ModuleOwnedBytes-$ResearchOwnedBytes) -lt 10000000) {
  throw 'Final explicit preregistered capacity budget and at least10MB outside research required'
}
function Digest([string]$Path) {
  $item=Get-Item -LiteralPath $Path
  if ($item.PSIsContainer -or $item.Length -gt 2000000 -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Small ordinary project metadata/code only: $Path" }
  $resolved=[IO.Path]::GetFullPath($item.FullName)
  if (-not $resolved.StartsWith('D:\codex\coin\',[StringComparison]::OrdinalIgnoreCase)) { throw 'ROOT-only small source digest' }
  (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function CheckedReport([string]$Path,[string]$ExpectedSha,[string]$ExpectedStatus) {
  if ((Digest $Path) -ne $ExpectedSha) { throw "Immutable saved report changed: $Path" }
  $value=Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -AsHashtable
  if ($value.status -ne $ExpectedStatus) { throw "Actual accepted status required: $Path" }
  $id=$value.binding.task_id
  if ($id -notmatch '^[0-9a-f]{32}$') { throw 'Exact prior actual task id required' }
  $taskPath='\\wsl.localhost\hpc_linux\home\xflops\coin-state\task-progress\task-'+$id+'.json'
  $task=Get-Content -LiteralPath $taskPath -Raw | ConvertFrom-Json -AsHashtable
  if ($task.id -ne $id -or $task.status -ne 'completed' -or $task.exit_code -ne 0) { throw 'Prior accepted report must have actual completed0' }
  return $value
}
$parentPath='protocols/PUBLIC_LONG_547D_FIXED_THREE_ACCOUNTS_20261003_V1.json'
$parentSha='5366363196157c1629e2e00a00301956e61b2c295b476520359bc0bd55ac746d'
if ((Digest $parentPath) -ne $parentSha) { throw 'Exact original D033 protocol required' }
$s=Get-Content -LiteralPath $parentPath -Raw | ConvertFrom-Json -AsHashtable
if ($s.folds.Count -ne 1 -or $s.folds[0].id -ne 'CONT547' -or $s.folds[0].period_start -ne '2024-01-01' -or $s.folds[0].period_end_exclusive -ne '2025-07-01' -or $s.warmup_days -ne 31) { throw 'Only original547day calendar with31day warmup' }
$months=@('2023-12')+@(1..12|ForEach-Object{'2024-{0:d2}'-f $_})+@(1..6|ForEach-Object{'2025-{0:d2}'-f $_})
if ($s.source_scope -ne 'DEC2023_JUN2025' -or $s.source_days_per_symbol -ne 578 -or ($s.source_calendar -join ',') -ne ($months -join ',')) { throw 'Exact accepted19months and578source days required' }
if ($s.common_config.initial_cash -ne 10000 -or $s.common_config.per_symbol_cap -ne .3 -or $s.common_config.gross_cap -ne .6 -or $s.common_config.target_annual_vol -ne .1 -or $s.common_config.vol_window_days -ne 30 -or $s.common_config.min_vol_days -ne 20) { throw 'Preserved capital/caps/risk only' }
if ($s.costs.fee_bps_per_side -ne 10 -or $s.costs.slippage_bps_per_side -ne 4 -or ($s.costs.spread_bps -join ',') -ne '8' -or ($s.costs.nominal_roundtrip_bps -join ',') -ne '36') { throw 'Only original36bp received-asset spot scenario' }
$fee='protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json';$feeSha='d6c1e2f5b25dabf4d088edfbccbc35d7154684287ff477c2fc16a14ee5f96b3f'
if ($s.fee_settlement -ne 'BYBIT_SPOT_RECEIVED_ASSET_V1' -or $s.fee_profile_path -ne $fee -or $s.fee_profile_sha256 -ne $feeSha -or (Digest $fee) -ne $feeSha) { throw 'Unchanged fixed ordinary Bybit Spot profile' }
foreach($name in @($s.frozen_sources.Keys)) { if ((Digest $name) -ne $s.frozen_sources[$name]) { throw "Original frozen dependency changed: $name" } }
$sourcePath='reports/fast_research/PUBLIC_LONG_547D_SOURCE_REUSE_20261003_V1.json';$sourceSha='64dc9474828b1707b21a7ed09b5719f202645cbc4ceb72007d9775d72d67fee2'
$source=CheckedReport $sourcePath $sourceSha 'PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_578D_CALENDAR'
if ($source.source_files -ne 38 -or $source.actual_minute_rows -ne 1664640 -or $source.days_per_symbol -ne 578) { throw 'Only existing accepted38source metadata' }
$actualPath='reports/fast_research/PUBLIC_LONG_547D_ACTUAL_20261003_V1.json';$actualSha='c70e3011f74ddbbbf250316bb2cad9a02d2bd6945b266a1a96a1083b9fcbc6e8'
$actual=CheckedReport $actualPath $actualSha 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING'
$auditPath='reports/fast_research/PUBLIC_LONG_547D_THREE_LEDGER_INDEPENDENT_AUDIT_20261003_V3.json';$auditSha='c7033ef299071f1d3149381fc19d923487bbbdd1040c4b20c75481058203441d'
$audit=CheckedReport $auditPath $auditSha 'PASS_D033_THREE_NATIVE_SPOT_LEDGER_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR'
$rootPath='reports/fast_research/PUBLIC_LONG_547D_ROOT_ACCEPTANCE_20261003_V1.json';$rootSha='3c34b9b01b84d2febc6692e8d0d310ce2f416ade0b1a7006b434c176ef03f76c'
$rootReceipt=CheckedReport $rootPath $rootSha 'PASS_ROOT_D033_547D_THREE_ACCOUNT_SAVED_SUMMARY_METADATA_NOT_NATIVE_OR_LONG_TERM_APR'
$minutePath='/home/xflops/coin-state/public-long-547d-actual-20261003-v1/shared_source_minutes.parquet';$minuteSha='69ee7e5b8bee31f1cc28cbfbee4c99176060959a0e7d831683a3fddc796a06d2'
if (-not $actual.source_bytes_unchanged -or -not $actual.all_planned_ledgers_complete -or $actual.completed_ledgers -ne 3 -or $actual.source_receipt_sha256 -ne $sourceSha -or $actual.minute_source.path -ne $minutePath -or $actual.minute_source.sha256 -ne $minuteSha -or $actual.minute_source.rows -ne 1664640 -or $actual.minute_source.invalid_minutes -ne 0 -or $audit.actual_report_sha256 -ne $actualSha) { throw 'Exact completed parent derivative metadata, not old targets replay' }
# STAT ONLY: do not hash/read the market derivative or IPC before the new research is preregistered.
$parquetStat=Get-Item -LiteralPath '\\wsl.localhost\hpc_linux\home\xflops\coin-state\public-long-547d-actual-20261003-v1\shared_source_minutes.parquet'
$ipcStat=Get-Item -LiteralPath '\\wsl.localhost\hpc_linux\home\xflops\coin-state\public-long-547d-actual-20261003-v1\CONT547-minute-input.arrow'
if ($parquetStat.Length -ne 50992557 -or $ipcStat.Length -ne 160444779 -or $actual.folds[0].minute_input_sha256 -ne '1d1a2e49b15f0430248ac77fbc745b15e498cc7b14307244712720c6f417ec27') { throw 'Observed prior size/receipt mismatch' }
if ((Digest $AdapterPath) -ne $AdapterSha256 -or (Digest $TestPath) -ne $TestSha256) { throw 'Pending child adapter/test must be actual root-frozen bytes before protocol creation' }
$freezerSha=Digest $PSCommandPath
if ((Digest $FreezerArchivePath) -ne $freezerSha) { throw 'Archive exact unexecuted freezer bytes before one invocation' }
foreach($key in @('reused_reference_report','reused_target_inputs','paired_control_reference','preceding_failure','smoke_pytest_expression')) { $s.Remove($key) }
$priorFailurePath='reports/fast_research/VOL_MANAGED_HOLD_547D_BOUNDARY_TINY_20261003_V1.json'
$priorFailureSHA='a09f779f3dabdad7cfa8e60d2884ff21e2e82206850caab67b0361eb5938e21d'
if ((Digest $priorFailurePath) -ne $priorFailureSHA -or (Digest 'protocols/VOL_MANAGED_HOLD_547D_BYBIT_20261003_V1.json') -ne '685ecb9b1f737db821f301df939aa767ac16ef300e48880c2081a8c109c81c6e' -or (Digest 'tests/test_public_long_vol_managed_adapter.py') -ne 'be56f209bc726462012676cc590ef561a46e8959ce19005293564f3ca3262111') { throw 'Original failed boundary source/protocol/receipt must be preserved' }
$s.preceding_failure=@{report_path=$priorFailurePath;report_sha256=$priorFailureSHA;host_result='session7560/chunka429aa/exit1';reason='Only synthetic assertion assumed unsorted group_by output chronology; production causal function already sorts; new test explicitly sorts its daily reference';original_strategy_fee_risk_unchanged=$true}
foreach($name in @($priorFailurePath,'protocols/VOL_MANAGED_HOLD_547D_BYBIT_20261003_V1.json','tests/test_public_long_vol_managed_adapter.py','docs/archive/VOL_MANAGED_HOLD_547D_PROTOCOL_FREEZER_SOURCE_20261003_V1.ps1')) { $s.frozen_sources[$name]=Digest $name }
$s.contract_id='VOL_MANAGED_HOLD_547D_BYBIT_20261003_V2'
$s.parent_protocol=@{path=$parentPath;sha256=$parentSha;role='Exact original dates/source/native/risk; new VM-only subset, no old account or target replay'}
$s.namespace_parent_protocol=@{path=$parentPath;sha256=$parentSha}
$s.classification='PREVIOUSLY_SEEN_547D_BINANCE_SPOT_BYBIT_VIP0_VOL_MANAGED_HOLD_SCREENING_NOT_UNSEEN'
$s.primary_reference='VOL_MANAGED_BUY_AND_HOLD'
$s.primary_selection_reason='D034 fixed simple exposure baseline before new results; compare saved public2h/hybrid/CASH only'
$s.strategy_ids=@('VOL_MANAGED_BUY_AND_HOLD');$s.planned_ledgers=1
$s.maximum_wall_seconds=1800;$s.maximum_new_owned_bytes=$ResearchOwnedBytes
$s.module_combined_STATE_budget_bytes=$ModuleOwnedBytes
$s.module_subbudgets=@{research=$ResearchOwnedBytes;source=0;synthetic=10000000;independent_and_root_and_metadata=10000000}
$s.maximum_per_process_RSS_bytes=3500000000;$s.independent_maximum_wall_seconds=600
$s.reused_minute_input=@{report_path=$actualPath;report_sha256=$actualSha;path=$minutePath;sha256=$minuteSha}
$s.saved_comparison_references=@{actual=@{path=$actualPath;sha256=$actualSha};independent=@{path=$auditPath;sha256=$auditSha};root=@{path=$rootPath;sha256=$rootSha};role='Previously seen saved three-account comparison only; no calls to prior simulator or targets'}
$s.required_smoke_receipt='reports/fast_research/VOL_MANAGED_HOLD_547D_BOUNDARY_TINY_20261003_V2.json'
$s.smoke_test_path=$TestPath
$s.research_output_path='reports/fast_research/VOL_MANAGED_HOLD_547D_ACTUAL_20261003_V1.json'
$s.research_run_dir='/home/xflops/coin-state/vol-managed-hold-547d-actual-20261003-v1'
$s.strategy_rules=@{VOL_MANAGED_BUY_AND_HOLD='Unchanged original fixed.3/.3 gross basket daily returns, past-only full-prefix EWMA span7/min7 annualvol multiplier min(1,.10/max(.01,vol)); update at existing closed UTCday boundary; original common30day/min20 intent-risk layer also retained';causality='Original complete source/warmup/reference_daily_returns/target calendar and execution risk availability';terminal='Original costed terminal zero target, realistic original latency/capacity/lot and marked remainder';selection='One fixed547day VM account at36bp, no winner/month selection, HPO, fitting, leverage or reduced cost'}
$s.research_question='Does original volatility-managed passive exposure retain net economic advantage at comparable realized risk to saved public2h/hybrid across the same full547days?'
$s.return_reporting='One new continuous547day VM account; old three parent accounts remain saved references; descriptive CAGR is not demonstrated future APR'
$s.continuity_invariants.source='Reuse exact accepted shared-source Parquet with original reused_minute_input; old38raw files/QA not reread; original newParquet andArrow materialization remains'
$s.continuity_invariants.strategy='Original VOL_MANAGED_BUY_AND_HOLD only; no new parameter or economic rule'
$s.fixed_budget_reason='Accepted parent stat-only inputs: Parquet50992557B + IPC160444779B=211437336B; original per-account intent21.37MB and active minute ledgerabout27MB; final explicit capacity approved before new arrays'
$s.io_stat_only_budget_basis=@{parent_parquet_bytes=50992557;parent_ipc_bytes=160444779;new_original_input_copies_bytes=211437336;parent_intent_calendar_bytes_about=21370000;parent_active_minute_ledger_bytes_about=27000000;parent_market_bytes_hashed_or_rows_read_during_freeze=$false;original_copy_semantics_preserved=$true;account_output_sizes_not_yet_measured=$true}
$s.local_non_git_source_hashes=@{'state/dataset_lock.json'='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'}
$s.portable_git_policy='Scientific frozen_sources retain private lock enforcement; only later Git-specific projection excludes exact local lock into separately enforced local_non_git_source_hashes'
$s.limitations+=@('VM adds simple exposure baseline evidence only, not a new qualified candidate; compare realized risk/exposure and all costs to saved full-period controls','BybitVIP0 settlement and fee counterfactual on historical Binance data remain; nativeBybit market/filter/BBO/fee-history not certified','No newraw source QA or38 price file read; original derivative currentSHA/schema/calendar verification occurs only in preregistered bounded research')
$s.created_before_new_economics_utc=[DateTime]::UtcNow.ToString('o');$s.actual_freeze_git_commit=(git rev-parse HEAD).Trim()
foreach($name in @($parentPath,$sourcePath,$actualPath,$auditPath,$rootPath,$AdapterPath,$TestPath,$FreezerArchivePath)) { $s.frozen_sources[$name]=Digest $name }
if ((Digest $parentPath) -ne $parentSha -or (Digest $actualPath) -ne $actualSha -or (Digest $AdapterPath) -ne $AdapterSha256 -or (Digest $TestPath) -ne $TestSha256 -or (Digest $FreezerArchivePath) -ne $freezerSha) { throw 'Small metadata/source pins changed before exclusive freeze' }
$out='protocols/VOL_MANAGED_HOLD_547D_BYBIT_20261003_V2.json'
if (Test-Path -LiteralPath $out) { throw 'Exclusive new protocol required, do not overwrite evidence' }
$json=($s|ConvertTo-Json -Depth 60)+[Environment]::NewLine
$bytes=[Text.UTF8Encoding]::new($false).GetBytes($json)
if ($bytes.Length -gt 100000) { throw 'Small metadata only' }
$stream=[IO.File]::Open((Join-Path (Get-Location) $out),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
try { $stream.Write($bytes,0,$bytes.Length) } finally { $stream.Dispose() }
@{path=$out;sha256=Digest $out;head=$s.actual_freeze_git_commit;planned_ledgers=1;reuse_input_format='ORIGINAL_PARQUET_REUSED_MINUTE_INPUT_SCHEMA';research_budget=$ResearchOwnedBytes;module_budget=$ModuleOwnedBytes;market_IO_during_freeze=$false;new_source_QA=$false;source_derivative_sha256=$minuteSha} | ConvertTo-Json
