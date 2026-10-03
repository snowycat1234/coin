param([ValidateSet('SourceQA','Root')][string]$Phase)
$ErrorActionPreference='Stop';$root='D:/codex/coin';$enc=[Text.UTF8Encoding]::new($false)
function Digest([string]$Name){(Get-FileHash -LiteralPath (Join-Path $root $Name) -Algorithm SHA256).Hash.ToLowerInvariant()}
function ReadJson([string]$Name){Get-Content (Join-Path $root $Name) -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
function WriteNew([string]$Name,$Value){$p=Join-Path $root $Name;if(Test-Path -LiteralPath $p){throw "Exclusive destination $Name"};[IO.File]::WriteAllText($p,($Value|ConvertTo-Json -Depth 50)+"`n",$enc)}
function Ref([string]$Name){$v=ReadJson $Name;return [ordered]@{path=$Name;sha256=(Digest $Name);task_id=$v.binding.task_id;required_status=$v.status}}
$sourcePath='reports/fast_research/PERPETUAL_303_SOURCE_ACTUAL_20261003_V1.json';$source=ReadJson $sourcePath
if($source.status -ne 'PASS_D045_94_HISTORY_FORMAT_54_REUSED_40_NEW_PENDING_INDEPENDENT_QA' -or $source.completed_files -ne 94 -or $source.archive_bodies_downloaded -ne 40){throw '94 producer not complete'}
$specPath='protocols/PERPETUAL_303_SOURCE_20261003_V1.json';$spec=ReadJson $specPath;$hashes=[ordered]@{}
foreach($p in $spec.frozen_sources.Keys){if((Digest $p) -ne $spec.frozen_sources[$p]){throw "Frozen dependency $p"};$hashes[$p]=$spec.frozen_sources[$p]}
foreach($p in @($sourcePath,$specPath,'scripts/investment/audit_perpetual_303_source.py','docs/archive/PERPETUAL_303_SOURCE_INDEPENDENT_AUDITOR_20261003_V1.py','docs/archive/PERPETUAL_303_SOURCE_ACCEPTANCE_FREEZER_20261003_V1.ps1')){$hashes[$p]=Digest $p}
$qaPath='reports/fast_research/PERPETUAL_303_SOURCE_INDEPENDENT_20261003_V1.json'
if($Phase -eq 'SourceQA'){
 $owners=@();foreach($row in @(@('reports/fast_research/PERPETUAL_HISTORY_SOURCE_ACTUAL_20261003_V1.json','/home/xflops/coin-state/d042-perpetual-history-source-20261003-v1',1),@('reports/fast_research/PERPETUAL_TRADE_SOURCE_ACTUAL_20261003_V1.json','/home/xflops/coin-state/perpetual-trade-source-actual-20261003-v1',0),@($sourcePath,$spec.run_dir,0))){$r=Ref $row[0];$r.run_dir=$row[1];$r.exit_code=$row[2];$owners+=,$r}
 $caps=@();foreach($row in @(@('reports/fast_research/PERPETUAL_213_SOURCE_INDEPENDENT_20261003_V1.json','reports/fast_research/PERPETUAL_213_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json'),@('reports/fast_research/PERPETUAL_TRADE_SOURCE_INDEPENDENT_QA_20261003_V2.json','reports/fast_research/PERPETUAL_TRADE_SOURCE_ROOT_ACCEPTANCE_20261003_V4.json'))){$caps+=,@{qa=(Ref $row[0]);root=(Ref $row[1])};foreach($p in $row){$hashes[$p]=Digest $p}}
 $plan=[ordered]@{ready_to_execute=$true;checker_sha256=(Digest 'scripts/investment/audit_perpetual_303_source.py');source_spec=@{path=$specPath;sha256=(Digest $specPath);required_contract=$spec.contract_id};actual_source=(Ref $sourcePath);owner_bindings=$owners;accepted_capabilities=$caps;frozen_sources=$hashes;budgets=@{peak_RSS_bytes=1000000000;wall_seconds=1200;new_owned_bytes=5000000};created_utc=[datetime]::UtcNow.ToString('o')}
 $dest='protocols/PERPETUAL_303_SOURCE_INDEPENDENT_BINDING_20261003_V1.json';WriteNew $dest $plan
 $newrun='/home/xflops/coin-state/d045-perpetual-303-independent-20261003-v1'
 & wsl.exe -d hpc_linux -- bash /mnt/d/codex/coin/scripts/bounded.sh mkdir -- $newrun
 if($LASTEXITCODE -ne 0){throw 'Exclusive STATE creation failed'}
 & wsl.exe -d hpc_linux -- bash /mnt/d/codex/coin/scripts/bounded.sh cp -- ('/mnt/d/codex/coin/'+$dest) ($newrun+'/ACTUAL_BINDING.json')
 if($LASTEXITCODE -ne 0){throw 'QA binding copy failed'}
}else{
 $qa=ReadJson $qaPath;if($qa.status -ne 'PASS_D045_94_SOURCE_COVERAGE_70_FIRST_QA_24_ACCEPTED_REUSE_NOT_UNIT_OR_ECONOMICS' -or $qa.first_independent_QA_files -ne 70 -or $qa.reused_accepted_QA_files -ne 24){throw 'Independent70+24 not accepted'}
 foreach($p in @($qaPath,'protocols/PERPETUAL_303_SOURCE_INDEPENDENT_BINDING_20261003_V1.json','scripts/investment/accept_perpetual_303_source.py','docs/archive/PERPETUAL_303_SOURCE_ROOT_ACCEPTANCE_SOURCE_20261003_V1.py')){$hashes[$p]=Digest $p}
 $roles=[ordered]@{SOURCE=(Ref $sourcePath);INDEPENDENT=(Ref $qaPath)}
 $plan=[ordered]@{ready_to_execute=$true;checker_sha256=(Digest 'scripts/investment/accept_perpetual_303_source.py');source_hashes=$hashes;source_protocol=@{path=$specPath;sha256=(Digest $specPath);required_contract=$spec.contract_id};roles=$roles;run_dir='/home/xflops/coin-state/d045-perpetual-303-source-root-20261003-v1';budgets=@{wall_seconds=120;peak_RSS_bytes=1000000000;new_owned_bytes=5000000};created_utc=[datetime]::UtcNow.ToString('o')}
 $dest='protocols/PERPETUAL_303_SOURCE_ROOT_BINDING_20261003_V1.json';WriteNew $dest $plan
}
[pscustomobject]@{phase=$Phase;path=$dest;sha256=(Digest $dest)}|ConvertTo-Json
