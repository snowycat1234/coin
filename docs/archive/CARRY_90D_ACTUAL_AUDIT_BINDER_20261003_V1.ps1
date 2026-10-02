$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\codex\coin'
$linuxRoot = '/mnt/d/codex/coin'
$work = '/home/xflops/coin-state/test-carry-90d-two-controls-independent-audit-20261003-v1'
$archive = 'docs/archive/CARRY_90D_USED_INDEPENDENT_SOURCES_20261003_V1'
$protocol = 'protocols/CONDITIONAL_CARRY_90D_FIXED_PERIOD_20261003_V1.json'
function Digest([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower() }
function WriteNew([string]$path, $value) {
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes(($value | ConvertTo-Json -Depth 30) + "`n")
    $stream = [IO.File]::Open($path, [IO.FileMode]::CreateNew)
    try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
}
New-Item -ItemType Directory -Path (Join-Path $projectRoot $archive) -ErrorAction Stop | Out-Null
& wsl.exe -d hpc_linux --cd $linuxRoot -- cp -- "$work/audit.py" "$work/reused_blocks.py" "$work/PREPARED_STATIC_BINDING.json" "$linuxRoot/$archive/"
if ($LASTEXITCODE -ne 0) { throw 'Copy exact prepared checker failed' }
$prepared = Get-Content -LiteralPath (Join-Path $projectRoot "$archive/PREPARED_STATIC_BINDING.json") -Raw | ConvertFrom-Json
if ((Digest (Join-Path $projectRoot "$archive/audit.py")) -ne $prepared.checker_sha256 -or
    (Digest (Join-Path $projectRoot "$archive/reused_blocks.py")) -ne $prepared.reused_blocks_sha256) { throw 'Prepared bytes changed' }
$bound = [ordered]@{
    status='FROZEN_AFTER_TWO_ACTUAL_CLOSED_EXIT0_BEFORE_UNIQUE_INDEPENDENT_AUDIT'
    protocol_path=$protocol
    checker_path="$work/audit.py"
    checker_sha256=$prepared.checker_sha256
    reused_blocks_sha256=$prepared.reused_blocks_sha256
    actuals=@()
    small_inputs=[ordered]@{}
    reused_blocks_archived="$linuxRoot/$archive/reused_blocks.py"
    binder_source="$linuxRoot/docs/archive/CARRY_90D_ACTUAL_AUDIT_BINDER_20261003_V1.ps1"
    binder_sha256=(Digest (Join-Path $projectRoot 'docs/archive/CARRY_90D_ACTUAL_AUDIT_BINDER_20261003_V1.ps1'))
    market_arrays_read=$false
    old_tests_or_QA_repeated=$false
}
$old = @(
    @('core','docs/archive/CONDITIONAL_CARRY_USED_INDEPENDENT_SOURCES_20261003_V1/audit.py'),
    @('pair_audit','docs/archive/CONDITIONAL_CARRY_PAIR_TRIM_USED_INDEPENDENT_SOURCES_20261003_V1/audit.py'),
    @('pair_delta','docs/archive/CONDITIONAL_CARRY_PAIR_TRIM_USED_INDEPENDENT_SOURCES_20261003_V1/audit_delta.py'),
    @('price_reader','docs/archive/BASIS_RISK_USED_INDEPENDENT_SOURCES_20261003_V1/audit.py')
)
foreach ($row in $old) {
    $path = "$linuxRoot/$($row[1])"; $digest = Digest (Join-Path $projectRoot $row[1])
    if ($prepared.source_hashes.$path -ne $digest) { throw 'Accepted independent bytes changed' }
    $bound[$row[0]+'_path'] = $path; $bound[$row[0]+'_sha256'] = $digest
    $bound.small_inputs[$path] = $digest
}
$hosts = @{ALL_FLAT='session73766 / chunk66dec8 / actual exit0';PAIR_TRIM='session33399 / chunk61416e / actual exit0'}
foreach ($policy in @('ALL_FLAT','PAIR_TRIM')) {
    $relative = 'reports/fast_research/CARRY_90D_'+$policy+'_ACTUAL_20261003_V1.json'
    $actual = Get-Content -LiteralPath (Join-Path $projectRoot $relative) -Raw | ConvertFrom-Json
    if ($actual.policy -ne $policy -or $actual.status -ne 'COMPLETE_CARRY_90D_DEVELOPMENT_EXTRAPOLATION_CONDITIONAL_NOT_LONG_TERM_APR') { throw 'Actual incomplete' }
    $taskPath = '/home/xflops/coin-state/task-progress/task-'+$actual.binding.task_id+'.json'
    $taskRaw = & wsl.exe -d hpc_linux -- cat -- $taskPath
    if ($LASTEXITCODE -ne 0) { throw 'Actual task missing' }
    $task = ($taskRaw -join "`n") | ConvertFrom-Json
    if ($task.id -ne $actual.binding.task_id -or $task.status -ne 'completed' -or $task.exit_code -ne 0) { throw 'Actual task not closed0' }
    $bound.actuals += [ordered]@{policy=$policy;actual_report_path=$relative;actual_report_sha256=(Digest (Join-Path $projectRoot $relative));actual_task_id=$task.id;actual_host_result=$hosts[$policy]}
    foreach ($property in $actual.binding.source_hashes.PSObject.Properties) {
        $path = "$linuxRoot/$($property.Name)"; $digest = Digest (Join-Path $projectRoot $property.Name)
        if ($digest -ne $property.Value -or ($bound.small_inputs.Contains($path) -and $bound.small_inputs[$path] -ne $digest)) { throw 'Frozen actual sources changed or disagree' }
        $bound.small_inputs[$path] = $digest
    }
    $bound.small_inputs["$linuxRoot/$relative"] = Digest (Join-Path $projectRoot $relative)
}
foreach ($relative in @('reports/fast_research/CARRY_90D_PERIOD_TINY_20261003_V1.json',"$archive/audit.py","$archive/reused_blocks.py","$archive/PREPARED_STATIC_BINDING.json",'docs/archive/CARRY_90D_ACTUAL_AUDIT_BINDER_20261003_V1.ps1')) {
    $bound.small_inputs["$linuxRoot/$relative"] = Digest (Join-Path $projectRoot $relative)
}
WriteNew (Join-Path $projectRoot "$archive/ACTUAL_BINDING.json") $bound
& wsl.exe -d hpc_linux -- cp -- "$linuxRoot/$archive/ACTUAL_BINDING.json" "$work/ACTUAL_BINDING.json"
if ($LASTEXITCODE -ne 0) { throw 'Frozen STATE binding copy failed' }
[ordered]@{status=$bound.status;actuals=$bound.actuals;binding_sha256=(Digest (Join-Path $projectRoot "$archive/ACTUAL_BINDING.json"));checker_sha256=$bound.checker_sha256;small_sources=$bound.small_inputs.Count} | ConvertTo-Json -Depth 8
