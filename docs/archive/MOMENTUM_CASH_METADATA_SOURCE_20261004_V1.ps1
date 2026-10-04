param(
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedTargetSHA256,
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedPortfolioSHA256,
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedCheckerSHA256,
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedComparerSHA256,
 [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{32}$')][string]$MetadataTaskId
)
$ErrorActionPreference='Stop'
$root='D:\codex\coin';$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state'
$parent='1459b2d17cc669a736e2caebf90cd2734c82a835'
$adapter='scripts/investment/momentum_cash_pool_target.py'
$strategy='COIN_PAST30_ABSOLUTE_MOMENTUM_LONG_CASH_USDM_CONFIGURED_POOL_ADAPTER'
$signal='PAST30_POSITIVE_ABSOLUTE_RETURN_LONG_OR_CASH'
$archive='docs/archive/MOMENTUM_CASH_METADATA_SOURCE_20261004_V1.ps1'
$metadata='reports/fast_research/MOMENTUM_CASH_INPUT_BINDING_20261004_V1.json'
function TaskDigest($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function StatePath($p){if(-not $p.StartsWith('/home/xflops/coin-state/') -or $p -match '(^|/)\.\.(/|$)'){throw 'Only exact STATE metadata'};Join-Path $state $p.Substring(24)}
function MetaPath($p){if($p.StartsWith('/home/xflops/coin-state/')){return StatePath $p};if($p.StartsWith('/mnt/d/codex/coin/')){$p=$p.Substring(18)};if([IO.Path]::IsPathRooted($p) -or $p -match '(^|[/\\])\.\.([/\\]|$)' -or $p -eq 'state/dataset_lock.json'){throw 'Public ROOT or STATE metadata only'};Join-Path $root $p}
function ReadSmall($p,$sha){$f=Get-Item -LiteralPath $p;if($f.Length -gt 2000000 -or $f.LinkType){throw 'Small ordinary JSON only'};if($sha -and (TaskDigest $p) -ne $sha){throw ('Exact metadata SHA '+$p)};Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
function Closed($id){if($id -notmatch '^[0-9a-f]{32}$'){throw 'Actual task identity'};$p=Join-Path $state ('task-progress/task-'+$id+'.json');$t=ReadSmall $p '';if($t.id -ne $id -or $t.status -ne 'completed' -or $t.exit_code -ne 0 -or -not $t.ended_at){throw 'Actual closed0 prerequisite'};@{path='/home/xflops/coin-state/task-progress/task-'+$id+'.json';sha256=TaskDigest $p;task=$t}}
function SaveNew($p,$value){if(Test-Path -LiteralPath $p){throw ('Existing output '+$p)};[IO.File]::WriteAllText($p,($value|ConvertTo-Json -Depth 40)+"`n",[Text.UTF8Encoding]::new($false))}
$rules=[ordered]@{
 timeframe_minutes=1440;completed_daily_eligibility_bars=200;momentum_completed_daily_return_days=30
 entry_predicate='CURRENT_COMPLETED_CLOSE_GT_COMPLETED_CLOSE_30_DAYS_EARLIER'
 exit_predicate='HELD_LONG_AND_CURRENT_COMPLETED_CLOSE_LE_COMPLETED_CLOSE_30_DAYS_EARLIER'
 equal_policy='FLAT_ENTRY_BLOCKED_HELD_LONG_EXIT';short_entries_allowed=$false;direction_is_constant=$false
 close_then_wait_next_daily_decision_to_reenter=$true;past_covariance_daily_returns=30;annual_volatility_target=0.10
 absolute_target_per_asset=0.3;gross_target_cap=0.6;raw_allocation='EQUAL_SHARE_OF_0.6_GROSS_TO_CONFIGURED_ELIGIBLE_MEMBERS'
 inactive_signal_budget_redistributed=$false;allocation='EQUAL';risk_scaling='ORIGINAL_SIGNED_COVARIANCE_10_PERCENT_SCALE_DOWN_ONLY'
 fresh_flat_each_window=$true;missing_or_exited_member_state='RESET_FLAT_KEEP_SYMBOL_IDENTITY'
 SMA_alpha_or_original_Jesse_hooks_used=$false;public_momentum_strategy_replicated=$false
 native_Jesse_or_Bybit_execution_replicated=$false;funding_rates_used_for_signal=$false
 daily_availability='EXCLUSIVE_UTC_DAY_CLOSE_PROXY_NOT_PUBLICATION_CERTIFIED'
}
$parameters=@{completed_days=30;threshold=0;entry='LAST_COMPLETED_CLOSE_GT_30D_PRIOR_CLOSE';exit='HELD_LONG_AND_LAST_COMPLETED_CLOSE_LE_30D_PRIOR_CLOSE';inactive_raw_budget_redistributed=$false}
$cases=@(
 @{id='SEPNOV91';stem='MULTI_ASSET_CONTINUOUS_91D_TEN_EQUAL_20261004_V1';days=91;start=1725148800000000L;end=1733011200000000L;parent_sha='25fdf0ab7ae6fe1cfd1a01f13800b3360146748d4bfc23395c6c6485428384c9';actual_sha='cfa3e3b6aac8643b7ff3f3fd2ac325dbd75f16cb4d0c83d41984a0b04f70e3a1';task='e535a25117c14b119d5610fcaa5d203f';owner='/home/xflops/coin-state/d055-continuous-ten-equal-20261004-v1';rb_sha='78306e59477f7e1eed028396dbbcc8c76c4fad92f61158d9381684a5081e8bd2';manifest_sha='847d8a6e561d782ae641d492697ee03fd7b3ba2eda65298e5d0f02cb0c7b1e50';new_owner='d057-momentum-cash-sep-nov-20261004-v1'}
 @{id='DECFEB90';stem='MULTI_ASSET_WINTER_TEN_EQUAL_20261004_V3';days=90;start=1733011200000000L;end=1740787200000000L;parent_sha='9ddc2928df55e4ec835de398943fce20834a22495bf5bc8284f7363a4b92e3dc';actual_sha='bc0b50f77837d400874f6fa133e5656748e62c6d93eb798ac3a6198a189b8f70';task='9be98723fd944f8fbb49e4f479955e2e';owner='/home/xflops/coin-state/d056-winter-ten-equal-20261004-v3';rb_sha='5a31a6017ce5ddc9d7474442a9eb43bfa1a376b0695b52db0cdaf887ced7bb64';manifest_sha='56f1eb1b768e14d4c67198156732c1d4a22e6a901e980c24ebee9f20bbf86193';new_owner='d057-momentum-cash-dec-feb-20261004-v1'}
)
if((git -C $root rev-parse HEAD) -ne $parent -or (Test-Path -LiteralPath (Join-Path $root $metadata))){throw 'Accepted parent and new metadata output required'}
$updates=@{'scripts/investment/multi_asset_data.py'='c604395e109ccd54a3864e1ebf2cdb448feeb0e1116860f204695409876acfd3';'scripts/investment/multi_asset_portfolio.py'=$ExpectedPortfolioSHA256}
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
 $new.strategy=$strategy;$new.signal=$signal;$new.strategy_rules=$rules;$new.momentum_parameters=$parameters
 $new.experiment_id='D057-MOMENTUM-CASH-'+$case.id+'-20261004'
 $new.independent_reference_pre_market_sha256=$ExpectedCheckerSHA256;$new.economic_comparer_pre_market_sha256=$ExpectedComparerSHA256
 $new.budget=@{owned_bytes=250000000;wall_seconds=1800;peak_RSS_bytes=3000000000}
 $new.research_budget=@{models_fit=0;HPO=0;new_actual_accounts=8;new_independent_accounts=8;total_new_STATE_bytes=800000000;new_recipes=1;test_owned_bytes=10000000;test_wall_seconds=1200;test_peak_RSS_bytes=1000000000;metadata_owned_bytes=5000000;financial_owned_bytes_per_run=100000;financial_wall_seconds=1800;financial_peak_RSS_bytes=1500000000}
 $new.question='Does fixed past30 positive absolute-return long/cash direction improve saved equal-HOLD money/risk quality in both unchanged seen quarters?'
 $new.success_rule='Eight new true complete or truthfully halted calendars and independent accounting; compare saved same-quarter equal HOLD without replay or positive-profit requirement.'
 $new.created_utc=[DateTimeOffset]::UtcNow.ToString('o')
 $out='protocols/MOMENTUM_CASH_'+$case.id+'_20261004_V1.json';$actual='reports/fast_research/MOMENTUM_CASH_'+$case.id+'_20261004_V1.json'
 if((Test-Path -LiteralPath (Join-Path $root $out)) -or (Test-Path -LiteralPath (Join-Path $root $actual)) -or (Test-Path -LiteralPath (Join-Path $state $case.new_owner))){throw 'Exclusive new experiment; failed attempt needs a new declared identity'}
 $prepared[$case.id]=@{path=$out;spec=$new;run_dir='/home/xflops/coin-state/'+$case.new_owner;output_path=$actual;required_cli_pool_id='LIQUIDITY_TEN';required_cases=4}
 $proofs[$case.id]=@{protocol=@{path=$pp;sha256=$case.parent_sha};actual=@{path=$ap;sha256=$case.actual_sha};closed_task=$t;owner=$case.owner;run_binding_sha256=$case.rb_sha;manifest=$p.data_manifest;accepted_capabilities=$capProofs;warmup_scope='Original accepted70 daily and existing necessary minute-derived days;200-contiguous-day eligibility remains original loader guard;not new rows QA'}
}
if((TaskDigest (Join-Path $root 'state/dataset_lock.json')) -ne '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'){throw 'Private policy streaming SHA only'}
if(Test-Path -LiteralPath (Join-Path $root $archive)){if((TaskDigest $PSCommandPath) -ne (TaskDigest (Join-Path $root $archive))){throw 'Existing helper archive differs'}}else{Copy-Item -LiteralPath $PSCommandPath -Destination (Join-Path $root $archive)}
$protocols=@{};foreach($id in $prepared.Keys){$v=$prepared[$id];SaveNew (Join-Path $root $v.path) $v.spec;$protocols[$id]=@{path=$v.path;sha256=TaskDigest (Join-Path $root $v.path);run_dir=$v.run_dir;output_path=$v.output_path;required_cli_pool_id=$v.required_cli_pool_id;required_cases=4}}
$result=@{status='READY_D057_TWO_UNCHANGED_SOURCE_QUARTERS_MOMENTUM_CASH_PROTOCOLS_NOT_MARKET_RESULTS';task_id=$MetadataTaskId;own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED';parent_commit=$parent;metadata_source=@{path=$archive;sha256=TaskDigest $PSCommandPath};protocols=$protocols;accepted_saved_references=$proofs;new_downloads=0;source_QA_calls=0;market_accounts=0;financial_calls=0;models_fit=0;HPO=0;funding_unit_certified=$false;native_certified=$false;candidate='NONE';investment='CASH';long_term_APR='NOT_EVALUABLE';source_payloads_read=0;private_lock_body_read=$false;created_utc=[DateTimeOffset]::UtcNow.ToString('o')}
SaveNew (Join-Path $root $metadata) $result
[pscustomobject]@{status=$result.status;metadata=$metadata;sha256=TaskDigest (Join-Path $root $metadata);protocols=$protocols;source_QA_calls=0;market_accounts=0}
