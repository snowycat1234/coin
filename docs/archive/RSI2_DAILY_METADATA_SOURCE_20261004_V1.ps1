param(
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedTargetSHA256,
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedPortfolioSHA256,
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedCheckerSHA256,
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedComparerSHA256,
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedDataSHA256,
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedSharedSHA256,
 [Parameter(Mandatory)][string]$WarmProofPath,
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$WarmProofSHA256,
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{32}$')][string]$MetadataTaskId
)
$ErrorActionPreference='Stop'
$root='D:\codex\coin';$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state'
$parent='713618686ac2208f52e9b15fe072a9d5149b25b9'
$adapter='scripts/investment/rsi2_daily_pool_target.py'
$strategy='COIN_JESSE_RSI2_1D_USDM_CONFIGURED_POOL_ADAPTER'
$signal='PUBLIC_RSI2_OVERSOLD_ABOVE_SMA200_LONG_OR_CASH'
$archive='docs/archive/RSI2_DAILY_METADATA_SOURCE_20261004_V1.ps1'
$metadata='reports/fast_research/RSI2_DAILY_INPUT_BINDING_20261004_V1.json'
function TaskDigest($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function StatePath($p){if(-not $p.StartsWith('/home/xflops/coin-state/') -or $p -match '(^|/)\.\.(/|$)'){throw 'Only exact STATE metadata'};Join-Path $state $p.Substring(24)}
function MetaPath($p){if($p.StartsWith('/home/xflops/coin-state/')){return StatePath $p};if($p.StartsWith('/mnt/d/codex/coin/')){$p=$p.Substring(18)};if([IO.Path]::IsPathRooted($p) -or $p -match '(^|[/\\])\.\.([/\\]|$)' -or $p -eq 'state/dataset_lock.json'){throw 'Public ROOT or STATE metadata only'};Join-Path $root $p}
function ReadSmall($p,$sha){$f=Get-Item -LiteralPath $p;if($f.Length -gt 2000000 -or $f.LinkType){throw 'Small ordinary JSON only'};if($sha -and (TaskDigest $p) -ne $sha){throw ('Exact metadata SHA '+$p)};Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
function Closed($id){if($id -notmatch '^[0-9a-f]{32}$'){throw 'Actual task identity'};$p=Join-Path $state ('task-progress/task-'+$id+'.json');$t=ReadSmall $p '';if($t.id -ne $id -or $t.status -ne 'completed' -or $t.exit_code -ne 0 -or -not $t.ended_at){throw 'Actual closed0 prerequisite'};@{path='/home/xflops/coin-state/task-progress/task-'+$id+'.json';sha256=TaskDigest $p;task=$t}}
function SaveNew($p,$value){if(Test-Path -LiteralPath $p){throw ('Existing output '+$p)};[IO.File]::WriteAllText($p,($value|ConvertTo-Json -Depth 40)+"`n",[Text.UTF8Encoding]::new($false))}
$testPath='protocols/RSI2_DAILY_POOL_TARGET_SYNTHETIC_20261004_V2.json'
$testSpec=ReadSmall (Join-Path $root $testPath) ''
$testReportPath='reports/fast_research/RSI2_DAILY_POOL_TARGET_SYNTHETIC_20261004_V2.json'
$testReport=ReadSmall (Join-Path $root $testReportPath) ''
if($testReport.status -ne 'PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT' -or $testReport.test_exit_code -ne 0 -or -not $testReport.source_bytes_unchanged -or $testReport.binding.source_hashes['scripts/investment/public_sma_perpetual.py'] -ne $ExpectedSharedSHA256){throw 'Actual new240 and preserved default synthetic compatibility'}
$testClosed=Closed $testReport.binding.task_id
$rules=$testSpec.calculation_rules;$parameters=$testSpec.rsi_parameters
if($rules.completed_daily_eligibility_bars -ne 240 -or $parameters.rsi_os_threshold -ne 10){throw 'Pinned daily RSI2 no search choice'}
$warm=ReadSmall (MetaPath $WarmProofPath) $WarmProofSHA256
if($warm.status -ne 'PASS_D058_JANUARY_DAILY_WARMUP_SOURCE_FORMAT_ONLY' -or -not $warm.source_only -or $warm.actual_exit_code -ne 0 -or $warm.sources.Count -ne 10){throw 'New independent warm source acceptance only'}
$warmClosed=Closed $warm.binding.task_id
$cases=@(
 @{id='SEPNOV91';stem='MULTI_ASSET_CONTINUOUS_91D_TEN_EQUAL_20261004_V1';days=91;start=1725148800000000L;end=1733011200000000L;parent_sha='25fdf0ab7ae6fe1cfd1a01f13800b3360146748d4bfc23395c6c6485428384c9';actual_sha='cfa3e3b6aac8643b7ff3f3fd2ac325dbd75f16cb4d0c83d41984a0b04f70e3a1';task='e535a25117c14b119d5610fcaa5d203f';owner='/home/xflops/coin-state/d055-continuous-ten-equal-20261004-v1';rb_sha='78306e59477f7e1eed028396dbbcc8c76c4fad92f61158d9381684a5081e8bd2';manifest_sha='847d8a6e561d782ae641d492697ee03fd7b3ba2eda65298e5d0f02cb0c7b1e50';new_owner='d058-rsi2-daily-sep-nov-20261004-v1'}
 @{id='DECFEB90';stem='MULTI_ASSET_WINTER_TEN_EQUAL_20261004_V3';days=90;start=1733011200000000L;end=1740787200000000L;parent_sha='9ddc2928df55e4ec835de398943fce20834a22495bf5bc8284f7363a4b92e3dc';actual_sha='bc0b50f77837d400874f6fa133e5656748e62c6d93eb798ac3a6198a189b8f70';task='9be98723fd944f8fbb49e4f479955e2e';owner='/home/xflops/coin-state/d056-winter-ten-equal-20261004-v3';rb_sha='5a31a6017ce5ddc9d7474442a9eb43bfa1a376b0695b52db0cdaf887ced7bb64';manifest_sha='56f1eb1b768e14d4c67198156732c1d4a22e6a901e980c24ebee9f20bbf86193';new_owner='d058-rsi2-daily-dec-feb-20261004-v1'}
)
if((git -C $root rev-parse HEAD) -ne $parent -or (Test-Path -LiteralPath (Join-Path $root $metadata))){throw 'Accepted parent and new metadata output required'}
$updates=@{'scripts/investment/multi_asset_data.py'=$ExpectedDataSHA256;'scripts/investment/multi_asset_portfolio.py'=$ExpectedPortfolioSHA256;'scripts/investment/public_sma_perpetual.py'=$ExpectedSharedSHA256}
$newPins=@{$adapter=$ExpectedTargetSHA256;'scripts/investment/multi_asset_financial_audit.py'=$ExpectedCheckerSHA256;'scripts/investment/compare_multi_asset_portfolios.py'=$ExpectedComparerSHA256}
foreach($entry in @($updates.GetEnumerator())+@($newPins.GetEnumerator())){if((TaskDigest (Join-Path $root $entry.Key)) -ne $entry.Value){throw ('Final held current source '+$entry.Key)}}
$prepared=@{};$proofs=@{}
foreach($case in $cases){
 $pp='protocols/'+$case.stem+'.json';$ap='reports/fast_research/'+$case.stem+'.json'
 $p=ReadSmall (Join-Path $root $pp) $case.parent_sha;$a=ReadSmall (Join-Path $root $ap) $case.actual_sha;$t=Closed $case.task
 $rb=ReadSmall (StatePath ($case.owner+'/RUN_BINDING.json')) $case.rb_sha
 if($a.binding.task_id -ne $case.task -or $a.run_dir -ne $case.owner -or $a.completed_cases -ne 4 -or $a.complete_calendar_cases -ne 4 -or $a.actual_calendar_days -ne $case.days -or $a.allocation -ne 'EQUAL' -or $a.strategy_id -ne 'COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'){throw 'Saved complete equal-HOLD prerequisite only'}
 if($rb.task_id -ne $case.task -or $rb.protocol_sha256 -ne $case.parent_sha -or $rb.manifest_sha256 -ne $case.manifest_sha -or ($rb.source_hashes|ConvertTo-Json -Compress) -ne ($p.source_hashes|ConvertTo-Json -Compress)){throw 'Original RUN_BINDING agrees with original protocol, not current source bytes'}
 $m=ReadSmall (MetaPath $p.data_manifest.path) $case.manifest_sha
 if($p.data_manifest.sha256 -ne $case.manifest_sha -or $m.start_us -ne $case.start -or $m.end_us -ne $case.end -or $m.days -ne $case.days -or $m.source_only -ne $true -or $m.checksummed_source_format_verified -ne $true -or $m.market_records.Count -ne 90 -or $m.daily_records.Count -ne 70 -or $m.control_daily_records.Count -ne 14){throw 'Accepted unchanged quarter source schema'}
 if($p.pool_receipt.path -ne $m.pool_receipt.path -or $p.pool_receipt.sha256 -ne $m.pool_receipt.sha256 -or ($p.pools[1].symbols|ConvertTo-Json -Compress) -ne ($m.selected_symbols|ConvertTo-Json -Compress)){throw 'Same exact July pool identity; extra status metadata is not a new pool'}
 $caps=if($case.id -eq 'SEPNOV91'){@($m.monthly_acceptances)}else{@($m.source_acceptance)+@($m.warmup_source_acceptances)}
 $capProofs=@();foreach($ref in $caps){$cap=ReadSmall (MetaPath $ref.path) $ref.sha256;if($cap.status -ne $ref.required_status -or $cap.source_only -ne $true -or $cap.actual_exit_code -ne 0){throw 'Actually accepted source capability'};$capProofs+=@{reference=$ref;closed_task=Closed $cap.binding.task_id}}
 $records=@($m.market_records)+@($m.daily_records);if($m.ContainsKey('warmup_minute_records')){$records+=@($m.warmup_minute_records)}
 foreach($r in $records){$f=Get-Item -LiteralPath (StatePath $r.normalized_path);if($f.LinkType -or $f.Length -ne $r.normalized_bytes -or $m.normalized_source_hashes[$r.normalized_path] -ne $r.normalized_sha256){throw 'Bound source descriptor and file stat unchanged; no payload rehash'}}
 $new=($p|ConvertTo-Json -Depth 40|ConvertFrom-Json -AsHashtable -DateKind String)
 foreach($name in @($new.source_hashes.Keys)){$expected=if($updates.ContainsKey($name)){$updates[$name]}else{$p.source_hashes[$name]};if($name -eq 'state/dataset_lock.json' -or (TaskDigest (Join-Path $root $name)) -ne $expected){throw ('Unchanged financial/target source '+$name)};$new.source_hashes[$name]=$expected}
 $new.source_hashes[$adapter]=$ExpectedTargetSHA256
 foreach($extra in @('scripts/investment/public_rsi2_adapter.py','scripts/investment/public_rsi2_indicator.py','scripts/research_v8/public_donchian_adapter.py','scripts/investment/public_donchian_hybrid.py')){$new.source_hashes[$extra]=TaskDigest (Join-Path $root $extra)}
 foreach($f in Get-ChildItem -LiteralPath (Join-Path $root 'third_party/jesse_example_rsi2') -File){$rel='third_party/jesse_example_rsi2/'+$f.Name;$new.source_hashes[$rel]=TaskDigest $f.FullName}
 $new.strategy=$strategy;$new.signal=$signal;$new.strategy_rules=$rules;$new.rsi_parameters=$parameters
 $new.target_compatibility=@{path=$testReportPath;sha256=TaskDigest (Join-Path $root $testReportPath)}
 if($case.id -eq 'SEPNOV91'){
  if($warm.pool_receipt.sha256 -ne $p.pool_receipt.sha256 -or ($warm.symbols|Sort-Object|ConvertTo-Json -Compress) -ne ($m.selected_symbols|Sort-Object|ConvertTo-Json -Compress)){throw 'Same frozen pool, early daily only'}
  $new.daily_warmup_extension=@{path=$WarmProofPath;sha256=$WarmProofSHA256}
  $new.warmup='Separately accepted January1d plus originalFebAug; true240 available context required per member; short IPO history stays cash, no pool change.'
 }
 $new.experiment_id='D058-RSI2-DAILY-'+$case.id+'-20261004'
 $new.independent_reference_pre_market_sha256=$ExpectedCheckerSHA256;$new.economic_comparer_pre_market_sha256=$ExpectedComparerSHA256
 $new.budget=@{owned_bytes=250000000;wall_seconds=1800;peak_RSS_bytes=3000000000}
 $new.research_budget=@{models_fit=0;HPO=0;new_actual_accounts=8;new_independent_accounts=8;total_new_STATE_bytes=800000000;new_recipes=1;test_owned_bytes=10000000;test_wall_seconds=1200;test_peak_RSS_bytes=1000000000;metadata_owned_bytes=5000000;financial_owned_bytes_per_run=100000;financial_wall_seconds=1800;financial_peak_RSS_bytes=1500000000}
 $new.question='Do original RSI2 long/exit hooks on a fixed daily timeframe improve money/risk quality versus saved equal-HOLD across both full seen quarters?'
 $new.success_rule='Eight new true complete or truthfully halted calendars and independent accounting; compare saved same-quarter equal HOLD without replay or positive-profit requirement.'
 $new.created_utc=[DateTimeOffset]::UtcNow.ToString('o')
 $out='protocols/RSI2_DAILY_'+$case.id+'_20261004_V1.json';$actual='reports/fast_research/RSI2_DAILY_'+$case.id+'_20261004_V1.json'
 if((Test-Path -LiteralPath (Join-Path $root $out)) -or (Test-Path -LiteralPath (Join-Path $root $actual)) -or (Test-Path -LiteralPath (Join-Path $state $case.new_owner))){throw 'Exclusive new experiment; failed attempt needs a new declared identity'}
 $prepared[$case.id]=@{path=$out;spec=$new;run_dir='/home/xflops/coin-state/'+$case.new_owner;output_path=$actual;required_cli_pool_id='LIQUIDITY_TEN';required_cases=4}
 $proofs[$case.id]=@{protocol=@{path=$pp;sha256=$case.parent_sha};actual=@{path=$ap;sha256=$case.actual_sha};closed_task=$t;owner=$case.owner;run_binding_sha256=$case.rb_sha;manifest=$p.data_manifest;accepted_capabilities=$capProofs;warmup_scope='Original accepted70 daily and existing necessary minute-derived days;200-contiguous-day eligibility remains original loader guard;not new rows QA'}
}
if((TaskDigest (Join-Path $root 'state/dataset_lock.json')) -ne '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'){throw 'Private policy streaming SHA only'}
if(Test-Path -LiteralPath (Join-Path $root $archive)){if((TaskDigest $PSCommandPath) -ne (TaskDigest (Join-Path $root $archive))){throw 'Existing helper archive differs'}}else{Copy-Item -LiteralPath $PSCommandPath -Destination (Join-Path $root $archive)}
$protocols=@{};foreach($id in $prepared.Keys){$v=$prepared[$id];SaveNew (Join-Path $root $v.path) $v.spec;$protocols[$id]=@{path=$v.path;sha256=TaskDigest (Join-Path $root $v.path);run_dir=$v.run_dir;output_path=$v.output_path;required_cli_pool_id=$v.required_cli_pool_id;required_cases=4}}
$result=@{status='READY_D058_TWO_UNCHANGED_SOURCE_QUARTERS_RSI2_DAILY_PROTOCOLS_NOT_MARKET_RESULTS';task_id=$MetadataTaskId;own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED';parent_commit=$parent;metadata_source=@{path=$archive;sha256=TaskDigest $PSCommandPath};protocols=$protocols;accepted_saved_references=$proofs;daily_warmup_acceptance=@{path=$WarmProofPath;sha256=$WarmProofSHA256;closed_task=$warmClosed};target_compatibility=@{path=$testReportPath;sha256=TaskDigest (Join-Path $root $testReportPath);closed_task=$testClosed};new_downloads_by_this_metadata_call=0;source_QA_calls_by_this_metadata_call=0;warmup_sources=10;warmup_capability_reused_without_payload_QA=$true;market_accounts=0;financial_calls=0;models_fit=0;HPO=0;funding_unit_certified=$false;native_certified=$false;candidate='NONE';investment='CASH';long_term_APR='NOT_EVALUABLE';source_payloads_read=0;private_lock_body_read=$false;created_utc=[DateTimeOffset]::UtcNow.ToString('o')}
SaveNew (Join-Path $root $metadata) $result
[pscustomobject]@{status=$result.status;metadata=$metadata;sha256=TaskDigest (Join-Path $root $metadata);protocols=$protocols;source_QA_calls=0;market_accounts=0}
