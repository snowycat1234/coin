$ErrorActionPreference='Stop'
Set-Location 'D:/codex/coin'
function TaskDigest([string]$Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
$archive='docs/archive/PUBLIC_SMA_DAILY_ROOT_BINDING_FREEZER_20261003_V2.ps1'
if(Test-Path -LiteralPath $archive){throw 'Exclusive root binder archive'}
[IO.File]::WriteAllBytes((Join-Path (Get-Location) $archive),[IO.File]::ReadAllBytes($PSCommandPath))
$rows=@(
 @('VENDOR','SMACROSSOVER_OFFICIAL_SOURCE_PROVENANCE_20261003_V1.json','PASS_D038_PINNED_SMA_SOURCE_BYTES_AND_MIT_PROVENANCE_ONLY','d038-sma-official-source-20261003-v1'),
 @('TINY','PUBLIC_SMA_DAILY_BOUNDARY_TINY_20261003_V2.json','PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT','d038-public-sma-smoke-20261003-v2'),
 @('MARKET547','PUBLIC_SMA_DAILY_547D_ACTUAL_20261003_V1.json','COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING','d038-public-sma-547d-actual-20261003-v1'),
 @('MARKET122','PUBLIC_SMA_DAILY_122D_ACTUAL_20261003_V1.json','COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING','d038-public-sma-122d-actual-20261003-v1'),
 @('MARKET90','PUBLIC_SMA_DAILY_90D_ACTUAL_20261003_V1.json','COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING','d038-public-sma-90d-actual-20261003-v1'),
 @('INDEPENDENT','PUBLIC_SMA_DAILY_THREE_PERIOD_INDEPENDENT_AUDIT_20261003_V2.json','PASS_D038_THREE_SMA_DAILY_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR','d038-sma-three-ledger-independent-20261003-v2'))
$roles=[ordered]@{}
foreach($row in $rows){$name='reports/fast_research/'+$row[1];$v=Get-Content -LiteralPath $name -Raw|ConvertFrom-Json -AsHashtable;if($v.status -ne $row[2]){throw ('Actual PASS required '+$row[0])};$roles[$row[0]]=[ordered]@{report=$name;report_sha256=TaskDigest $name;required_status=$row[2];task_id=$v.binding.task_id;run_binding='/home/xflops/coin-state/'+$row[3]+'/RUN_BINDING.json';run_binding_sha256=$v.run_binding_sha256}}
$name='reports/fast_research/PUBLIC_SMA_DAILY_ECONOMIC_COMPARISON_20261003_V1.json';$c=Get-Content -LiteralPath $name -Raw|ConvertFrom-Json -AsHashtable
$extra=[ordered]@{COMPARISON=[ordered]@{report=$name;report_sha256=TaskDigest $name;required_status='COMPLETE_D038_SAVED_METRICS_COMPARISON_NOT_NEW_ACCOUNT_OR_LONG_TERM_APR';task_id=$c.binding.task_id}}
$owns=@(@{path='/home/xflops/coin-state/d038-sma-official-source-20261003-v1';maximum_bytes=10000000},@{path='/home/xflops/coin-state/d038-public-sma-smoke-20261003-v1';maximum_bytes=10000000},@{path='/home/xflops/coin-state/d038-public-sma-smoke-20261003-v2';maximum_bytes=10000000},@{path='/home/xflops/coin-state/d038-public-sma-547d-actual-20261003-v1';maximum_bytes=280000000},@{path='/home/xflops/coin-state/d038-public-sma-122d-actual-20261003-v1';maximum_bytes=70000000},@{path='/home/xflops/coin-state/d038-public-sma-90d-actual-20261003-v1';maximum_bytes=60000000},@{path='/home/xflops/coin-state/d038-sma-three-ledger-independent-20261003-v1';maximum_bytes=10000000})
$pins=[ordered]@{}
foreach($file in @($archive,'scripts/investment/audit_public_sma_daily_ledgers.py','docs/archive/PUBLIC_SMA_DAILY_INDEPENDENT_TARGET_SOURCE_20261003_V1.py','docs/archive/PUBLIC_SMA_DAILY_INDEPENDENT_UNRUN_DRAFT_20261003_V1.py','docs/archive/PUBLIC_SMA_DAILY_INDEPENDENT_ACTUAL_BINDING_20261003_V2.json','scripts/investment/audit_public_daily_ledgers.py','docs/archive/PUBLIC_LONG_547D_USED_INDEPENDENT_SOURCES_20261003_V3/reuse_blocks.py','docs/archive/CONDITIONAL_CARRY_USED_INDEPENDENT_SOURCES_20261003_V1/audit.py','docs/archive/PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_AUDIT_CHECKER_20261002_V1.py','docs/archive/PUBLIC_SMA_DAILY_SAVED_COMPARISON_SOURCE_20261003_V2.py','docs/archive/PUBLIC_SMA_DAILY_RESEARCH_FREEZER_20261003_V1.py','docs/archive/PUBLIC_SMA_DAILY_RESEARCH_FREEZER_20261003_V2.py','docs/archive/PUBLIC_SMA_DAILY_ROOT_CLOSE_SOURCE_20261003_V1.py')){$pins[$file]=TaskDigest $file}
$failed=@(@{report='reports/fast_research/PUBLIC_SMA_DAILY_BOUNDARY_TINY_20261003_V1.json';report_sha256=TaskDigest 'reports/fast_research/PUBLIC_SMA_DAILY_BOUNDARY_TINY_20261003_V1.json';task_id='4c2db7bfba664a44a2a28a66b25172ef'})
$helper='docs/archive/PUBLIC_SMA_DAILY_ROOT_CLOSE_SOURCE_20261003_V3.py'
$owns+=@{path='/home/xflops/coin-state/d038-sma-three-ledger-independent-20261003-v2';maximum_bytes=10000000}
foreach($file in @('docs/archive/OPEN_SOURCE_REGISTRY_SMACROSSOVER_ACCEPTED_20261003_V1.md','scripts/investment/audit_public_sma_daily_ledgers_v2.py','docs/archive/PUBLIC_SMA_DAILY_INDEPENDENT_ACTUAL_BINDING_20261003_V1.json','docs/archive/PUBLIC_SMA_DAILY_ROOT_BINDING_FREEZER_20261003_V1.ps1','docs/archive/PUBLIC_SMA_DAILY_ROOT_CLOSE_SOURCE_20261003_V2.py','docs/archive/PUBLIC_SMA_DAILY_SAVED_COMPARISON_SOURCE_20261003_V1.py')){$pins[$file]=TaskDigest $file}
$failed+=@{report='reports/fast_research/PUBLIC_SMA_DAILY_THREE_PERIOD_INDEPENDENT_AUDIT_20261003_V1.json';report_sha256=TaskDigest 'reports/fast_research/PUBLIC_SMA_DAILY_THREE_PERIOD_INDEPENDENT_AUDIT_20261003_V1.json';task_id='f8285234aef34fc7a35dc97484ee944c'}
$plan=[ordered]@{helper_sha256=TaskDigest $helper;roles=$roles;extra_closed_metadata_roles=$extra;owned_directories=$owns;project_sources=$pins;preserved_failures=$failed}
$out='protocols/PUBLIC_SMA_DAILY_ROOT_BINDING_20261003_V2.json';if(Test-Path -LiteralPath $out){throw 'Exclusive root binding'}
[IO.File]::WriteAllText((Join-Path (Get-Location) $out),($plan|ConvertTo-Json -Depth 12)+"`n",[Text.UTF8Encoding]::new($false))
[ordered]@{binding=$out;sha256=TaskDigest $out;closed0_roles_required=7;market_accounts_replayed=$false}|ConvertTo-Json -Compress
