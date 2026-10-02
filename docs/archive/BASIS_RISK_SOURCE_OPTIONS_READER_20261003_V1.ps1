# Existing receipt selection only; never opens a Parquet or a network endpoint.
$ErrorActionPreference = 'Stop'
$spotName = 'reports/fast_research/V8_EXISTING_FROZEN_SPOT_MINUTE_SOURCE_REUSE_20261002_V1.json'
$acceptName = 'reports/fast_research/V8_FUNDING_MARK_INDEX_SOURCE_ACCEPTANCE_20261002_V1.json'
$qaName = 'reports/fast_research/V8_FUNDING_MARK_INDEX_INDEPENDENT_QA_20261002_V1.json'
$correctionName = 'reports/fast_research/V8_FUNDING_MARK_INDEX_HEADER_CORRECTION_20261002_V1.json'
$outName = 'reports/fast_research/BASIS_RISK_SOURCE_OPTIONS_20261003_V1.json'
if (Test-Path -LiteralPath $outName) { throw 'Exclusive new report only' }
$spot = Get-Content -LiteralPath $spotName -Raw | ConvertFrom-Json
$accept = Get-Content -LiteralPath $acceptName -Raw | ConvertFrom-Json
$qa = Get-Content -LiteralPath $qaName -Raw | ConvertFrom-Json
if ($spot.status -cne 'PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_153D_CALENDAR' -or
    $accept.status -cne 'PASS_NEW_OFFICIAL_INPUT_SOURCE_FORMAT_ONLY_INDEPENDENT_QA' -or
    $qa.status -cne 'PASS_OFFICIAL_CARRY_INPUT_FORMAT_ONLY_INDEPENDENT_QA') { throw 'Existing accepted source receipts required' }
$months = @('2025-08','2025-09','2025-10','2025-11')
$spotSHA = (Get-FileHash -LiteralPath $spotName -Algorithm SHA256).Hash.ToLowerInvariant()
$sources = @()
foreach ($r in $spot.sources | Where-Object { $_.month -in $months }) {
    $sources += [pscustomobject]@{kind='spot1m';symbol=$r.symbol;month=$r.month;
        parquet_path=$r.normalized_path;parquet_sha256=$r.normalized_sha256;rows=$r.rows;
        first_open_us=$r.old_quality.first_open_us;last_open_us=$r.old_quality.last_open_us;
        source_receipt_path=$spotName;source_receipt_sha256=$spotSHA;
        QA_scope='EXACT_EXISTING_SEALED_CALENDAR_QA_REUSED_NO_ROW_READ'}
}
foreach ($r in $accept.sources | Where-Object { $_.kind -in @('markPriceKlines','indexPriceKlines') }) {
    $checked = @($qa.sources | Where-Object { $_.kind -eq $r.kind -and $_.symbol -eq $r.symbol -and $_.month -eq $r.month })
    if ($checked.Count -ne 1 -or !$checked[0].exact_1m_calendar -or
        $checked[0].status -cne 'PASS_SOURCE_FORMAT_ONLY' -or
        $checked[0].receipt_sha256 -cne $r.receipt_sha256) { throw 'Existing proxy metadata QA differs' }
    $native = $r.receipt_path.Replace('/home/xflops/coin-state/','\\wsl.localhost\hpc_linux\home\xflops\coin-state\').Replace('/','\')
    $receipt = Get-Content -LiteralPath $native -Raw | ConvertFrom-Json
    if ((Get-FileHash -LiteralPath $native -Algorithm SHA256).Hash.ToLowerInvariant() -cne $r.receipt_sha256 -or
        $receipt.parquet_sha256 -cne $r.parquet_sha256) { throw 'Original small proxy receipt changed' }
    $sources += [pscustomobject]@{kind=$r.kind;symbol=$r.symbol;month=$r.month;
        parquet_path=$r.parquet_path;parquet_sha256=$r.parquet_sha256;rows=$r.rows;
        first_timestamp_ms=$checked[0].first_timestamp_ms;last_timestamp_ms=$checked[0].last_timestamp_ms;
        source_receipt_path=$r.receipt_path;source_receipt_sha256=$r.receipt_sha256;
        original_per_file_status=$receipt.status;
        QA_scope='LATER_INDEPENDENT_ACCEPTANCE_REUSED_ORIGINAL_PER_FILE_STATUS_UNCHANGED'}
}
$groups = @($sources | Group-Object { '{0}:{1}' -f $_.kind,$_.symbol })
if ($sources.Count -ne 24 -or $groups.Count -ne 6 -or
    @($groups | Where-Object { $_.Count -ne 4 -or ($_.Group | Measure-Object -Property rows -Sum).Sum -ne 175680 }).Count -gt 0) {
    throw 'Exactly six complete 122-day streams, eight monthly files per kind required'
}
$proofs = [ordered]@{}
foreach ($name in @($spotName,$acceptName,$qaName,$correctionName,
    'protocols/FUNDING_MARK_INDEX_SOURCE_V8_V1.json','src/quant/data.py','scripts/research_v8/funding_price_source_v2.py')) {
    $proofs[$name] = (Get-FileHash -LiteralPath $name -Algorithm SHA256).Hash.ToLowerInvariant()
}
$report = [ordered]@{
    status='READONLY_METADATA_NOT_QA_NOT_ECONOMICS';created_utc=[DateTimeOffset]::UtcNow.ToString('o');
    research_decision='D027';period_start='2025-08-01';period_end_exclusive='2025-12-01';
    symbols=@('BTCUSDT','ETHUSDT');source_calendar=$months;source_file_count=24;
    rows_per_symbol_per_kind=175680;expected_joint_minutes_per_symbol=175680;source_proofs=$proofs;
    new_data_downloaded=$false;source_receipt_hashes_checked=$true;Parquet_bytes_or_rows_read=$false;
    Parquet_hashes_inherited_from_existing_acceptance=$true;QA_repeated=$false;economics_computed=$false;
    locked_consumed=$false;models_fit=0;orders_sent=0;GPU=0;
    price_profiles=[ordered]@{
        spot1m=[ordered]@{price_field='close';price_dtype='double';
            definition='Official Binance Spot1m kline Close column unchanged except Float64 cast in src/quant/data.py parse_csv; not project last-aggTrade reconstruction';
            timestamp_field='open_us';timestamp_dtype='int64';timestamp_unit='EPOCH_MICROSECONDS';
            normalized_close='close_us=open_us+60000000';source_close='source_close_us preserves original CSV endpoint';
            normalized_available='available_us=open_us+60000000 is a logical closed-bar convention, not measured historical publication';
            not_certified='Not BBO, executable fill or specifically observed last trade'};
        markPriceKlines=[ordered]@{price_field='close';price_dtype='double';
            definition='Official Binance USD-M 1m mark-price kline close';
            timestamp_field='timestamp_ms';timestamp_dtype='int64';timestamp_unit='EPOCH_MILLISECONDS';
            close_endpoint='close_time_ms=timestamp_ms+59999';
            not_certified='Not executable perpetual trade price/BBO or exact funding-charge mark'};
        indexPriceKlines=[ordered]@{price_field='close';price_dtype='double';
            definition='Official Binance USD-M 1m index-price kline close';
            timestamp_field='timestamp_ms';timestamp_dtype='int64';timestamp_unit='EPOCH_MILLISECONDS';
            close_endpoint='close_time_ms=timestamp_ms+59999';
            not_certified='Composite index proxy, not Spot venue trade/BBO/fill'}
    };
    logical_alignment=[ordered]@{
        join_rule='Spot.open_us == 1000 * mark.timestamp_ms == 1000 * index.timestamp_ms';
        closed_bar_rule='Spot.close_us == (mark.close_time_ms+1)*1000 == (index.close_time_ms+1)*1000';
        selection='OPEN in [Aug1,Dec1); last complete minute closes at Dec1 boundary';
        missing='No interpolation, synthetic carry-forward, or missing-row deletion';
        not_newly_verified='Actual values/joins/unchanged Parquet hashes require the future bounded diagnostic, not this receipt'};
    header_correction='Prior acceptance synopsis said absent price headers in error; append-only correction and QA record exact 12-column headers. Original receipts remain unchanged.';
    sources=$sources;
    original_scope='Carry24 consists of funding8+mark8+index8. This metadata selection is mark8/index8+Spot8; no raw ZIP/QA/stat replay.';
    limitations=@('Research close proxies, not fills','Funding unit still unconfirmed; no charge mark reconstructed',
        'No cash/quantity/fee-asset/capital/margin/liquidation/financing closure','No NAV/APR/Candidate/unseen qualification');
    source_ready_for_protocol_only=$true;
    preparation_source='.cache/basis_risk_source_options_20261003_v1.ps1';
    preparation_source_sha256=(Get-FileHash -LiteralPath '.cache/basis_risk_source_options_20261003_v1.ps1' -Algorithm SHA256).Hash.ToLowerInvariant();
    prior_metadata_save_attempt='PowerShell OrderedDictionary property aggregation failed before output; corrected to PSCustomObject only, no rows read or report overwritten'
}
$payload = [Text.UTF8Encoding]::new($false).GetBytes(($report | ConvertTo-Json -Depth 10)+[Environment]::NewLine)
$stream = [IO.File]::Open((Join-Path (Get-Location).Path $outName),[IO.FileMode]::CreateNew)
try { $stream.Write($payload,0,$payload.Length) } finally { $stream.Dispose() }
Get-FileHash -LiteralPath $outName -Algorithm SHA256 | ForEach-Object { '{0} {1}' -f $_.Hash,$_.Path }
Get-Item -LiteralPath $outName | ForEach-Object { '{0} bytes' -f $_.Length }
