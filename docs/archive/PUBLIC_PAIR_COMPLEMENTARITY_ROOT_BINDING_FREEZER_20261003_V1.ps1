$ErrorActionPreference='Stop'
$rootPath='D:\codex\coin'
function RootFileHash([string]$n){(Get-FileHash -LiteralPath (Join-Path $rootPath $n) -Algorithm SHA256).Hash.ToLowerInvariant()}
function RootSmallJson([string]$n){Get-Content -LiteralPath (Join-Path $rootPath $n) -Raw | ConvertFrom-Json}
function LinuxMetaHash([string]$n){if(-not $n.StartsWith('/home/xflops/coin-state/')){throw 'Only D-hosted STATE metadata'};$p='\\wsl.localhost\hpc_linux'+$n.Replace('/','\');(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
$archive='docs/archive/PUBLIC_PAIR_COMPLEMENTARITY_ROOT_CLOSE_SOURCE_20261003_V1.py'
if((RootFileHash $archive) -ne 'd1cdb3c008de657ad8877a83ae1e56195a19b624e1e6b1d4240d9b61be107b10'){throw 'Held ROOT code changed'}
$roles=[ordered]@{}
foreach($item in @(
 [ordered]@{role='DIAGNOSTIC';report='reports/fast_research/PUBLIC_PAIR_COMPLEMENTARITY_ACTUAL_20261003_V2.json';run='/home/xflops/coin-state/d036-public-pair-diagnostics-20261003-v2';source='scripts/investment/public_pair_diagnostics_v2.py';status='COMPLETE_D036_SAVED_PUBLIC_PAIR_COMPLEMENTARITY_DIAGNOSTIC_NOT_ENSEMBLE_OR_LONG_TERM_APR'},
 [ordered]@{role='INDEPENDENT';report='reports/fast_research/PUBLIC_PAIR_COMPLEMENTARITY_INDEPENDENT_AUDIT_20261003_V1.json';run='/home/xflops/coin-state/d036-public-pair-independent-20261003-v1';source='docs/archive/PUBLIC_PAIR_COMPLEMENTARITY_INDEPENDENT_SOURCE_20261003_V1.py';status='PASS_D036_SAVED_PUBLIC_PAIR_STATISTICS_AND_SOURCE_BINDINGS_NOT_ENSEMBLE_OR_APR'}
)){
 $r=RootSmallJson $item.report
 if($r.status -ne $item.status){throw 'Exact completed scientific status'}
 $rb=$item.run+'/RUN_BINDING.json';$sha=LinuxMetaHash $rb
 if($sha -ne $r.run_binding_sha256){throw 'Actual RB changed'}
 $roles[$item.role]=[ordered]@{report=$item.report;report_sha256=RootFileHash $item.report;required_status=$item.status;expected_task_id=$r.binding.task_id;run_binding=$rb;run_binding_sha256=$sha;source=[ordered]@{path=$item.source;sha256=RootFileHash $item.source}}
}
$files=@('docs/archive/PUBLIC_PAIR_DIAGNOSTICS_PROTOCOL_FREEZER_20261003_V1.ps1','docs/archive/PUBLIC_PAIR_DIAGNOSTICS_PROTOCOL_FREEZER_20261003_V2.ps1','docs/archive/PUBLIC_PAIR_DIAGNOSTICS_PROTOCOL_FREEZER_20261003_V3.ps1','docs/archive/PUBLIC_PAIR_DIAGNOSTICS_FREEZER_FAILURE_20261003_V1.json','docs/archive/PUBLIC_PAIR_DIAGNOSTICS_ACTUAL_STARTUP_FAILURE_20261003_V1.json','docs/archive/PUBLIC_PAIR_COMPLEMENTARITY_PROTOCOL_DISPLAY_ERRATUM_20261003_V1.json','docs/archive/PUBLIC_PAIR_COMPLEMENTARITY_ROOT_BINDING_FREEZER_20261003_V1.ps1','reports/GITHUB_VOL_MANAGED_HOLD_TWO_PERIOD_SYNC_VERIFIED_20261003_V1.json')
$failure='docs/archive/PUBLIC_PAIR_DIAGNOSTICS_ACTUAL_STARTUP_FAILURE_20261003_V1.json';$f=RootSmallJson $failure
$p='protocols/PUBLIC_PAIR_COMPLEMENTARITY_20261003_V2.json'
$plan=[ordered]@{classification='CLOSED_D036_SMALL_METADATA_BINDING_NO_LEDGER_REPLAY';ready_to_execute=$true;created_utc=[DateTime]::UtcNow.ToString('o');helper_sha256=RootFileHash $archive;protocol=[ordered]@{path=$p;sha256=RootFileHash $p};roles=$roles;owned_STATE_directories=@('/home/xflops/coin-state/d036-public-pair-diagnostics-20261003-v2','/home/xflops/coin-state/d036-public-pair-independent-20261003-v1');project_files=@($files|ForEach-Object{[ordered]@{path=$_;sha256=RootFileHash $_}});preserved_failures=[ordered]@{STARTUP_V1=[ordered]@{report=$failure;report_sha256=RootFileHash $failure;required_status=$f.status;expected_task_id=$f.task_id;required_exit_code=1}};display_erratum_reference='docs/archive/PUBLIC_PAIR_COMPLEMENTARITY_PROTOCOL_DISPLAY_ERRATUM_20261003_V1.json'}
$out='protocols/PUBLIC_PAIR_COMPLEMENTARITY_ROOT_CLOSE_BINDING_20261003_V1.json';$target=Join-Path $rootPath $out;if(Test-Path -LiteralPath $target){throw 'Exclusive new ROOT binding'};[IO.File]::WriteAllText($target,(($plan|ConvertTo-Json -Depth 30)+"`n"),[Text.UTF8Encoding]::new($false))
[pscustomobject]@{path=$out;sha256=RootFileHash $out;completed_scientific_roles=2;arrays_read=$false}|ConvertTo-Json -Compress
