$ErrorActionPreference='Stop'
$projectRoot='D:\codex\coin'; $linuxRoot='/mnt/d/codex/coin'
$old='docs/archive/CARRY_90D_USED_INDEPENDENT_SOURCES_20261003_V1'
$new='docs/archive/CARRY_90D_USED_INDEPENDENT_SOURCES_20261003_V2'
$work='/home/xflops/coin-state/test-carry-90d-two-controls-independent-audit-20261003-v2'
function Digest([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower() }
function WriteBytesNew([string]$path,[string]$text) {
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes($text)
    $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew)
    try {$stream.Write($bytes,0,$bytes.Length)} finally {$stream.Dispose()}
}
function WriteJsonNew([string]$path,$value) {WriteBytesNew $path (($value|ConvertTo-Json -Depth 30)+"`n")}
New-Item -ItemType Directory -Path (Join-Path $projectRoot $new) -ErrorAction Stop | Out-Null
$code=[IO.File]::ReadAllText((Join-Path $projectRoot "$old/audit.py"))
foreach ($token in @('test-carry-90d-two-controls-independent-audit-20261003-v1','CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json')) {
    if (($code.Split(@($token),[StringSplitOptions]::None).Length-1) -ne 1) {throw 'Unique version anchor required'}
}
$code=$code.Replace('test-carry-90d-two-controls-independent-audit-20261003-v1','test-carry-90d-two-controls-independent-audit-20261003-v2').Replace('CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json','CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V2.json')
WriteBytesNew (Join-Path $projectRoot "$new/audit.py") $code
$blocks=[IO.File]::ReadAllText((Join-Path $projectRoot "$old/reused_blocks.py"))
$anchor="    need(len(begins)==len(ends)==1 and begins[0]<ends[0],'Unique accepted financial-only span')"
if (($blocks.Split(@($anchor),[StringSplitOptions]::None).Length-1) -ne 1) {throw 'Unique extraction guard required'}
$replacement="    need(len(begins)==1,'Unique accepted financial beginning')`n    ends=[i for i in ends if i>begins[0]]`n"+$anchor
$blocks=$blocks.Replace($anchor,$replacement)
WriteBytesNew (Join-Path $projectRoot "$new/reused_blocks.py") $blocks
$failurePath='reports/fast_research/CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json'
$failure=Get-Content -LiteralPath (Join-Path $projectRoot $failurePath) -Raw | ConvertFrom-Json
if ($failure.status -ne 'FAIL_CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT' -or $failure.reason -ne 'Unique accepted financial-only span' -or $failure.completed_cases_verified -ne 0) {throw 'Actual V1 failure required'}
$failedTask='/home/xflops/coin-state/task-progress/task-'+$failure.binding.task_id+'.json'
& wsl.exe -d hpc_linux -- cp -- $failedTask "$linuxRoot/$old/FAILED_TASK_ACTUAL.json"
if ($LASTEXITCODE -ne 0) {throw 'Failed task copy'}
$task=Get-Content -LiteralPath (Join-Path $projectRoot "$old/FAILED_TASK_ACTUAL.json") -Raw | ConvertFrom-Json
if ($task.id -ne $failure.binding.task_id -or $task.status -ne 'failed' -or $task.exit_code -ne 1) {throw 'Real failed exit1 proof'}
$bound=Get-Content -LiteralPath (Join-Path $projectRoot "$old/ACTUAL_BINDING.json") -Raw | ConvertFrom-Json
$bound.checker_path="$work/audit.py"
$bound.checker_sha256=Digest (Join-Path $projectRoot "$new/audit.py")
$bound.reused_blocks_sha256=Digest (Join-Path $projectRoot "$new/reused_blocks.py")
$bound.reused_blocks_archived="$linuxRoot/$new/reused_blocks.py"
$bound.binder_source="$linuxRoot/docs/archive/CARRY_90D_AUDIT_V2_FREEZER_20261003_V1.ps1"
$bound.binder_sha256=Digest (Join-Path $projectRoot 'docs/archive/CARRY_90D_AUDIT_V2_FREEZER_20261003_V1.ps1')
$bound | Add-Member -NotePropertyName actual_failed_v1 -NotePropertyValue ([ordered]@{path=$failurePath;sha256=(Digest (Join-Path $projectRoot $failurePath));task_id=$task.id;host='chunk8f5d50 actual exit1';price_arrays_read=$true;completed_financial_cases=0;reason=$failure.reason})
foreach ($relative in @($failurePath,"$old/FAILED_TASK_ACTUAL.json","$old/ACTUAL_BINDING.json","$new/audit.py","$new/reused_blocks.py",'docs/archive/CARRY_90D_AUDIT_V2_FREEZER_20261003_V1.ps1')) {
    $bound.small_inputs | Add-Member -NotePropertyName "$linuxRoot/$relative" -NotePropertyValue (Digest (Join-Path $projectRoot $relative))
}
WriteJsonNew (Join-Path $projectRoot "$new/ACTUAL_BINDING.json") $bound
WriteJsonNew (Join-Path $projectRoot "$new/DERIVATION_FROM_FAILED_V1.json") ([ordered]@{status='FROZEN_NEW_V2_BEFORE_FINANCIAL_EXECUTION';failed_v1=$bound.actual_failed_v1;old_checker_sha256=(Digest (Join-Path $projectRoot "$old/audit.py"));new_checker_sha256=$bound.checker_sha256;old_blocks_sha256=(Digest (Join-Path $projectRoot "$old/reused_blocks.py"));new_blocks_sha256=$bound.reused_blocks_sha256;only_changes=@('New V2 STATE/output paths','Select unique financial-end anchor strictly after unique financial-begin anchor');original_frozen_sources_modified=$false;account_rules_or_actual_reports_modified=$false;new_financial_execution_started=$false})
& wsl.exe -d hpc_linux -- mkdir -- $work
if ($LASTEXITCODE -ne 0) {throw 'Exclusive new STATE failed'}
& wsl.exe -d hpc_linux -- cp -- "$linuxRoot/$new/audit.py" "$linuxRoot/$new/reused_blocks.py" "$linuxRoot/$new/ACTUAL_BINDING.json" $work
if ($LASTEXITCODE -ne 0) {throw 'Exact new frozen audit copy failed'}
[ordered]@{status='FROZEN_NEW_V2_AFTER_REAL_V1_FAILURE';checker_sha256=$bound.checker_sha256;reused_blocks_sha256=$bound.reused_blocks_sha256;binding_sha256=(Digest (Join-Path $projectRoot "$new/ACTUAL_BINDING.json"));failure=$bound.actual_failed_v1} | ConvertTo-Json -Depth 8
