param([ValidateSet('Financial','Comparison')][string]$Phase)
$ErrorActionPreference='Stop';$root='D:/codex/coin';$enc=[Text.UTF8Encoding]::new($false)
function Digest([string]$p){(Get-FileHash -LiteralPath (Join-Path $root $p) -Algorithm SHA256).Hash.ToLowerInvariant()}
function ReadJson([string]$p){Get-Content (Join-Path $root $p) -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
function WriteNew([string]$p,$v){if(Test-Path (Join-Path $root $p)){throw "Exclusive path $p"};[IO.File]::WriteAllText((Join-Path $root $p),($v|ConvertTo-Json -Depth 50)+"`n",$enc)}
$proto='protocols/PERPETUAL_HOLD_RESEARCH_20261003_V1.json';$spec=ReadJson $proto
$marketPath='reports/fast_research/PERPETUAL_HOLD_RESEARCH_ACTUAL_20261003_V1.json';$market=ReadJson $marketPath
if($market.status -ne 'COMPLETE_D044_TWELVE_CONDITIONAL_PERPETUAL_HOLD_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR' -or $market.completed_cases -ne 12){throw 'Twelve actual selectors required'}
$hashes=[ordered]@{}
foreach($p in $spec.frozen_sources.Keys){if((Digest $p) -ne $spec.frozen_sources[$p]){throw "Frozen source $p"};$hashes[$p]=$spec.frozen_sources[$p]}
foreach($p in @($proto,$marketPath,'scripts/investment/audit_perpetual_hold_research.py','docs/archive/PERPETUAL_HOLD_FINANCIAL_INDEPENDENT_SOURCE_20261003_V1.py','scripts/investment/compare_perpetual_hold_results.py','docs/archive/PERPETUAL_HOLD_COMPARISON_SOURCE_20261003_V1.py','docs/archive/PERPETUAL_HOLD_ACCEPTANCE_FREEZER_20261003_V1.ps1','docs/archive/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDITOR_20261003_V1.py','docs/archive/PERPETUAL_213_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py','docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py','scripts/investment/compare_perpetual_213_results.py','reports/fast_research/LONG_SHORT_USDM_INPUT_BINDING_20261003_V1.json','reports/fast_research/PERPETUAL_TRADE_SOURCE_ROOT_ACCEPTANCE_20261003_V4.json')){$hashes[$p]=Digest $p}
$qa='reports/fast_research/PERPETUAL_CONSTANT_LONG_REFERENCE_INDEPENDENT_20261003_V1.json'
if($Phase -eq 'Financial'){
 $reuse=ReadJson 'reports/fast_research/PERPETUAL_HOLD_SOURCE_REUSE_20261003_V1.json'
 $parents=@{213D=$reuse.original_input_manifests.'213D'.manifest;122D=$reuse.original_input_manifests.'122D90D'.manifest;90D=$reuse.original_input_manifests.'122D90D'.manifest}
 $receipts=@($reuse.original_input_manifests.'213D'.root,$reuse.original_input_manifests.'122D90D'.root)
 $newrun='/home/xflops/coin-state/d044-constant-long-financial-independent-20261003-v1'
 $plan=[ordered]@{ready_to_execute=$true;checker_sha256=(Digest 'scripts/investment/audit_perpetual_hold_research.py');protocol_path=$proto;protocol_sha256=(Digest $proto);actual_report=$marketPath;actual_report_sha256=(Digest $marketPath);actual_task_id=$market.binding.task_id;source_hashes=$hashes;tolerances=@{cash_USDT=0.0000001;ratio=0.0000000001};budgets=@{peak_RSS_bytes=3000000000;wall_seconds=3600;new_owned_bytes=5000000};original_input_manifests=$parents;accepted_source_receipts=$receipts;created_utc=[datetime]::UtcNow.ToString('o')}
 $dest='protocols/PERPETUAL_HOLD_FINANCIAL_INDEPENDENT_BINDING_20261003_V1.json';WriteNew $dest $plan
 & wsl.exe -d hpc_linux -- bash /mnt/d/codex/coin/scripts/bounded.sh mkdir -- $newrun
 if($LASTEXITCODE -ne 0){throw 'Exclusive financial STATE'}
 & wsl.exe -d hpc_linux -- bash /mnt/d/codex/coin/scripts/bounded.sh cp -- ('/mnt/d/codex/coin/'+$dest) ($newrun+'/ACTUAL_BINDING.json')
 if($LASTEXITCODE -ne 0){throw 'Exact financial binding copy'}
}else{
 $audit=ReadJson $qa
 $auditStatus='PASS_D044_TWELVE_CONSTANT_LONG_PERPETUAL_ACCOUNTS_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR'
 if($audit.status -ne $auditStatus -or $audit.completed_cases_verified -ne 12){throw 'Twelve independent cases required'}
 foreach($p in @($qa,'protocols/PERPETUAL_HOLD_FINANCIAL_INDEPENDENT_BINDING_20261003_V1.json')){$hashes[$p]=Digest $p}
 $roles=[ordered]@{MARKET=@{path=$marketPath;sha256=(Digest $marketPath);required_status=$market.status;task_id=$market.binding.task_id};INDEPENDENT=@{path=$qa;sha256=(Digest $qa);required_status=$audit.status;task_id=$audit.binding.task_id}}
 $plan=[ordered]@{ready_to_execute=$true;contract_id='D044_ALWAYS_LONG_THREE_PERIOD_SAVED_COMPARISON_V1';helper_sha256=(Digest 'scripts/investment/compare_perpetual_hold_results.py');frozen_sources=$hashes;market_protocol=@{path=$proto;sha256=(Digest $proto)};hold_strategy_id='COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE';roles=$roles;budgets=@{new_owned_bytes=5000000;peak_RSS_bytes=1000000000;wall_seconds=120};run_dir='/home/xflops/coin-state/d044-perpetual-hold-comparison-20261003-v1';output_path='reports/fast_research/PERPETUAL_HOLD_ECONOMIC_COMPARISON_20261003_V1.json';created_utc=[datetime]::UtcNow.ToString('o')}
 $dest='protocols/PERPETUAL_HOLD_COMPARISON_BINDING_20261003_V1.json';WriteNew $dest $plan
}
[pscustomobject]@{phase=$Phase;path=$dest;sha256=(Digest $dest)}|ConvertTo-Json
