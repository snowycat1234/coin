$ErrorActionPreference='Stop';$root='D:/codex/coin';$utf=[Text.UTF8Encoding]::new($false)
function Digest([string]$p){(Get-FileHash -LiteralPath (Join-Path $root $p) -Algorithm SHA256).Hash.ToLowerInvariant()}
function ReadJson([string]$p){Get-Content (Join-Path $root $p) -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
$proto='protocols/PERPETUAL_RISK_REDUCTION_RESEARCH_20261003_V2.json';$spec=ReadJson $proto
$actual='reports/fast_research/PERPETUAL_RISK_REDUCTION_RESEARCH_ACTUAL_20261003_V2.json';$v=ReadJson $actual
if($v.status -ne 'COMPLETE_D046_FOUR_FIXED303D_LONG_SHORT_RISK_REDUCTION_CONTROLS_NOT_NATIVE_OR_LONG_TERM_APR'){throw 'New actual not complete execution'}
$old=ReadJson 'protocols/PERPETUAL_303_FINANCIAL_INDEPENDENT_BINDING_20261003_V1.json';$hashes=[ordered]@{}
foreach($p in $spec.frozen_sources.Keys){$hashes[$p]=$spec.frozen_sources[$p]}
$deps=@('docs/archive/PERPETUAL_303_FINANCIAL_INDEPENDENT_AUDITOR_20261003_V1.py',
 'docs/archive/PERPETUAL_213_FINANCIAL_INDEPENDENT_AUDITOR_20261003_V3.py',
 'docs/archive/PERPETUAL_303_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py',
 'docs/archive/PERPETUAL_213_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py',
 'scripts/investment/audit_perpetual_hold_research_v3.py',
 'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py')
$oldloader=[IO.File]::ReadAllText((Join-Path $root 'docs/archive/PERPETUAL_213_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py'))
foreach($key in @('FINANCE','HAND')){if($oldloader -notmatch ($key+"='([^']+)'")){throw 'Exact original finance/hand path'};$deps+=$Matches[1]}
foreach($p in $deps){$h=Digest $p;if($old.source_hashes[$p] -ne $h){throw "Original financial source $p"};$hashes[$p]=$h}
foreach($p in @($proto,$actual,'scripts/investment/audit_perpetual_risk_reduction.py','docs/archive/PERPETUAL_RISK_REDUCTION_FINANCIAL_AUDITOR_SOURCE_20261003_V1.py','docs/archive/PERPETUAL_RISK_REDUCTION_FINANCIAL_COMPILE_SOURCE_20261003_V1.py','reports/fast_research/PERPETUAL_RISK_REDUCTION_FINANCIAL_COMPILE_20261003_V1.json','docs/archive/PERPETUAL_RISK_REDUCTION_FINANCIAL_FREEZER_20261003_V1.ps1')){$hashes[$p]=Digest $p}
foreach($p in $hashes.Keys){if((Digest $p) -ne $hashes[$p]){throw "Exact binding $p"}}
$p='protocols/PERPETUAL_RISK_REDUCTION_FINANCIAL_BINDING_20261003_V1.json'
$plan=[ordered]@{ready_to_execute=$true;checker_sha256=(Digest 'scripts/investment/audit_perpetual_risk_reduction.py');source_hashes=$hashes;protocol_path=$proto;protocol_sha256=(Digest $proto);actual_report=$actual;actual_report_sha256=(Digest $actual);actual_task_id=$v.binding.task_id;tolerances=@{cash_USDT=1e-7;ratio=1e-10};budgets=@{peak_RSS_bytes=3000000000;wall_seconds=3600;new_owned_bytes=5000000};created_utc=[datetime]::UtcNow.ToString('o')}
if(Test-Path -LiteralPath (Join-Path $root $p)){throw 'Exclusive financial plan'}
[IO.File]::WriteAllText((Join-Path $root $p),($plan|ConvertTo-Json -Depth 40)+"`n",$utf)
wsl -d hpc_linux -- bash /mnt/d/codex/coin/scripts/bounded.sh -- mkdir /home/xflops/coin-state/d046-perpetual-risk-reduction-financial-independent-20261003-v1
if($LASTEXITCODE -ne 0){throw 'Exclusive financial STATE'}
wsl -d hpc_linux -- bash /mnt/d/codex/coin/scripts/bounded.sh -- cp -n /mnt/d/codex/coin/protocols/PERPETUAL_RISK_REDUCTION_FINANCIAL_BINDING_20261003_V1.json /home/xflops/coin-state/d046-perpetual-risk-reduction-financial-independent-20261003-v1/ACTUAL_BINDING.json
if($LASTEXITCODE -ne 0){throw 'Actual manifest copy'}
@{status='FROZEN_D046_FOUR_ACCOUNT_FINANCIAL_MANIFEST_NOT_RUN';path=$p;sha256=(Digest $p);direct_pins=$hashes.Count}|ConvertTo-Json
