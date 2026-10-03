param([Parameter(Mandatory=$true)][string]$SourceSha)
$ErrorActionPreference='Stop'
Set-Location 'D:/codex/coin'
function TaskDigest([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
$entry='scripts/investment/public_daily_official_source_v3.py'
if ((TaskDigest $entry) -ne $SourceSha) { throw 'Final source bytes differ' }
$archive='docs/archive/PUBLIC_DAILY_SOURCE_PROTOCOL_FREEZER_20261003_V3.ps1'
if (Test-Path -LiteralPath $archive) { throw 'Exclusive archive required' }
[IO.File]::WriteAllBytes((Join-Path (Get-Location) $archive),[IO.File]::ReadAllBytes($PSCommandPath))
$names=@($entry,'scripts/investment/public_daily_official_source_v2.py','scripts/investment/public_daily_official_source.py','src/quant/data.py','src/quant/paths.py','src/quant/disk.py','src/quant/resources.py','scripts/research_v8/funding_price_source_v2.py','scripts/investment/official_carry_chronology_source.py','scripts/investment/bybit_spot_adapter.py','scripts/research_v8/registry.py','docs/archive/V8_OFFICIAL_INPUT_METADATA_SOURCE_20261002_V1.py','reports/fast_research/V8_OFFICIAL_DOWNLOAD_COMPONENT_20261002_V2.json','environments/v8/uv.lock',$archive)
$pins=[ordered]@{}
foreach($name in $names) { $pins[$name]=TaskDigest $name }
$months=@('2023-06','2023-07','2023-08','2023-09','2023-10','2023-11','2023-12')+@(1..12|ForEach-Object{'2024-{0:00}' -f $_})+@(1..12|ForEach-Object{'2025-{0:00}' -f $_})+@('2026-01','2026-02')
$symbols=@('BTCUSDT','ETHUSDT')
$entries=@(foreach($symbol in $symbols){foreach($month in $months){$url="https://data.binance.vision/data/spot/monthly/klines/$symbol/1d/$symbol-1d-$month.zip";[ordered]@{market='spot';kind='klines';partition='monthly';interval='1d';symbol=$symbol;month=$month;url=$url;checksum_url=$url+'.CHECKSUM';metadata_object_available=$null;announced_zip_bytes=$null;announced_zip_sha256=$null;actual_source_rows=$null}}})
if ($months.Count -ne 33 -or $entries.Count -ne 66) { throw 'Exact new calendar required' }
$spec=[ordered]@{contract_id='D037_OFFICIAL_SPOT_DAILY_SOURCE_V1';classification='OFFICIAL_SOURCE_FORMAT_CALENDAR_ONLY_NOT_ECONOMICS';source_start='2023-06-01';source_end_exclusive='2026-03-01';source_calendar=$months;symbols=$symbols;expected_archives=66;expected_days_per_symbol=1004;expected_total_rows=2008;entries=$entries;budgets=[ordered]@{new_owned_bytes=10000000;max_archive_bytes=32768;max_csv_bytes=65536;max_parquet_bytes=32768;wall_seconds=1800;peak_RSS_bytes=1000000000};compressed_bytes_expected=$null;source_acceptance_before_actual=$false;publication_time_certified=$false;economic_scope='NOT_EVALUATED';upstream_commit='f446ce3812bd4e5521f21faecd4ae3c6460e49fc';frozen_sources=$pins;run_dir='/home/xflops/coin-state/d037-official-spot-daily-source-20261003-v2';output_path='reports/fast_research/PUBLIC_DONCHIAN_DAILY_SOURCE_ACTUAL_20261003_V2.json';source_software='Pinned binance/binance-public-data utility.download_file; thin private interval/parser orchestration';data_role='Official1d signal and200completeUTCday warmup; accepted1m data remain execution/risk inputs';locked_consumed=$false;models_fit=0;orders_sent=0;GPU=0;fee_economics='NOT_EVALUATED_SOURCE_ONLY'}
$target='protocols/PUBLIC_DONCHIAN_DAILY_SOURCE_20261003_V3.json'
if(Test-Path -LiteralPath $target){throw 'No overwrite of frozen protocol'}
[IO.File]::WriteAllText((Join-Path (Get-Location) $target),($spec|ConvertTo-Json -Depth 12)+"`n",[Text.UTF8Encoding]::new($false))
[ordered]@{protocol=$target;protocol_sha256=TaskDigest $target;source_sha256=$SourceSha;archives=$entries.Count;new_owned_budget=10000000}|ConvertTo-Json -Compress
