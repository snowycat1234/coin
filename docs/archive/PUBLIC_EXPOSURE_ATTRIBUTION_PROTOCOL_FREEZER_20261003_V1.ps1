param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedProducerSHA256,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedTestSHA256
)
$ErrorActionPreference='Stop'
$root='D:\codex\coin'
function TaskDigest([string]$n){
    if([IO.Path]::IsPathRooted($n)-or$n.Split('/')-contains'..'){throw 'Only ROOT-relative frozen files'}
    (Get-FileHash -LiteralPath (Join-Path $root $n) -Algorithm SHA256).Hash.ToLowerInvariant()
}
function J([string]$n){Get-Content -LiteralPath (Join-Path $root $n) -Raw|ConvertFrom-Json}
function X([string]$n,$value){
    $path=Join-Path $root $n
    if(Test-Path -LiteralPath $path){throw "Exclusive protocol already exists: $n"}
    $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
    try{$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($value|ConvertTo-Json -Depth 40)+"`n");$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
}
$archive='docs/archive/PUBLIC_EXPOSURE_ATTRIBUTION_PROTOCOL_FREEZER_20261003_V1.ps1'
$prepared='.cache/d039_freeze_protocol_20261003_v1.ps1'
if((TaskDigest $archive)-ne(TaskDigest $prepared)){throw 'Prepared/freezer archive must be exact same bytes'}
$producer='scripts/investment/public_exposure_attribution.py'
$test='tests/test_public_exposure_attribution.py'
if((TaskDigest $producer)-ne$ExpectedProducerSHA256.ToLowerInvariant()-or(TaskDigest $test)-ne$ExpectedTestSHA256.ToLowerInvariant()){
    throw 'Final producer/test bytes differ; do not freeze an in-progress source'
}
$reconPath='docs/archive/PUBLIC_EXPOSURE_ATTRIBUTION_INPUT_RECON_20261003_V1.json'
$reconSHA='2bc70b7f7bf1a6227fc8cd449ed523f49124076d0b3ff5abf43f958ad527a3fe'
$methodPath='docs/archive/PUBLIC_EXPOSURE_ATTRIBUTION_METHOD_REVIEW_20261003_V1.md'
$methodSHA='e4a03a4bdf96cac3da463d9ffba0783e3188cf71ad6f07fb676bbe558bffbf2b'
if((TaskDigest $reconPath)-ne$reconSHA-or(TaskDigest $methodPath)-ne$methodSHA){throw 'Accepted recon or prior method-review bytes changed'}
$recon=J $reconPath
if($recon.actual_case_count-ne9-or$recon.artifact_files-ne18-or$recon.market_or_ledger_arrays_read-ne$false-or$recon.all_costs.spread_bps-ne8-or$recon.all_costs.nominal_roundtrip_bps-ne36-or$recon.all_costs.initial_nav-ne10000){throw 'Fixed nine-case metadata scope required'}
$head=(git -C $root rev-parse HEAD).Trim()
if($head-ne'4bf2bc1c521835c22598482900329c96a0564d4f'-or$recon.git_commit-ne$head){throw 'D038 parent HEAD must remain fixed before D039'}
$fixed=[ordered]@{}
foreach($group in @('small_report_hashes','schema_source_hashes')){
    foreach($entry in $recon.$group.PSObject.Properties){
        if((TaskDigest $entry.Name)-ne$entry.Value){throw "Accepted frozen metadata/source changed: $($entry.Name)"}
        $fixed[$entry.Name]=$entry.Value
    }
}
$fee='protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json'
$env='environments/v8/uv.lock'
foreach($name in @($archive,$producer,$test,$reconPath,$methodPath,$fee,$env,'state/dataset_lock.json',
    'scripts/investment/public_pair_diagnostics.py','scripts/investment/public_pair_diagnostics_v2.py',
    'docs/archive/PUBLIC_EXPOSURE_ATTRIBUTION_CASE_RUNNER_20261003_V1.py',
    'scripts/research_v7/oracle_flow_ceiling.py','scripts/research_v8/registry.py',
    'src/quant/resources.py','src/quant/disk.py','src/quant/paths.py')){
    $digest=TaskDigest $name
    if($fixed.Contains($name)-and$fixed[$name]-ne$digest){throw 'Inconsistent shared frozen identity'}
    $fixed[$name]=$digest
}
if($fixed[$env]-ne'97335dc3dbb04d7dbc67425f91d4e941a0cfd2c84e5f2adcd852514ec4600de6'-or$fixed[$fee]-ne'd6c1e2f5b25dabf4d088edfbccbc35d7154684287ff477c2fc16a14ee5f96b3f'-or$fixed['state/dataset_lock.json']-ne'29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'){
    throw 'Accepted environment, fee profile and private lock hashes required'
}
$rules=[ordered]@{
    cash_tolerance=0.0000001
    ratio_tolerance=0.000000000001
    material_notional_USDT=10.0
    above_target_weight=0.3
    spread_execution_fraction=0.5
    slippage_execution_fraction=0.5
    gross_formula='SUM_NEG_POSITION_DELTA_TIMES_FILL_MID_PLUS_TERMINAL_MARKED'
    net_formula='GROSS_MINUS_FEE_USDT_MID_MINUS_GROSS_EXECUTION_COST'
    windows_independent=$true
    snapshot_holding_scope='RECORDED_MINUTE_SNAPSHOTS_NOT_EVENT_HOLDING_DURATION'
    alpha_beta_identified=$false
    new_account_NAV_generated=$false
}
$inputBytes=0
foreach($case in $recon.cases){foreach($entry in $case.artifacts.PSObject.Properties){$inputBytes+=$entry.Value.bytes}}
$spec=[ordered]@{
    contract_id='D039_PUBLIC_EXPOSURE_ATTRIBUTION_20261003_V1'
    classification='SCREENING_SAVED_NATIVE_SPOT_ASSET_ATTRIBUTION_NOT_ACCOUNT_OR_ALPHA'
    created_utc=[DateTime]::UtcNow.ToString('o')
    original_head=$head
    frozen_sources=$fixed
    environment=[ordered]@{lock_path=$env;lock_sha256=$fixed[$env];sys_prefix='/home/xflops/coin-state/v8-clean-env-20261002-v2'}
    fee_profile=[ordered]@{path=$fee;sha256=$fixed[$fee];market_type='SPOT';fee_settlement='BYBIT_SPOT_RECEIVED_ASSET_V1';fee_bps_per_side=10;half_spread_bps_per_side=4;slippage_bps_per_side=4;nominal_roundtrip_bps=36;data_venue='Binance';fee_reference_venue='Bybit';native_market_certified=$false}
    recon_path=$reconPath
    recon_sha256=$reconSHA
    method_review_path=$methodPath
    method_review_sha256=$methodSHA
    synthetic_test_path=$test
    required_smoke_receipt='reports/fast_research/PUBLIC_EXPOSURE_ATTRIBUTION_SYNTHETIC_20261003_V1.json'
    calculation_rules=$rules
    budgets=[ordered]@{new_owned_bytes=5000000;module_combined_STATE_bytes=10000000;peak_RSS_bytes=1000000000;wall_seconds=600;additional_market_copy_bytes=0;input_files=18;cases=9}
    input_bytes_from_saved_metadata=$inputBytes
    cases=$recon.cases
    run_dir='/home/xflops/coin-state/public-exposure-attribution-20261003-v1'
    output_path='reports/fast_research/PUBLIC_EXPOSURE_ATTRIBUTION_ACTUAL_20261003_V1.json'
    market_source_or_ledger_arrays_read_by_freezer=$false
    old_accounts_or_QA_or_tests_replayed=$false
    new_market_accounts=0
    models_fit=0
    HPO=0
    orders_sent=0
    GPU=0
    shared_RAM_limit_bytes=5000000000
    swap_bytes=0
    locked_consumed=$false
    candidate_status='NO_QUALIFIED_CANDIDATE'
    long_term_APR='NOT_EVALUABLE'
    alpha_qualification=$false
    native_market_certified=$false
    windows_independent=$true
    accounts_stitched=$false
    initial_capital_per_coin_assigned=$false
    same_caps_not_equal_realized_risk=$true
    financial_scope='Saved same-net-received-quantity gross/cost contribution and actual marked-exposure diagnosis; no new account NAV, causal alpha/beta identification or statistical profitability qualification'
    terminal_inventory='Accepted MTM retained, no hypothetical sale, cash liquidation or free terminal execution'
    historical_audit_scope='Accepted composite 2h122/90 financial blocks reused; the retained original failed whole-six suite is not relabeled PASS'
}
$output='protocols/PUBLIC_EXPOSURE_ATTRIBUTION_20261003_V1.json'
X $output $spec
[ordered]@{protocol=$output;sha256=TaskDigest $output;bytes=(Get-Item -LiteralPath (Join-Path $root $output)).Length;sourcecount=$fixed.Count;cases=9;input_files=18;array_files_read=$false}|ConvertTo-Json -Compress
