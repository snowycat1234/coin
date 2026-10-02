$ErrorActionPreference='Stop'
$projectRoot='D:\codex\coin'; $linuxRoot='/mnt/d/codex/coin'
$old='docs/archive/CARRY_90D_USED_INDEPENDENT_SOURCES_20261003_V2'
$new='docs/archive/CARRY_90D_USED_INDEPENDENT_SOURCES_20261003_V3'
$work='/home/xflops/coin-state/test-carry-90d-two-controls-independent-audit-20261003-v3'
function Digest([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower() }
function WriteBytesNew([string]$path,[string]$text) {
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes($text)
    $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew)
    try {$stream.Write($bytes,0,$bytes.Length)} finally {$stream.Dispose()}
}
function WriteJsonNew([string]$path,$value) {WriteBytesNew $path (($value|ConvertTo-Json -Depth 30)+"`n")}
function ReplaceOne([string]$text,[string]$from,[string]$to) {
    if (($text.Split(@($from),[StringSplitOptions]::None).Length-1) -ne 1) {throw 'Unique explicit adapter anchor required'}
    return $text.Replace($from,$to)
}
New-Item -ItemType Directory -Path (Join-Path $projectRoot $new) -ErrorAction Stop | Out-Null
$code=[IO.File]::ReadAllText((Join-Path $projectRoot "$old/audit.py"))
$code=ReplaceOne $code 'test-carry-90d-two-controls-independent-audit-20261003-v2' 'test-carry-90d-two-controls-independent-audit-20261003-v3'
$code=ReplaceOne $code 'CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V2.json' 'CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V3.json'
$code=ReplaceOne $code '        prices,events,inputs=original_inputs(view,reader,core)' "        compiled_financial={policy:rb.financial(core,trim,delta,policy) for policy in ('ALL_FLAT','PAIR_TRIM')}`n        prices,events,inputs=original_inputs(view,reader,core)"
$code=ReplaceOne $code '            verify,proof=rb.financial(core,trim,delta,policy)' '            verify,proof=compiled_financial[policy]'
WriteBytesNew (Join-Path $projectRoot "$new/audit.py") $code
$blocks=[IO.File]::ReadAllText((Join-Path $projectRoot "$old/reused_blocks.py"))
$blocks=ReplaceOne $blocks "    need({r['old'] for r in changes}==set(substitutions),'Each period/count constant is explicitly adapted')" "    expected=set(substitutions) if policy=='ALL_FLAT' else {732,122}`n    need({r['old'] for r in changes}==expected,'Each existing period/count constant is explicitly adapted')"
WriteBytesNew (Join-Path $projectRoot "$new/reused_blocks.py") $blocks
$failurePath='reports/fast_research/CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT_20261003_V2.json'
$failure=Get-Content -LiteralPath (Join-Path $projectRoot $failurePath) -Raw | ConvertFrom-Json
if ($failure.status -ne 'FAIL_CARRY_90D_TWO_POLICY_DECIMAL_INDEPENDENT_AUDIT' -or $failure.reason -ne 'Each period/count constant is explicitly adapted' -or $failure.completed_cases_verified -ne 1) {throw 'Actual V2 partial failed proof required'}
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
$bound.binder_source="$linuxRoot/docs/archive/CARRY_90D_AUDIT_V3_FREEZER_20261003_V1.ps1"
$bound.binder_sha256=Digest (Join-Path $projectRoot 'docs/archive/CARRY_90D_AUDIT_V3_FREEZER_20261003_V1.ps1')
$bound | Add-Member -NotePropertyName actual_failed_v2 -NotePropertyValue ([ordered]@{path=$failurePath;sha256=(Digest (Join-Path $projectRoot $failurePath));task_id=$task.id;host='session2028 / chunkf9748e / actual exit1';price_arrays_read=$true;completed_financial_cases=1;reason=$failure.reason;partial_not_module_accepted=$true})
foreach ($relative in @($failurePath,"$old/FAILED_TASK_ACTUAL.json","$old/ACTUAL_BINDING.json","$new/audit.py","$new/reused_blocks.py",'docs/archive/CARRY_90D_AUDIT_V3_FREEZER_20261003_V1.ps1')) {
    $bound.small_inputs | Add-Member -NotePropertyName "$linuxRoot/$relative" -NotePropertyValue (Digest (Join-Path $projectRoot $relative))
}
WriteJsonNew (Join-Path $projectRoot "$new/ACTUAL_BINDING.json") $bound
WriteJsonNew (Join-Path $projectRoot "$new/DERIVATION_FROM_FAILED_V2.json") ([ordered]@{status='FROZEN_NEW_V3_BEFORE_EXECUTION';failed_v2=$bound.actual_failed_v2;old_checker_sha256=(Digest (Join-Path $projectRoot "$old/audit.py"));new_checker_sha256=$bound.checker_sha256;old_blocks_sha256=(Digest (Join-Path $projectRoot "$old/reused_blocks.py"));new_blocks_sha256=$bound.reused_blocks_sha256;only_changes=@('New V3 STATE/output paths','Require only existing literals per policy; PAIR_TRIM uses COUNT namespace instead of literal175680','Resolve both unchanged financial blocks before array reading');original_frozen_sources_modified=$false;account_rules_or_actual_reports_modified=$false;new_execution_started=$false})
& wsl.exe -d hpc_linux -- mkdir -- $work
if ($LASTEXITCODE -ne 0) {throw 'Exclusive new STATE failed'}
& wsl.exe -d hpc_linux -- cp -- "$linuxRoot/$new/audit.py" "$linuxRoot/$new/reused_blocks.py" "$linuxRoot/$new/ACTUAL_BINDING.json" $work
if ($LASTEXITCODE -ne 0) {throw 'Exact new frozen audit copy failed'}
[ordered]@{status='FROZEN_NEW_V3_AFTER_REAL_V2_FAILURE';checker_sha256=$bound.checker_sha256;reused_blocks_sha256=$bound.reused_blocks_sha256;binding_sha256=(Digest (Join-Path $projectRoot "$new/ACTUAL_BINDING.json"));failure=$bound.actual_failed_v2} | ConvertTo-Json -Depth 8
