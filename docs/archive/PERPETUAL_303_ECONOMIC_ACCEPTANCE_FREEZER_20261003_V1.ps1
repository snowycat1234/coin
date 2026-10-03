param([ValidateSet('Financial','Comparison')][string]$Phase)
$ErrorActionPreference='Stop';$root='D:/codex/coin';$enc=[Text.UTF8Encoding]::new($false)
function Digest([string]$p){(Get-FileHash -LiteralPath (Join-Path $root $p) -Algorithm SHA256).Hash.ToLowerInvariant()}
function ReadJson([string]$p){Get-Content (Join-Path $root $p) -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
function WriteNew([string]$p,$v){$d=Join-Path $root $p;if(Test-Path -LiteralPath $d){throw "Exclusive $p"};[IO.File]::WriteAllText($d,($v|ConvertTo-Json -Depth 50)+"`n",$enc)}
function Ref([string]$p){$v=ReadJson $p;return @{path=$p;sha256=(Digest $p);task_id=$v.binding.task_id;required_status=$v.status}}
$proto='protocols/PERPETUAL_303_RESEARCH_20261003_V1.json';$spec=ReadJson $proto
$actual='reports/fast_research/PERPETUAL_303_RESEARCH_ACTUAL_20261003_V1.json';$m=ReadJson $actual
if($m.status -ne 'COMPLETE_D045_FIXED303D_PERPETUAL_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR' -or $m.completed_cases -ne 20){throw 'Actual twenty not complete'}
$hashes=[ordered]@{};foreach($p in $spec.frozen_sources.Keys){if((Digest $p) -ne $spec.frozen_sources[$p]){throw "Frozen source $p"};$hashes[$p]=$spec.frozen_sources[$p]}
foreach($p in @($proto,$actual,'scripts/investment/audit_perpetual_303_research.py','docs/archive/PERPETUAL_303_FINANCIAL_INDEPENDENT_AUDITOR_20261003_V1.py','docs/archive/PERPETUAL_213_FINANCIAL_INDEPENDENT_AUDITOR_20261003_V3.py','scripts/investment/audit_perpetual_hold_research_v3.py','docs/archive/PERPETUAL_303_ECONOMIC_ACCEPTANCE_FREEZER_20261003_V1.ps1','docs/archive/PERPETUAL_303_FINANCIAL_CONTEXT_COMPILE_SOURCE_20261003_V1.py','reports/fast_research/PERPETUAL_303_FINANCIAL_CONTEXT_COMPILE_20261003_V1.json','docs/archive/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDITOR_20261003_V1.py','docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py')){$hashes[$p]=Digest $p}
$finance='reports/fast_research/PERPETUAL_303_RESEARCH_INDEPENDENT_20261003_V1.json'
if($Phase -eq 'Financial'){
 $run='/home/xflops/coin-state/d045-perpetual-303-financial-independent-20261003-v1';$runner='scripts/investment/audit_perpetual_303_research.py'
 $plan=[ordered]@{ready_to_execute=$true;checker_sha256=(Digest $runner);protocol_path=$proto;protocol_sha256=(Digest $proto);actual_report=$actual;actual_report_sha256=(Digest $actual);actual_task_id=$m.binding.task_id;source_hashes=$hashes;tolerances=@{cash_USDT=0.0000001;ratio=0.0000000001};budgets=@{peak_RSS_bytes=3000000000;wall_seconds=3600;new_owned_bytes=5000000};created_utc=[datetime]::UtcNow.ToString('o')}
 $dest='protocols/PERPETUAL_303_FINANCIAL_INDEPENDENT_BINDING_20261003_V1.json';WriteNew $dest $plan
 & wsl.exe -d hpc_linux -- bash /mnt/d/codex/coin/scripts/bounded.sh mkdir -- $run
 if($LASTEXITCODE -ne 0){throw 'Exclusive financial STATE'}
 & wsl.exe -d hpc_linux -- bash /mnt/d/codex/coin/scripts/bounded.sh cp -- ('/mnt/d/codex/coin/'+$dest) ($run+'/ACTUAL_BINDING.json')
 if($LASTEXITCODE -ne 0){throw 'Financial binding copy'}
}else{
 $f=ReadJson $finance;if($f.status -ne 'PASS_D045_TWENTY_FIXED303D_SMA_HOLD_PERPETUAL_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR' -or $f.completed_cases_verified -ne 20){throw 'Independent twenty not accepted'}
 foreach($p in @($finance,'protocols/PERPETUAL_303_FINANCIAL_INDEPENDENT_BINDING_20261003_V1.json','scripts/investment/compare_perpetual_303_results.py','docs/archive/PERPETUAL_303_ECONOMIC_COMPARISON_SOURCE_20261003_V1.py','scripts/investment/compare_perpetual_213_results.py','reports/fast_research/PERPETUAL_HOLD_ECONOMIC_COMPARISON_20261003_V1.json','reports/fast_research/PERPETUAL_HOLD_ROOT_ACCEPTANCE_20261003_V2.json')){$hashes[$p]=Digest $p}
 $plan=[ordered]@{ready_to_execute=$true;contract_id='D045_FIXED_303D_SAVED_SUMMARY_COMPARISON_V1';helper_sha256=(Digest 'scripts/investment/compare_perpetual_303_results.py');frozen_sources=$hashes;market_protocol=@{path=$proto;sha256=(Digest $proto)};roles=[ordered]@{MARKET=(Ref $actual);FINANCE=(Ref $finance)};budgets=@{new_owned_bytes=5000000;peak_RSS_bytes=1000000000;wall_seconds=120};run_dir='/home/xflops/coin-state/d045-perpetual-303-economic-comparison-20261003-v1';output_path='reports/fast_research/PERPETUAL_303_ECONOMIC_COMPARISON_20261003_V1.json';created_utc=[datetime]::UtcNow.ToString('o')}
 $dest='protocols/PERPETUAL_303_ECONOMIC_COMPARISON_BINDING_20261003_V1.json';WriteNew $dest $plan
}
[pscustomobject]@{phase=$Phase;path=$dest;sha256=(Digest $dest)}|ConvertTo-Json
