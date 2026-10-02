param([Parameter(Mandatory=$true)][string]$Host122,[Parameter(Mandatory=$true)][string]$Host90)
$ErrorActionPreference='Stop'
$projectRoot='D:\codex\coin'; $linuxRoot='/mnt/d/codex/coin'
$work='/home/xflops/coin-state/test-d032-past-funding-exit-independent-audit-20261003-v1'
$archive='docs/archive/CARRY_PAST_FUNDING_EXIT_USED_INDEPENDENT_SOURCES_20261003_V1'
$binder='docs/archive/CARRY_PAST_FUNDING_EXIT_ACTUAL_AUDIT_BINDER_20261003_V1.ps1'
function Digest([string]$path){(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower()}
function WriteNew([string]$path,$value){
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($value|ConvertTo-Json -Depth 40)+"`n")
    $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew)
    try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
}
if((Digest $PSCommandPath) -ne (Digest (Join-Path $projectRoot $binder))){throw 'Binder source archive changed'}
New-Item -ItemType Directory -Path (Join-Path $projectRoot $archive) -ErrorAction Stop | Out-Null
& wsl.exe -d hpc_linux --cd $linuxRoot -- cp -- "$work/audit.py" "$work/gate_delta.py" "$work/PREPARED_STATIC_BINDING.json" "$linuxRoot/$archive/"
if($LASTEXITCODE -ne 0){throw 'Exact independent draft copy failed'}
$prepared=Get-Content -LiteralPath (Join-Path $projectRoot "$archive/PREPARED_STATIC_BINDING.json") -Raw | ConvertFrom-Json
if((Digest (Join-Path $projectRoot "$archive/audit.py")) -ne $prepared.checker_sha256 -or
   (Digest (Join-Path $projectRoot "$archive/gate_delta.py")) -ne $prepared.gate_delta_sha256){throw 'Static checker bytes changed'}
$bound=[ordered]@{status='FROZEN_AFTER_TWO_NEW_ACTUAL_CLOSED_EXIT0_BEFORE_UNIQUE_D032_AUDIT';
    protocol_path=$prepared.protocol_path;checker_sha256=$prepared.checker_sha256;gate_delta_sha256=$prepared.gate_delta_sha256;
    actuals=@();small_inputs=[ordered]@{};binder_source="$linuxRoot/$binder";binder_sha256=(Digest (Join-Path $projectRoot $binder));
    market_arrays_read=$false;old_controls_or_green_tests_repeated=$false}
foreach($property in $prepared.project_small_metadata_source_hashes.PSObject.Properties){
    $path=Join-Path $projectRoot $property.Name
    if((Digest $path) -ne $property.Value){throw "Frozen small dependency changed: $($property.Name)"}
    $bound.small_inputs["$linuxRoot/$($property.Name)"]=$property.Value
}
foreach($property in $prepared.reused_sources.PSObject.Properties){
    $row=$property.Value
    if((Digest (Join-Path $projectRoot $row.project_path)) -ne $row.sha256){throw 'Accepted independent reuse changed'}
    $bound[$property.Name]=$row.linux_path
    $bound[($property.Name -replace '_path$','_sha256')]=$row.sha256
    $bound.small_inputs[$row.linux_path]=$row.sha256
}
$hosts=@{'122D'=$Host122;'90D'=$Host90}
foreach($period in @('122D','90D')){
    $relative="reports/fast_research/CARRY_PAST_FUNDING_EXIT_${period}_ACTUAL_20261003_V1.json"
    $actual=Get-Content -LiteralPath (Join-Path $projectRoot $relative) -Raw | ConvertFrom-Json
    if($actual.period_id -ne $period -or $actual.status -ne $prepared.expected_actual_status -or
       $actual.binding.protocol_sha256 -ne $prepared.protocol_sha256){throw 'Actual report incomplete or wrong period/protocol'}
    $taskPath='/home/xflops/coin-state/task-progress/task-'+$actual.binding.task_id+'.json'
    $raw=& wsl.exe -d hpc_linux -- cat -- $taskPath
    if($LASTEXITCODE -ne 0){throw 'Actual task missing'}
    $task=($raw -join "`n")|ConvertFrom-Json
    if($task.id -ne $actual.binding.task_id -or $task.status -ne 'completed' -or $task.exit_code -ne 0){throw 'Actual not closed0'}
    $bound.actuals += [ordered]@{period=$period;actual_report_path=$relative;actual_report_sha256=(Digest (Join-Path $projectRoot $relative));actual_task_id=$task.id;actual_host_result=$hosts[$period]}
    foreach($property in $actual.binding.source_hashes.PSObject.Properties){
        $path="$linuxRoot/$($property.Name)"; $digest=Digest (Join-Path $projectRoot $property.Name)
        if($digest -ne $property.Value -or ($bound.small_inputs.Contains($path) -and $bound.small_inputs[$path] -ne $digest)){throw 'Actual frozen sources disagree'}
        $bound.small_inputs[$path]=$digest
    }
    $bound.small_inputs["$linuxRoot/$relative"]=Digest (Join-Path $projectRoot $relative)
}
foreach($relative in @('reports/fast_research/CARRY_PAST_FUNDING_EXIT_TINY_20261003_V1.json',"$archive/audit.py","$archive/gate_delta.py","$archive/PREPARED_STATIC_BINDING.json",$binder)){
    $bound.small_inputs["$linuxRoot/$relative"]=Digest (Join-Path $projectRoot $relative)
}
WriteNew (Join-Path $projectRoot "$archive/ACTUAL_BINDING.json") $bound
& wsl.exe -d hpc_linux -- cp -- "$linuxRoot/$archive/ACTUAL_BINDING.json" "$work/ACTUAL_BINDING.json"
if($LASTEXITCODE -ne 0){throw 'STATE actual binding copy failed'}
[ordered]@{status=$bound.status;actuals=$bound.actuals;binding_sha256=(Digest (Join-Path $projectRoot "$archive/ACTUAL_BINDING.json"));checker_sha256=$bound.checker_sha256;small_inputs=$bound.small_inputs.Count}|ConvertTo-Json -Depth 8
