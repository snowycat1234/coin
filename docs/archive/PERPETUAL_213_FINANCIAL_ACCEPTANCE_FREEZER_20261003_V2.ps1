param([ValidateSet('Financial','Comparison')][string]$Phase)
$ErrorActionPreference='Stop'
$root='D:/codex/coin';$enc=[Text.UTF8Encoding]::new($false)
function Digest([string]$Name) { (Get-FileHash -LiteralPath (Join-Path $root $Name) -Algorithm SHA256).Hash.ToLowerInvariant() }
function ReadJson([string]$Name) { Get-Content (Join-Path $root $Name) -Raw | ConvertFrom-Json -AsHashtable -DateKind String }
function WriteNew([string]$Name,$Value) { $p=Join-Path $root $Name;if(Test-Path -LiteralPath $p) { throw "Exclusive path exists: $Name" };[IO.File]::WriteAllText($p,($Value|ConvertTo-Json -Depth 50)+"`n",$enc) }
$proto='protocols/PERPETUAL_213_RESEARCH_20261003_V1.json';$spec=ReadJson $proto
$marketPath='reports/fast_research/PERPETUAL_213_RESEARCH_ACTUAL_20261003_V1.json';$market=ReadJson $marketPath
if($market.status -ne 'COMPLETE_D043_FIXED213D_PUBLIC_PERPETUAL_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR' -or $market.completed_cases -ne 20) { throw 'Twenty selector actual not fully passed' }
$hashes=[ordered]@{}
foreach($p in $spec.frozen_sources.Keys) { if((Digest $p) -ne $spec.frozen_sources[$p]) { throw "Frozen dependency changed: $p" };$hashes[$p]=$spec.frozen_sources[$p] }
foreach($p in @($proto,$marketPath,'scripts/investment/audit_perpetual_213_research_v2.py','docs/archive/PERPETUAL_213_FINANCIAL_INDEPENDENT_AUDITOR_20261003_V2.py','scripts/investment/compare_perpetual_213_results.py','docs/archive/PERPETUAL_213_ECONOMIC_COMPARISON_SOURCE_20261003_V1.py','docs/archive/PERPETUAL_213_FINANCIAL_ACCEPTANCE_FREEZER_20261003_V2.ps1','docs/archive/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDITOR_20261003_V1.py','docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py','scripts/investment/audit_perpetual_public_benchmark.py','docs/archive/PUBLIC_DONCHIAN_DAILY_INDEPENDENT_TARGET_SOURCE_20261003_V1.py')) { $hashes[$p]=Digest $p }
$qa='reports/fast_research/PERPETUAL_213_RESEARCH_INDEPENDENT_20261003_V2.json'
if($Phase -eq 'Financial') {
  $newrun='/home/xflops/coin-state/d043-perpetual-213-financial-independent-20261003-v2'
  $runner='scripts/investment/audit_perpetual_213_research_v2.py'
  $plan=[ordered]@{ready_to_execute=$true;checker_sha256=(Digest $runner);protocol_path=$proto;protocol_sha256=(Digest $proto);actual_report=$marketPath;actual_report_sha256=(Digest $marketPath);actual_task_id=$market.binding.task_id;source_hashes=$hashes;tolerances=@{cash_USDT=0.0000001;ratio=0.0000000001};budgets=@{peak_RSS_bytes=3000000000;wall_seconds=3600;new_owned_bytes=5000000};created_utc=[datetime]::UtcNow.ToString('o')}
  $dest='protocols/PERPETUAL_213_FINANCIAL_INDEPENDENT_BINDING_20261003_V2.json';WriteNew $dest $plan
  & wsl.exe -d hpc_linux -- bash /mnt/d/codex/coin/scripts/bounded.sh mkdir -- $newrun
  if($LASTEXITCODE -ne 0) { throw 'Exclusive financial audit STATE failed' }
  & wsl.exe -d hpc_linux -- bash /mnt/d/codex/coin/scripts/bounded.sh cp -- (('/mnt/d/codex/coin/'+$dest)) ($newrun+'/ACTUAL_BINDING.json')
  if($LASTEXITCODE -ne 0) { throw 'Exact financial binding copy failed' }
} else {
  $audit=ReadJson $qa
  if($audit.status -ne 'PASS_D043_TWENTY_FIXED213D_PUBLIC_PERPETUAL_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR' -or $audit.completed_cases_verified -ne 20) { throw 'Twenty financial independent not passed' }
  foreach($p in @($qa,'protocols/PERPETUAL_213_FINANCIAL_INDEPENDENT_BINDING_20261003_V2.json')) { $hashes[$p]=Digest $p }
  $roles=[ordered]@{}
  foreach($r in @(@('SOURCE_INDEPENDENT','reports/fast_research/PERPETUAL_213_SOURCE_INDEPENDENT_20261003_V1.json','PASS_D043_72_MIXED_OWNER_213D_USDM_FORMAT_CALENDAR_ONLY_NOT_UNIT_OR_ECONOMICS'),@('MARKET',$marketPath,'COMPLETE_D043_FIXED213D_PUBLIC_PERPETUAL_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR'),@('INDEPENDENT',$qa,'PASS_D043_TWENTY_FIXED213D_PUBLIC_PERPETUAL_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR'))) {
    $v=ReadJson $r[1];if($v.status -ne $r[2]) { throw "Wrong status role $($r[0])" };$roles[$r[0]]=@{path=$r[1];sha256=(Digest $r[1]);task_id=$v.binding.task_id;required_status=$r[2]}
  }
  $plan=[ordered]@{ready_to_execute=$true;contract_id='D043_FIXED_213D_SAVED_SUMMARY_ECONOMIC_COMPARISON_V1';helper_sha256=(Digest 'scripts/investment/compare_perpetual_213_results.py');frozen_sources=$hashes;market_protocol=@{path=$proto;sha256=(Digest $proto)};roles=$roles;budgets=@{new_owned_bytes=5000000;peak_RSS_bytes=1000000000;wall_seconds=120};run_dir='/home/xflops/coin-state/d043-perpetual-213-economic-comparison-20261003-v1';output_path='reports/fast_research/PERPETUAL_213_ECONOMIC_COMPARISON_20261003_V1.json';created_utc=[datetime]::UtcNow.ToString('o')}
  $dest='protocols/PERPETUAL_213_ECONOMIC_COMPARISON_BINDING_20261003_V1.json';WriteNew $dest $plan
}
[pscustomobject]@{phase=$Phase;path=$dest;sha256=(Digest $dest)}|ConvertTo-Json
