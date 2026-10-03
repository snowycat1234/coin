param([ValidateSet('metadata','source')][string]$Mode)
$ErrorActionPreference='Stop'
$root='D:\codex\coin'
function Digest([string]$Name) { (Get-FileHash -LiteralPath (Join-Path $root $Name) -Algorithm SHA256).Hash.ToLowerInvariant() }
$runner='scripts/investment/perpetual_history_source.py'
if(!(Test-Path -LiteralPath (Join-Path $root $runner))){throw 'Source runner not yet present'}
$old=Get-Content (Join-Path $root 'protocols/PERPETUAL_2H_WARMUP_SOURCE_20261003_V1.json') -Raw|ConvertFrom-Json -AsHashtable -DateKind String
$hashes=[ordered]@{}
foreach($name in $old.frozen_sources.Keys){if((Digest $name) -ne $old.frozen_sources[$name]){throw "Frozen reused source changed: $name"};$hashes[$name]=$old.frozen_sources[$name]}
foreach($name in @($runner,'scripts/investment/accept_perpetual_history_source.py','scripts/investment/audit_perpetual_history_source.py','scripts/research_v8/audit_funding_price_source.py','docs/archive/PERPETUAL_TRADE_SOURCE_INDEPENDENT_AUDITOR_20261003_V1.py','docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py','scripts/investment/public_long_development_adapter.py','protocols/FUNDING_MARK_INDEX_SOURCE_V8_V1.json')){if(Test-Path -LiteralPath (Join-Path $root $name)){$hashes[$name]=Digest $name}}
$entries=@()
$plans=@(@('klines','1m','2024-01-01','2025-06-01'),@('klines','1d','2023-06-01','2024-12-01'),@('klines','2h','2023-12-01','2023-12-01'),@('markPriceKlines','1m','2024-01-01','2025-06-01'),@('fundingRate',$null,'2024-01-01','2025-06-01'))
foreach($plan in $plans){
 $kind,$interval,$first,$last=$plan
 foreach($symbol in @('BTCUSDT','ETHUSDT')){for($month=[datetime]$first;$month -le [datetime]$last;$month=$month.AddMonths(1)){
  $m=$month.ToString('yyyy-MM')
  $url=if($kind -eq 'fundingRate'){"https://data.binance.vision/data/futures/um/monthly/fundingRate/$symbol/$symbol-fundingRate-$m.zip"}else{"https://data.binance.vision/data/futures/um/monthly/$kind/$symbol/$interval/$symbol-$interval-$m.zip"}
  $entry=[ordered]@{market='futures/um';partition='monthly';kind=$kind;symbol=$symbol;month=$m;url=$url;checksum_url=$url+'.CHECKSUM'}
  if($null -ne $interval){$entry.interval=$interval}
  $entries+=$entry
 }}
}
if($entries.Count -ne 148){throw 'Fixed148 entries required'}
$protocol=[ordered]@{ready_for_execution=$true;contract_id='D042_OFFICIAL_PERPETUAL_HISTORY_SOURCE_V1';mode=$Mode;entries=$entries;budgets=[ordered]@{new_owned_bytes=1000000000;max_archive_bytes=16000000;file_write_limit_bytes=32000000;max_csv_bytes=128000000;peak_RSS_bytes=1000000000;file_seconds=30;wall_seconds=1800};frozen_sources=$hashes;environment=@{sys_prefix='/home/xflops/coin-state/v8-clean-env-20261002-v2'};run_dir="/home/xflops/coin-state/d042-perpetual-history-$Mode-20261003-v1";output_path="reports/fast_research/PERPETUAL_HISTORY_$($Mode.ToUpperInvariant())_ACTUAL_20261003_V1.json";score_period_start='2024-01-01';score_period_end_exclusive='2025-07-01';research_role='SEEN_DEVELOPMENT_SCREENING_INPUT_ONLY_NOT_UNSEEN';economic_scope='NOT_EVALUATED';funding_rate_unit='UNCONFIRMED';funding_unit_certified=$false;publication_time_certified=$false;native_Bybit_certified=$false;locked_consumed=$false;GPU=0;orders_sent=0;models_fit=0;new_archives=148;reused_daily_archives=12;combined_capacity_reservation_bytes=2000000000;created_utc=[datetime]::UtcNow.ToString('o')}
$fund=Get-Content (Join-Path $root 'protocols/FUNDING_MARK_INDEX_SOURCE_V8_V1.json') -Raw|ConvertFrom-Json -AsHashtable -DateKind String
foreach($key in @('funding_header','price_header','funding_nominal_interval_tolerance_ms')){$protocol[$key]=$fund[$key]}
if($Mode -eq 'source'){
 $meta='reports/fast_research/PERPETUAL_HISTORY_METADATA_ACTUAL_20261003_V1.json'
 $actual=Get-Content (Join-Path $root $meta) -Raw|ConvertFrom-Json -AsHashtable -DateKind String
 if($actual.status -ne 'PASS_D042_148_OFFICIAL_HISTORY_METADATA_ONLY' -or $actual.completed_files -ne 148 -or $actual.archive_bodies_downloaded -ne 0){throw 'Metadata actual incomplete'}
 $protocol.metadata_path=$meta;$protocol.metadata_sha256=Digest $meta
}
$destination=Join-Path $root "protocols/PERPETUAL_HISTORY_$($Mode.ToUpperInvariant())_20261003_V1.json"
if(Test-Path -LiteralPath $destination){throw 'Exclusive new protocol already exists'}
[IO.File]::WriteAllText($destination,($protocol|ConvertTo-Json -Depth 20)+"`n",[Text.UTF8Encoding]::new($false))
[pscustomobject]@{path=$destination;sha256=(Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant();entries=$entries.Count;mode=$Mode}|ConvertTo-Json