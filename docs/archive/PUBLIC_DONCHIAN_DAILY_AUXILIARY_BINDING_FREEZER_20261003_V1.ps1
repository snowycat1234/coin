$ErrorActionPreference='Stop'
Set-Location 'D:/codex/coin'
$archive='docs/archive/PUBLIC_DONCHIAN_DAILY_AUXILIARY_BINDING_FREEZER_20261003_V1.ps1'
if(Test-Path -LiteralPath $archive){throw 'Exclusive archive'}
[IO.File]::WriteAllBytes((Join-Path (Get-Location) $archive),[IO.File]::ReadAllBytes($PSCommandPath))
$hashes=[ordered]@{}
$files=@(git ls-files --others --exclude-standard)
$selected=@($files|Where-Object {$_ -match '^(docs/archive|protocols|reports/fast_research)/(PUBLIC_DAILY_|PUBLIC_DONCHIAN_DAILY_)' -or $_ -match '^reports/GITHUB_PUBLIC_DONCHIAN_DAILY_' -or $_ -match '^scripts/investment/(public_daily_official_source|public_donchian_daily|audit_public_daily_ledgers)' -or $_ -eq 'tests/test_public_donchian_daily.py'})
$selected+=@('reports/GITHUB_PUBLIC_PAIR_COMPLEMENTARITY_SYNC_VERIFIED_20261003_V1.json')
foreach($name in @($selected|Sort-Object -Unique)){if((Get-Item -LiteralPath $name).Length -gt 4000000){throw 'No oversized Git artifact'};$hashes[$name]=(Get-FileHash -LiteralPath $name -Algorithm SHA256).Hash.ToLowerInvariant()}
$independent=Get-Content reports/fast_research/PUBLIC_DONCHIAN_DAILY_INDEPENDENT_ACTUAL_EXIT_20261003_V1.json -Raw|ConvertFrom-Json -AsHashtable
foreach($name in $independent.source_hashes.Keys){$value=$independent.source_hashes[$name];if((Get-FileHash -LiteralPath $name).Hash.ToLowerInvariant() -ne $value){throw 'Exact independent source changed'};if($hashes.Contains($name) -and $hashes[$name] -ne $value){throw 'Conflicting supplemental source'};$hashes[$name]=$value}
$value=[ordered]@{status='PASS_D037_AUXILIARY_EXACT_BYTES_FOR_STANDARD_STAGED_GATE_NOT_NEW_SCIENCE';source_hashes=$hashes;data_venue='Binance';fee_venue='BybitVIP0Spot';private_runtime_payload_archived=$false;scientific_acceptance='reports/fast_research/PUBLIC_DONCHIAN_DAILY_ROOT_ACCEPTANCE_20261003_V2.json';frozen_failures_and_unrun_helper_versions_preserved=$true;old_financial_QA_replayed=$false;models_fit=0;orders_sent=0;locked_consumed=$false;root_task_final_closed0_later_verified=$true;candidate_status='NO_QUALIFIED_CANDIDATE';long_term_APR='NOT_EVALUABLE'}
$out='reports/GITHUB_PUBLIC_DONCHIAN_DAILY_AUXILIARY_SOURCE_BINDING_20261003_V1.json';if(Test-Path -LiteralPath $out){throw 'Exclusive receipt'}
[IO.File]::WriteAllText((Join-Path (Get-Location) $out),($value|ConvertTo-Json -Depth 7)+"`n",[Text.UTF8Encoding]::new($false))
[ordered]@{status=$value.status;frozen_files=$hashes.Count;sha256=(Get-FileHash -LiteralPath $out).Hash.ToLowerInvariant()}|ConvertTo-Json -Compress
