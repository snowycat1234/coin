$ErrorActionPreference='Stop'
Set-Location D:/codex/coin
function Hash([string]$p){$item=Get-Item -LiteralPath $p;if($item.Length -gt 2000000 -or $item.PSIsContainer){throw 'Small metadata only'};(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function Closed([string]$p,[string]$status){
 $r=Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -AsHashtable
 if($r.status -ne $status){throw 'Actual expected status'}
 $t=Get-Content -LiteralPath ('\\wsl.localhost\hpc_linux\home\xflops\coin-state\task-progress\task-'+$r.binding.task_id+'.json') -Raw|ConvertFrom-Json -AsHashtable
 if($t.status -ne 'completed' -or $t.exit_code -ne 0 -or $t.id -ne $r.binding.task_id){throw 'Real closed0 only'}
 return $r
}
$checker='docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD_INDEPENDENT_SOURCE_20261003_V2.py';$checkerSha='752c1015144bff614147ec445a4fcf62ff64f4d89b7a7074e93718c5ab9447d4'
$audit='reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_INDEPENDENT_AUDIT_20261003_V1.json'
$i=Closed $audit 'PASS_D035_TWO_VM_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR'
$code='docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD_ECONOMIC_COMPARISON_SOURCE_20261003_V3.py';$codeSha='a1481cdca624e4249923fc724ab40167d9968dc27161afa7e45f524f9f2285da'
if((Hash $checker) -ne $checkerSha -or $i.binding.checker_sha256 -ne $checkerSha -or (Hash $code) -ne $codeSha -or $i.completed_ledgers_verified -ne 2){throw 'Exact two-account accepted checker and held comparator'}
if((Hash 'docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD_COMPARISON_BINDING_FREEZER_SOURCE_20261003_V1.ps1') -ne (Hash $PSCommandPath)){throw 'Archive freezer before execution'}
$cases=[ordered]@{}
foreach($days in @(122,90)){
 $proto='protocols/VOL_MANAGED_HOLD_'+$days+'D_BYBIT_20261003_V1.json';$expected=$(if($days -eq 122){'9ec8e182a933bb3e16b32fb8dc9391431fcca6a2bab034e37903bd7c83aff2c5'}else{'5c95df3ae7800b5cb72879643b5bfbf8f9104f26c3a9ac927f94a7e701bbb136'})
 $path='reports/fast_research/VOL_MANAGED_HOLD_'+$days+'D_ACTUAL_20261003_V1.json';$a=Closed $path 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING'
 $h=Hash $path
 if((Hash $proto) -ne $expected -or $a.binding.protocol_sha256 -ne $expected -or $a.completed_ledgers -ne 1 -or $i.binding.actual_reports['/mnt/d/codex/coin/'+$path] -ne $h){throw 'Exact independently closed new account'}
 $cases['CONT'+$days]=@{protocol=@{path=$proto;sha256=$expected};actual=@{path=$path;sha256=$h;task_id=$a.binding.task_id}}
}
$v=@{comparator_sha256=$codeSha;audit=@{path=$audit;sha256=Hash $audit;task_id=$i.binding.task_id};cases=$cases;old_market_or_QA_replayed=$false}
$dest='D:/codex/coin/protocols/VOL_MANAGED_HOLD_TWO_PERIOD_COMPARISON_BINDING_20261003_V1.json'
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($v|ConvertTo-Json -Depth 20)+[Environment]::NewLine)
$fs=[IO.File]::Open($dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write);try{$fs.Write($bytes,0,$bytes.Length)}finally{$fs.Dispose()}
@{path=$dest;sha256=Hash $dest;closed_new_accounts=2}|ConvertTo-Json