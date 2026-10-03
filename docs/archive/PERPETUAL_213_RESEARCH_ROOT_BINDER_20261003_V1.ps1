$ErrorActionPreference='Stop';$root='D:/codex/coin';$enc=[Text.UTF8Encoding]::new($false)
function Digest([string]$p){(Get-FileHash -LiteralPath (Join-Path $root $p) -Algorithm SHA256).Hash.ToLowerInvariant()}
function ReadJson([string]$p){Get-Content (Join-Path $root $p) -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
$hashes=[ordered]@{}
$finance=ReadJson 'protocols/PERPETUAL_213_FINANCIAL_INDEPENDENT_BINDING_20261003_V3.json'
foreach($p in $finance.source_hashes.Keys){if((Digest $p) -ne $finance.source_hashes[$p]){throw "Frozen source $p"};$hashes[$p]=$finance.source_hashes[$p]}
$names=@('scripts/investment/accept_perpetual_213_research.py','docs/archive/PERPETUAL_213_RESEARCH_ROOT_ACCEPTANCE_SOURCE_20261003_V1.py','docs/archive/PERPETUAL_213_SOURCE_ROOT_ACCEPTANCE_SOURCE_20261003_V1.py','docs/archive/PERPETUAL_213_RESEARCH_ROOT_BINDER_20261003_V1.ps1','docs/archive/PERPETUAL_213_SCAN_AND_FAILURE_METADATA_SOURCE_20261003_V1.py','reports/fast_research/PERPETUAL_213_METADATA_FAILURES_AND_SCAN_20261003_V1.json','scripts/investment/audit_perpetual_213_research.py','scripts/investment/audit_perpetual_213_research_v2.py','docs/archive/PERPETUAL_213_FINANCIAL_INDEPENDENT_AUDITOR_20261003_V1.py','docs/archive/PERPETUAL_213_FINANCIAL_INDEPENDENT_AUDITOR_20261003_V2.py','docs/archive/PERPETUAL_213_FINANCIAL_ACCEPTANCE_FREEZER_20261003_V1.ps1','docs/archive/PERPETUAL_213_FINANCIAL_ACCEPTANCE_FREEZER_20261003_V2.ps1','docs/archive/PERPETUAL_213_RESEARCH_PROTOCOL_FREEZER_20261003_V1.py','protocols/PERPETUAL_213_FINANCIAL_INDEPENDENT_BINDING_20261003_V1.json','protocols/PERPETUAL_213_FINANCIAL_INDEPENDENT_BINDING_20261003_V2.json','protocols/PERPETUAL_213_FINANCIAL_INDEPENDENT_BINDING_20261003_V3.json','protocols/PERPETUAL_213_ECONOMIC_COMPARISON_BINDING_20261003_V1.json','reports/GITHUB_PERPETUAL_HISTORY_GAP_SYNC_VERIFIED_20261003_V1.json')
$roles=[ordered]@{}
$definitions=@(
 @('SOURCE','PERPETUAL_213_SOURCE_ACTUAL_20261003_V1.json','PASS_D043_72_HISTORY_FORMAT_PENDING_FULL_INDEPENDENT_QA',0),
 @('SOURCE_QA','PERPETUAL_213_SOURCE_INDEPENDENT_20261003_V1.json','PASS_D043_72_MIXED_OWNER_213D_USDM_FORMAT_CALENDAR_ONLY_NOT_UNIT_OR_ECONOMICS',0),
 @('SOURCE_ROOT','PERPETUAL_213_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json','PASS_ROOT_D043_COMPLETE_213_USDM_SOURCE_NOT_UNIT_OR_ECONOMICS',0),
 @('SMOKE','PERPETUAL_213_WIRING_SMOKE_20261003_V1.json','PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT',0),
 @('MARKET','PERPETUAL_213_RESEARCH_ACTUAL_20261003_V1.json','COMPLETE_D043_FIXED213D_PUBLIC_PERPETUAL_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR',0),
 @('FINANCIAL','PERPETUAL_213_RESEARCH_INDEPENDENT_20261003_V3.json','PASS_D043_TWENTY_FIXED213D_PUBLIC_PERPETUAL_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR',0),
 @('COMPARISON','PERPETUAL_213_ECONOMIC_COMPARISON_20261003_V1.json','COMPLETE_D043_213D_SAVED_SUMMARY_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR',0),
 @('FINANCIAL_V1_FAILURE','PERPETUAL_213_RESEARCH_INDEPENDENT_20261003_V1.json','FAIL_D043_FIXED213D_PUBLIC_PERPETUAL_INDEPENDENT_AUDIT',1),
 @('FULL547_FAILURE','PERPETUAL_HISTORY_SOURCE_ACTUAL_20261003_V1.json','FAIL_D042_HISTORY_SOURCE',1))
foreach($row in $definitions){$p='reports/fast_research/'+$row[1];$v=ReadJson $p;if($v.status -ne $row[2]){throw "Role status $($row[0])"};$roles[$row[0]]=@{path=$p;sha256=(Digest $p);task_id=$v.binding.task_id;status=$row[2];exit_code=$row[3]};$names+=$p}
foreach($p in $names){$hashes[$p]=Digest $p}
$fail=ReadJson 'reports/fast_research/PERPETUAL_213_METADATA_FAILURES_AND_SCAN_20261003_V1.json'
foreach($id in $fail.failures.Keys){$item=$fail.failures[$id];if((Digest $item.path) -ne $item.sha256){throw 'Failure task bytes'};$hashes[$item.path]=$item.sha256}
$prior='reports/GITHUB_PERPETUAL_HISTORY_GAP_SOURCE_BINDING_20261003_V1.json'
$plan=[ordered]@{ready_to_execute=$true;run_dir='/home/xflops/coin-state/d043-perpetual-213-root-acceptance-20261003-v1';source_hashes=$hashes;roles=$roles;separate_metadata_failures=@{RESEARCH_FREEZER_V1='86718b12e56746c89a1a54837a386caa';FINANCIAL_STARTUP_V2='5432665f8631476f8147ba6b38353856'};prior_portable=@{path=$prior;sha256=(Digest $prior)};created_utc=[datetime]::UtcNow.ToString('o')}
$dest='protocols/PERPETUAL_213_RESEARCH_ROOT_BINDING_20261003_V1.json';if(Test-Path $dest){throw 'Exclusive root protocol exists'}
[IO.File]::WriteAllText((Join-Path $root $dest),($plan|ConvertTo-Json -Depth 40)+"`n",$enc)
[pscustomobject]@{path=$dest;sha256=(Digest $dest)}|ConvertTo-Json
