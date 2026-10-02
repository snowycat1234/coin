$ErrorActionPreference='Stop'
Set-Location D:/codex/coin
function Hash([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function Closed([string]$p,[string]$status){
 $r=Get-Content -LiteralPath $p -Raw|ConvertFrom-Json -AsHashtable
 if($r.status -ne $status){throw 'actual accepted status'}
 $t=Get-Content -LiteralPath ('\\wsl.localhost\hpc_linux\home\xflops\coin-state\task-progress\task-'+$r.binding.task_id+'.json') -Raw|ConvertFrom-Json -AsHashtable
 if($t.status -ne 'completed' -or $t.exit_code -ne 0 -or $t.id -ne $r.binding.task_id){throw 'real closed0 only'}
 return $r
}
$actual='reports/fast_research/VOL_MANAGED_HOLD_547D_ACTUAL_20261003_V1.json'
$a=Closed $actual 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING'
if((Hash $actual) -ne 'b56cb8c2ddaf87487acf5e417301135474b982f7cd1dd8572886dea699c4ece6'){throw 'exact actual receipt'}
$audit='reports/fast_research/VOL_MANAGED_HOLD_547D_INDEPENDENT_AUDIT_20261003_V1.json'
$i=Closed $audit 'PASS_D034_SINGLE_VM_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR'
$proto='protocols/VOL_MANAGED_HOLD_547D_BYBIT_20261003_V2.json'
$psha='d60d7f0364a93e0918e1fe71f3c44d166a1a9c073e76dc0898e3fce09fa83303'
$c='docs/archive/VOL_MANAGED_HOLD_547D_ECONOMIC_COMPARISON_SOURCE_20261003_V2.py'
$csha='6e7bc5d00c21127df860f9c443d497e468f894402c7af88bfd70db4c451c7309'
if((Hash $proto) -ne $psha -or (Hash $c) -ne $csha -or $i.actual_report_sha256 -ne (Hash $actual)){throw 'exact protocol/comparator/audit parent'}
if((Hash 'docs/archive/VOL_MANAGED_HOLD_547D_COMPARISON_BINDING_FREEZER_SOURCE_20261003_V1.ps1') -ne (Hash $PSCommandPath)){throw 'archive freezer first'}
$v=@{comparator_sha256=$csha;protocol=@{path=$proto;sha256=$psha};actual=@{path=$actual;sha256=Hash $actual;task_id=$a.binding.task_id};audit=@{path=$audit;sha256=Hash $audit;task_id=$i.binding.task_id}}
$out='protocols/VOL_MANAGED_HOLD_547D_COMPARISON_BINDING_20261003_V1.json'
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($v|ConvertTo-Json -Depth 20)+[Environment]::NewLine)
$fs=[IO.File]::Open((Join-Path (Get-Location) $out),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write);try{$fs.Write($bytes,0,$bytes.Length)}finally{$fs.Dispose()}
@{path=$out;sha256=Hash $out;actual_sha256=Hash $actual;audit_sha256=Hash $audit}|ConvertTo-Json