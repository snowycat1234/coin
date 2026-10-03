$ErrorActionPreference='Stop'
$root='D:/codex/coin'
$enc=[Text.UTF8Encoding]::new($false)
function Digest([string]$Name) { (Get-FileHash -LiteralPath (Join-Path $root $Name) -Algorithm SHA256).Hash.ToLowerInvariant() }
$old=Get-Content (Join-Path $root 'protocols/PERPETUAL_HISTORY_SOURCE_20261003_V1.json') -Raw | ConvertFrom-Json -AsHashtable -DateKind String
$hashes=[ordered]@{}
foreach($name in $old.frozen_sources.Keys) { if((Digest $name) -ne $old.frozen_sources[$name]) { throw "Frozen dependency changed: $name" }; $hashes[$name]=$old.frozen_sources[$name] }
$runner='scripts/investment/perpetual_213_source.py'
foreach($name in @($runner,'docs/archive/PERPETUAL_213_SOURCE_PRODUCER_SOURCE_20261003_V1.py','scripts/investment/accept_perpetual_213_source.py','docs/archive/PERPETUAL_213_SOURCE_PROTOCOL_FREEZER_20261003_V1.ps1','reports/fast_research/PERPETUAL_HISTORY_SOURCE_ACTUAL_20261003_V1.json','reports/fast_research/PERPETUAL_HISTORY_METADATA_ACTUAL_20261003_V1.json','protocols/PERPETUAL_HISTORY_SOURCE_20261003_V1.json')) { $hashes[$name]=Digest $name }
$entries=@($old.entries | Where-Object { $_.month -le '2024-07' })
if($entries.Count -ne 72) { throw 'Exactly72 explicit source objects' }
$spec=[ordered]@{}
foreach($k in $old.Keys) { $spec[$k]=$old[$k] }
$spec.contract_id='D043_FIXED_213D_MIXED_OWNER_OFFICIAL_SOURCE_V1'
$spec.entries=$entries; $spec.frozen_sources=$hashes
$spec.required_files=72; $spec.expected_reused_files=51; $spec.expected_new_files=21
$spec.score_period_start='2024-01-01'; $spec.score_period_end_exclusive='2024-08-01'; $spec.score_days=213; $spec.score_minutes_per_symbol=306720
$spec.parent_source_path='reports/fast_research/PERPETUAL_HISTORY_SOURCE_ACTUAL_20261003_V1.json'
$spec.parent_source_sha256=Digest $spec.parent_source_path
$spec.run_dir='/home/xflops/coin-state/d043-perpetual-213-source-20261003-v1'
$spec.source_owner_paths=@('/home/xflops/coin-state/d042-perpetual-history-source-20261003-v1',$spec.run_dir)
$spec.output_path='reports/fast_research/PERPETUAL_213_SOURCE_ACTUAL_20261003_V1.json'
$spec.new_archives=21; $spec.reused_daily_archives=0; $spec.reused_completed_parent_archives=51
$spec.parent_full547_accepted=$false; $spec.new72_independent_QA_required=$true
$spec.created_utc=[datetime]::UtcNow.ToString('o')
$dest=Join-Path $root 'protocols/PERPETUAL_213_SOURCE_20261003_V1.json'
if(Test-Path -LiteralPath $dest) { throw 'Exclusive new source protocol already exists' }
[IO.File]::WriteAllText($dest,($spec|ConvertTo-Json -Depth 30)+"`n",$enc)
[pscustomobject]@{path=$dest;sha256=(Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLowerInvariant();files=$entries.Count;reused=51;new=21}|ConvertTo-Json
