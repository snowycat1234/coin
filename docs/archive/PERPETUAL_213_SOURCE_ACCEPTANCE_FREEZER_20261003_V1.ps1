param([ValidateSet('SourceQA','Root')][string]$Phase)
$ErrorActionPreference='Stop'
$root='D:/codex/coin'; $enc=[Text.UTF8Encoding]::new($false)
function Digest([string]$Name) { (Get-FileHash -LiteralPath (Join-Path $root $Name) -Algorithm SHA256).Hash.ToLowerInvariant() }
function ReadJson([string]$Name) { Get-Content (Join-Path $root $Name) -Raw | ConvertFrom-Json -AsHashtable -DateKind String }
function WriteNew([string]$Name,$Value) { $p=Join-Path $root $Name; if(Test-Path -LiteralPath $p) { throw "Exclusive destination exists: $Name" }; [IO.File]::WriteAllText($p,($Value|ConvertTo-Json -Depth 50)+"`n",$enc) }
$sourcePath='reports/fast_research/PERPETUAL_213_SOURCE_ACTUAL_20261003_V1.json'
$source=ReadJson $sourcePath
if($source.status -ne 'PASS_D043_72_HISTORY_FORMAT_PENDING_FULL_INDEPENDENT_QA' -or $source.completed_files -ne 72 -or $source.archive_bodies_downloaded -ne 21) { throw 'New72 producer not fully passed' }
$specPath='protocols/PERPETUAL_213_SOURCE_20261003_V1.json'; $spec=ReadJson $specPath
$hashes=[ordered]@{}
foreach($p in $spec.frozen_sources.Keys) { if((Digest $p) -ne $spec.frozen_sources[$p]) { throw "Frozen source changed: $p" }; $hashes[$p]=$spec.frozen_sources[$p] }
foreach($p in @($sourcePath,$specPath,'scripts/investment/audit_perpetual_213_source.py','docs/archive/PERPETUAL_213_SOURCE_INDEPENDENT_AUDITOR_20261003_V1.py','docs/archive/PERPETUAL_213_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py','docs/archive/PERPETUAL_213_SOURCE_ACCEPTANCE_FREEZER_20261003_V1.ps1','scripts/investment/accept_perpetual_213_source.py')) { $hashes[$p]=Digest $p }
$parentPath=$spec.parent_source_path; $parent=ReadJson $parentPath
$qaPath='reports/fast_research/PERPETUAL_213_SOURCE_INDEPENDENT_20261003_V1.json'
if($Phase -eq 'SourceQA') {
  $runner='scripts/investment/audit_perpetual_213_source.py'
  $helper='docs/archive/PERPETUAL_213_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py'
  $newrun='/home/xflops/coin-state/d043-perpetual-213-independent-20261003-v1'
  $owners=@(
    [ordered]@{run_dir='/home/xflops/coin-state/d042-perpetual-history-source-20261003-v1';report_path=$parentPath;report_sha256=(Digest $parentPath);task_id=$parent.binding.task_id;exit_code=1;required_status='FAIL_D042_HISTORY_SOURCE'},
    [ordered]@{run_dir=$spec.run_dir;report_path=$sourcePath;report_sha256=(Digest $sourcePath);task_id=$source.binding.task_id;exit_code=0;required_status='PASS_D043_72_HISTORY_FORMAT_PENDING_FULL_INDEPENDENT_QA'})
  $plan=[ordered]@{ready_to_execute=$true;checker_sha256=(Digest $runner);helper=@{path=$helper;sha256=(Digest $helper)};
    source_spec=@{path=$specPath;sha256=(Digest $specPath);required_contract='D043_FIXED_213D_MIXED_OWNER_OFFICIAL_SOURCE_V1'};
    actual_source=@{path=$sourcePath;sha256=(Digest $sourcePath);task_id=$source.binding.task_id;required_status='PASS_D043_72_HISTORY_FORMAT_PENDING_FULL_INDEPENDENT_QA'};
    owner_bindings=$owners;frozen_sources=$hashes;budgets=@{peak_RSS_bytes=1000000000;wall_seconds=1200;new_owned_bytes=5000000};created_utc=[datetime]::UtcNow.ToString('o')}
  $dest='protocols/PERPETUAL_213_SOURCE_INDEPENDENT_BINDING_20261003_V1.json'; WriteNew $dest $plan
  & wsl.exe -d hpc_linux -- bash /mnt/d/codex/coin/scripts/bounded.sh mkdir -- $newrun
  if($LASTEXITCODE -ne 0) { throw 'Exclusive QA STATE creation failed' }
  & wsl.exe -d hpc_linux -- bash /mnt/d/codex/coin/scripts/bounded.sh cp -- (('/mnt/d/codex/coin/'+$dest)) ($newrun+'/ACTUAL_BINDING.json')
  if($LASTEXITCODE -ne 0) { throw 'Exact QA binding copy failed' }
} else {
  $qa=ReadJson $qaPath
  if($qa.status -ne 'PASS_D043_72_MIXED_OWNER_213D_USDM_FORMAT_CALENDAR_ONLY_NOT_UNIT_OR_ECONOMICS' -or $qa.completed_files_verified -ne 72) { throw 'All72 independent source not passed' }
  foreach($p in @($qaPath,'protocols/PERPETUAL_213_SOURCE_INDEPENDENT_BINDING_20261003_V1.json')) { $hashes[$p]=Digest $p }
  $roles=[ordered]@{}
  foreach($r in @(@('METADATA',$spec.metadata_path,'PASS_D042_148_OFFICIAL_HISTORY_METADATA_ONLY'),@('PRECEDING_FAILURE',$parentPath,'FAIL_D042_HISTORY_SOURCE'),@('SOURCE',$sourcePath,'PASS_D043_72_HISTORY_FORMAT_PENDING_FULL_INDEPENDENT_QA'),@('INDEPENDENT',$qaPath,'PASS_D043_72_MIXED_OWNER_213D_USDM_FORMAT_CALENDAR_ONLY_NOT_UNIT_OR_ECONOMICS'))) {
    $v=ReadJson $r[1];if($v.status -ne $r[2]) { throw "Wrong role status: $($r[0])" }
    $roles[$r[0]]=@{path=$r[1];sha256=(Digest $r[1]);task_id=$v.binding.task_id;status=$r[2]}
  }
  $plan=[ordered]@{ready_to_execute=$true;source_hashes=$hashes;roles=$roles;run_dir='/home/xflops/coin-state/d043-perpetual-213-source-root-20261003-v1';created_utc=[datetime]::UtcNow.ToString('o')}
  $dest='protocols/PERPETUAL_213_SOURCE_ROOT_BINDING_20261003_V1.json'; WriteNew $dest $plan
}
[pscustomobject]@{phase=$Phase;path=$dest;sha256=(Digest $dest)}|ConvertTo-Json
