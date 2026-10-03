$ErrorActionPreference='Stop';$root='D:/codex/coin';$enc=[Text.UTF8Encoding]::new($false)
function Digest([string]$p){(Get-FileHash -LiteralPath (Join-Path $root $p) -Algorithm SHA256).Hash.ToLowerInvariant()}
function ReadJson([string]$p){Get-Content (Join-Path $root $p) -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
$sources=[ordered]@{}
foreach($row in @(@('213D','reports/fast_research/PERPETUAL_213_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json','795667026b7eb50ab08f1c5b07254eb2002591549b792aa4685439a2d82cc823','reports/fast_research/PERPETUAL_213D_INPUT_BINDING_20261003_V1.json','904e05176d8332f07c500047baf5ef8a26925f70ed5d4b8b58e3d45fc4da7553'),@('122D90D','reports/fast_research/PERPETUAL_TRADE_SOURCE_ROOT_ACCEPTANCE_20261003_V4.json','f8f6d2e49c320ecc5f61506ffd291ac1c94af0b80803baa6b8e4210741a1f95d','reports/fast_research/LONG_SHORT_USDM_INPUT_BINDING_20261003_V1.json','f7b3e8eb724b8196280ef872454b36297171b5f487bea94410dc547eb846d045'))){
  if((Digest $row[1]) -ne $row[2] -or (Digest $row[3]) -ne $row[4]){throw 'Original source pins changed'}
  $sources[$row[0]]=@{root=@{path=$row[1];sha256=$row[2];required_status=(ReadJson $row[1]).status};manifest=@{path=$row[3];sha256=$row[4];required_status=(ReadJson $row[3]).status}}
}
$hashes=[ordered]@{}
foreach($p in @('scripts/investment/perpetual_hold_source_reuse.py','docs/archive/PERPETUAL_HOLD_SOURCE_REUSE_SOURCE_20261003_V1.py','docs/archive/PERPETUAL_HOLD_SOURCE_REUSE_FREEZER_20261003_V1.ps1','docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py','state/dataset_lock.json')){$hashes[$p]=Digest $p}
foreach($s in $sources.Values){foreach($r in @($s.root,$s.manifest)){$hashes[$r.path]=$r.sha256}}
$plan=[ordered]@{ready_to_execute=$true;run_dir='/home/xflops/coin-state/d044-perpetual-hold-source-reuse-20261003-v1';source_hashes=$hashes;sources=$sources;combined_output='reports/fast_research/PERPETUAL_HOLD_INPUT_BINDING_20261003_V1.json';output='reports/fast_research/PERPETUAL_HOLD_SOURCE_REUSE_20261003_V1.json';created_utc=[datetime]::UtcNow.ToString('o')}
$dest='protocols/PERPETUAL_HOLD_SOURCE_REUSE_BINDING_20261003_V1.json';if(Test-Path $dest){throw 'Exclusive source reuse protocol'}
[IO.File]::WriteAllText((Join-Path $root $dest),($plan|ConvertTo-Json -Depth 30)+"`n",$enc)
[pscustomobject]@{path=$dest;sha256=(Digest $dest)}|ConvertTo-Json
