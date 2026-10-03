$ErrorActionPreference='Stop'
$root='D:/codex/coin'; $enc=[Text.UTF8Encoding]::new($false)
function Digest([string]$Name) {(Get-FileHash -LiteralPath (Join-Path $root $Name) -Algorithm SHA256).Hash.ToLowerInvariant()}
function NewText([string]$Name,[string]$Text) {$p=Join-Path $root $Name; if(Test-Path -LiteralPath $p){throw "Exclusive path: $Name"};[IO.File]::WriteAllText($p,$Text,$enc)}
$old=Get-Content (Join-Path $root 'protocols/PERPETUAL_HISTORY_SOURCE_20261003_V1.json') -Raw|ConvertFrom-Json -AsHashtable -DateKind String
$hashes=[ordered]@{}
foreach($name in $old.frozen_sources.Keys){if((Digest $name) -ne $old.frozen_sources[$name]){throw "Frozen dependency: $name"};$hashes[$name]=$old.frozen_sources[$name]}
$runner='scripts/investment/perpetual_303_source.py'
$archive='docs/archive/PERPETUAL_303_SOURCE_PRODUCER_SOURCE_20261003_V1.py'
if(Test-Path -LiteralPath (Join-Path $root $archive)){throw 'Exclusive archive'}
[IO.File]::WriteAllBytes((Join-Path $root $archive),[IO.File]::ReadAllBytes((Join-Path $root $runner)))
$freezer='docs/archive/PERPETUAL_303_SOURCE_PROTOCOL_FREEZER_20261003_V1.ps1'
if(Test-Path -LiteralPath (Join-Path $root $freezer)){throw 'Exclusive freezer'}
[IO.File]::WriteAllBytes((Join-Path $root $freezer),[IO.File]::ReadAllBytes($PSCommandPath))
foreach($name in @($runner,$archive,$freezer,'reports/fast_research/PERPETUAL_HISTORY_SOURCE_ACTUAL_20261003_V1.json','reports/fast_research/PERPETUAL_HISTORY_METADATA_ACTUAL_20261003_V1.json','reports/fast_research/PERPETUAL_TRADE_SOURCE_ACTUAL_20261003_V1.json','reports/fast_research/PERPETUAL_TRADE_SOURCE_METADATA_20261003_V1.json')){$hashes[$name]=Digest $name}
$t=Get-Content (Join-Path $root 'protocols/PERPETUAL_TRADE_SOURCE_20261003_V1.json') -Raw|ConvertFrom-Json -AsHashtable -DateKind String
$entries=@($old.entries|Where-Object {($_.kind -eq 'klines' -and $_.interval -eq '1d' -and $_.month -ge '2024-02') -or ($_.interval -ne '1d' -and $_.interval -ne '2h' -and $_.month -ge '2024-09')})+@($t.entries|Where-Object {$_.interval -eq '1d' -and $_.month -ge '2025-01' -and $_.month -le '2025-06'})
# Original adapter order: trade1m, daily, mark1m, funding; symbol, then month.
$rank=@{'klines:1m'=0;'klines:1d'=1;'markPriceKlines:1m'=2;'fundingRate:'=3}
$entries=@($entries|Sort-Object @{Expression={$rank["$($_.kind):$($_.interval)"]}},symbol,month)
if($entries.Count -ne 94){throw 'Exactly94 selectors'}
$spec=[ordered]@{};foreach($k in $old.Keys){$spec[$k]=$old[$k]}
$spec.contract_id='D045_FIXED_303D_MIXED_OWNER_OFFICIAL_SOURCE_V1';$spec.entries=$entries;$spec.frozen_sources=$hashes
$spec.required_files=94;$spec.expected_reused_files=54;$spec.expected_new_files=40
$spec.score_period_start='2024-09-01';$spec.score_period_end_exclusive='2025-07-01';$spec.score_days=303;$spec.score_minutes_per_symbol=436320
$spec.run_dir='/home/xflops/coin-state/d045-perpetual-303-source-20261003-v1';$spec.output_path='reports/fast_research/PERPETUAL_303_SOURCE_ACTUAL_20261003_V1.json'
$spec.new_archives=40;$spec.reused_complete_producer_files=54;$spec.first_independent_QA_required=70;$spec.accepted_prior_QA_reuse_expected=24
$spec.metadata_reuse_role='ORIGINAL_148_AND_42_CLOSED_TASKS_PROJECTION_NO_NEW_HEAD';$spec.created_utc=[datetime]::UtcNow.ToString('o')
NewText 'protocols/PERPETUAL_303_SOURCE_20261003_V1.json' (($spec|ConvertTo-Json -Depth 30)+"`n")
[pscustomobject]@{source_sha256=Digest $runner;protocol_sha256=Digest 'protocols/PERPETUAL_303_SOURCE_20261003_V1.json';required=94;existing=54;new=40}|ConvertTo-Json
