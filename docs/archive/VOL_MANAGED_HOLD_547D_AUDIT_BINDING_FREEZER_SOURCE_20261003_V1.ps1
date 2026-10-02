$ErrorActionPreference='Stop'
Set-Location D:/codex/coin
function Hash([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function Closed([string]$p,[string]$status){
 $r=Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -AsHashtable
 if($r.status -ne $status){throw 'actual accepted report status'}
 $t=Get-Content -LiteralPath ('\\wsl.localhost\hpc_linux\home\xflops\coin-state\task-progress\task-'+$r.binding.task_id+'.json') -Raw|ConvertFrom-Json -AsHashtable
 if($t.status -ne 'completed' -or $t.exit_code -ne 0 -or $t.id -ne $r.binding.task_id){throw 'real closed0 only'}
 return $r
}
$actual='reports/fast_research/VOL_MANAGED_HOLD_547D_ACTUAL_20261003_V1.json'
$a=Closed $actual 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING'
$proto='protocols/VOL_MANAGED_HOLD_547D_BYBIT_20261003_V2.json'
$psha='d60d7f0364a93e0918e1fe71f3c44d166a1a9c073e76dc0898e3fce09fa83303'
if((Hash $proto) -ne $psha -or $a.binding.protocol_sha256 -ne $psha -or $a.completed_ledgers -ne 1){throw 'fixed single VM protocol'}
$tiny='reports/fast_research/VOL_MANAGED_HOLD_547D_BOUNDARY_TINY_20261003_V2.json'
$t=Closed $tiny 'PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT'
if((Hash $tiny) -ne 'e80ee18b778c5305377d8a66c1f84d94ba8bb3b30a19ab56fc3ca5005dc1130d'){throw 'exact tiny'}
$source='reports/fast_research/PUBLIC_LONG_547D_SOURCE_REUSE_20261003_V1.json'
$s=Closed $source 'PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_578D_CALENDAR'
if((Hash $source) -ne '64dc9474828b1707b21a7ed09b5719f202645cbc4ceb72007d9775d72d67fee2'){throw 'exact reused source'}
$checker='docs/archive/VOL_MANAGED_HOLD_547D_USED_INDEPENDENT_SOURCES_20261003_V1/audit.py'
$csha='942f006885a6e2cc5476f697b6368e586c30fe68b0344af55833aa8f4c808d78'
if((Hash $checker) -ne $csha){throw 'exact pre-read checker'}
if((Hash 'docs/archive/VOL_MANAGED_HOLD_547D_AUDIT_BINDING_FREEZER_SOURCE_20261003_V1.ps1') -ne (Hash $PSCommandPath)){throw 'archive freezer first'}
$out='\\wsl.localhost\hpc_linux\home\xflops\coin-state\d034-independent-20261003-v1'
if(Test-Path -LiteralPath $out){throw 'exclusive new STATE'}
New-Item -ItemType Directory -Path $out|Out-Null
$v=@{actual_report='/mnt/d/codex/coin/'+$actual;actual_report_sha256=Hash $actual;actual_task_id=$a.binding.task_id;protocol_path='/mnt/d/codex/coin/'+$proto;protocol_sha256=$psha;production_entrypoint='scripts/investment/public_long_vol_managed_adapter.py';smoke_sha256=Hash $tiny;smoke_task_id=$t.binding.task_id;source_receipt_sha256=Hash $source;source_task_id=$s.binding.task_id;checker_sha256=$csha;maximum_independent_RSS_bytes=3500000000;maximum_wall_seconds=600}
$path=Join-Path $out 'ACTUAL_BINDING.json';$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($v|ConvertTo-Json -Depth 20)+[Environment]::NewLine)
$fs=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write);try{$fs.Write($bytes,0,$bytes.Length)}finally{$fs.Dispose()}
@{path='/home/xflops/coin-state/d034-independent-20261003-v1/ACTUAL_BINDING.json';sha256=Hash $path;actual_sha256=Hash $actual}|ConvertTo-Json