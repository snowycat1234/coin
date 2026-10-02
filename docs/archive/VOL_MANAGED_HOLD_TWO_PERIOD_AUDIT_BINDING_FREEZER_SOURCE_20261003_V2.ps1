# UNRUN D035: small metadata only; root archives this exact source before invocation.
$ErrorActionPreference='Stop'
if($PSVersionTable.PSVersion.Major -lt 7){throw 'Existing PowerShell7 required'}
Set-Location 'D:/codex/coin'
$Root='D:\codex\coin\';$State='\\wsl.localhost\hpc_linux\home\xflops\coin-state\'
$Archive='docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD_AUDIT_BINDING_FREEZER_SOURCE_20261003_V2.ps1'
$Checker='docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD_INDEPENDENT_SOURCE_20261003_V3.py'
$CheckerSha='0e4e4bcdb042e5d6818f471ae3c551896f0787f94aac04783e9c05f729f27bd2'
$Entry='scripts/investment/vol_managed_two_period_adapter.py'
$EntrySha='594b1a16117221fe2c99494199a01df2e4c2403066f82314ce4b29bdcb28d4fe'
$Tiny='reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_BOUNDARY_TINY_20261003_V1.json'
$TinySha='d891ec44790d6291103b4bbcbca20e73751a68d9e7e4f9349e719cd91ffa045f'
$TinyTask='65a6182e63c847d885cd4b8359c11f2e'
function Native([string]$p){
 if($p.StartsWith('/home/xflops/coin-state/')){return $State+$p.Substring(24).Replace('/','\')}
 if($p.StartsWith('/mnt/d/codex/coin/')){return $Root+$p.Substring(18).Replace('/','\')}
 return [IO.Path]::GetFullPath($p)
}
function Hash([string]$p){
 $f=Get-Item -LiteralPath (Native $p)
 if($f.PSIsContainer -or $f.Length -gt 2000000 -or ($f.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $f.Extension -notin @('.json','.py','.ps1') -or -not ($f.FullName.StartsWith($Root,[StringComparison]::OrdinalIgnoreCase) -or $f.FullName.StartsWith($State,[StringComparison]::OrdinalIgnoreCase))){throw 'Ordinary small metadata/code only; no market hash or read'}
 return (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Read([string]$p){$null=Hash $p;Get-Content -LiteralPath (Native $p) -Raw|ConvertFrom-Json -AsHashtable}
function Closed([string]$p,[string]$status){
 $r=Read $p;$id=$r.binding.task_id
 if($r.status -ne $status -or $id -notmatch '^[0-9a-f]{32}$'){throw 'Exact report status and real task identity required'}
 $t=Read ($State+'task-progress\task-'+$id+'.json')
 if($t.id -ne $id -or $t.status -ne 'completed' -or ($t.exit_code -isnot [int] -and $t.exit_code -isnot [long]) -or $t.exit_code -ne 0 -or $t.pid -le 0 -or $t.start_ticks -le 0){throw 'Actual completed0 pid/start ticks only'}
 return $r
}
$FactorySha=Hash $PSCommandPath
if((Hash $Archive) -ne $FactorySha -or (Hash $Checker) -ne $CheckerSha -or (Hash $Entry) -ne $EntrySha){throw 'Archive exact factory/checker and held route first'}
$t=Closed $Tiny 'PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT'
if((Hash $Tiny) -ne $TinySha -or $t.binding.task_id -ne $TinyTask){throw 'Exact one shared new tiny completed0'}
$Profiles=@(
 @{period='122D';fold='CONT122';start='2025-08-01';end='2025-12-01';proto='protocols/VOL_MANAGED_HOLD_122D_BYBIT_20261003_V1.json';psha='9ec8e182a933bb3e16b32fb8dc9391431fcca6a2bab034e37903bd7c83aff2c5'},
 @{period='90D';fold='CONT90';start='2025-12-01';end='2026-03-01';proto='protocols/VOL_MANAGED_HOLD_90D_BYBIT_20261003_V1.json';psha='5c95df3ae7800b5cb72879643b5bfbf8f9104f26c3a9ac927f94a7e701bbb136'})
$Cases=@()
foreach($p in $Profiles){
 $s=Read $p.proto
 if((Hash $p.proto) -ne $p.psha -or $s.strategy_ids.Count -ne 1 -or $s.strategy_ids[0] -ne 'VOL_MANAGED_BUY_AND_HOLD' -or $s.planned_ledgers -ne 1 -or $s.folds.Count -ne 1 -or $s.folds[0].id -ne $p.fold -or $s.folds[0].period_start -ne $p.start -or $s.folds[0].period_end_exclusive -ne $p.end -or $s.production_entrypoint -ne $Entry -or $s.frozen_sources[$Entry] -ne $EntrySha -or $s.required_smoke_receipt -ne $Tiny){throw 'Exact separate fixed new sole VM child protocol'}
 $expected='reports/fast_research/VOL_MANAGED_HOLD_'+$p.period.Substring(0,$p.period.Length-1)+'D_ACTUAL_20261003_V1.json'
 if($s.research_output_path -ne $expected){throw 'Exact immutable child actual path'}
 $a=Closed $expected 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING'
 if($a.binding.protocol_sha256 -ne $p.psha -or $a.completed_ledgers -ne 1 -or -not $a.all_planned_ledgers_complete -or -not $a.source_bytes_unchanged -or $a.accepted_smoke_sha256 -ne $TinySha -or $a.run_dir -ne $s.research_run_dir -or $a.folds.Count -ne 1 -or $a.folds[0].fold -ne $p.fold -or $a.folds[0].results.Count -ne 1 -or $a.folds[0].results[0].strategy -ne 'VOL_MANAGED_BUY_AND_HOLD' -or $a.folds[0].results[0].spread_bps -ne 8 -or $a.market_models_fit -ne 0 -or $a.orders_sent -ne 0 -or $a.locked_consumed){throw 'One complete new VM36bp actual bound to child protocol/smoke'}
 $Cases+=@{period=$p.period;protocol_path='/mnt/d/codex/coin/'+$p.proto;protocol_sha256=$p.psha;actual_report='/mnt/d/codex/coin/'+$expected;actual_report_sha256=Hash $expected;actual_task_id=$a.binding.task_id;production_entrypoint=$Entry}
}
# Legacy153/151day source receipts have no task IDs; the numerical auditor binds metadata, not reconstructed tasks.
$v=@{cases=$Cases;checker_sha256=$CheckerSha;smoke_sha256=$TinySha;smoke_task_id=$TinyTask;maximum_independent_RSS_bytes=3500000000;maximum_wall_seconds=600;binding_factory_sha256=$FactorySha}
$Out=$State+'d035-independent-20261003-v2'
if(Test-Path -LiteralPath $Out){throw 'Exclusive new independent STATE required'}
New-Item -ItemType Directory -Path $Out|Out-Null
$Path=Join-Path $Out 'ACTUAL_BINDING.json';$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($v|ConvertTo-Json -Depth 20)+[Environment]::NewLine)
$f=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write);try{$f.Write($bytes,0,$bytes.Length)}finally{$f.Dispose()}
@{path='/home/xflops/coin-state/d035-independent-20261003-v2/ACTUAL_BINDING.json';sha256=Hash $Path;cases=$Cases;checker_sha256=$CheckerSha;binding_factory_sha256=$FactorySha}|ConvertTo-Json -Depth 20
