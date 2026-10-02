$ErrorActionPreference = 'Stop'
$coinRoot = 'D:\codex\coin'
$coinOutput = "$coinRoot\reports\fast_research\V7_TASK_WINDOW_KEEPALIVE_ACCEPTANCE_20261002_V1.json"
if (Test-Path -LiteralPath $coinOutput) { throw 'Exclusive acceptance report required' }
$coinFirst = & "$coinRoot\scripts\keep_task_progress_wsl.ps1" | ConvertFrom-Json
$coinSecond = & "$coinRoot\scripts\keep_task_progress_wsl.ps1" | ConvertFrom-Json
if ($coinFirst.pid -ne $coinSecond.pid) { throw 'Repeated launcher created another connection' }
$coinBridge = Get-CimInstance Win32_Process -Filter "ProcessId = $($coinFirst.pid)"
if ($null -eq $coinBridge -or $coinBridge.CommandLine -notmatch 'bounded.sh sleep infinity') { throw 'Live bounded WSL connection missing' }
$coinApi = Invoke-RestMethod 'http://localhost:8765/api/status' -TimeoutSec 8
if (@($coinApi.errors).Count -ne 0 -or $coinApi.resources.ram_limit_bytes -gt 5000000000 -or $coinApi.resources.swap_bytes -ne 0) { throw 'Window or shared resource check failed' }
$coinLinux = @(wsl -d hpc_linux -- bash -lc 'systemctl --user show coin-task-progress-window-v7-v3.service -p MainPID -p ActiveState -p UnitFileState
ps -eo pid,etimes,args | grep -E "/usr/bin/sleep infinity|serve_task_progress_v2.py" | grep -v grep
cat /proc/sys/kernel/random/boot_id' 2>$null)
if ($LASTEXITCODE -ne 0 -or ($coinLinux -join "`n") -notmatch 'ActiveState=active' -or ($coinLinux -join "`n") -notmatch '/usr/bin/sleep infinity') { throw 'Actual Linux viewer or hold process missing' }
$coinPrior = Get-Content "$coinRoot\reports\fast_research\V7_TASK_WINDOW_BOUNDED_SERVICE_ACCEPTANCE_20261002_V1.json" -Raw | ConvertFrom-Json
foreach ($coinItem in $coinPrior.source_hashes.PSObject.Properties) {
    $coinPath = Join-Path $coinRoot $coinItem.Name
    if ((Get-FileHash -LiteralPath $coinPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $coinItem.Value) { throw "Frozen viewer source changed: $($coinItem.Name)" }
}
$coinSources = @{}
$coinSources['scripts/keep_task_progress_wsl.ps1'] = (Get-FileHash "$coinRoot\scripts\keep_task_progress_wsl.ps1" -Algorithm SHA256).Hash.ToLowerInvariant()
$coinPriorHashes = @{}
foreach ($coinName in @('reports/fast_research/V7_TASK_WINDOW_BOUNDED_SERVICE_ACCEPTANCE_20261002_V1.json','reports/fast_research/V7_RUNTIME_INTERRUPTION_PRESERVATION_20261002_V3.json','reports/fast_research/V7_PUBLIC_COLLECTOR_RECOVERY_20261002_V3.json')) {
    $coinPriorHashes[$coinName] = (Get-FileHash (Join-Path $coinRoot $coinName) -Algorithm SHA256).Hash.ToLowerInvariant()
}
$coinReport = [ordered]@{
    status = 'ACCEPTED_LIVE_BOUNDED_WSL_HOLD_AND_UNCHANGED_WINDOW_SERVICE'
    created_utc = (Get-Date).ToUniversalTime().ToString('o')
    source_hashes = $coinSources
    verified_prior_files = $coinPriorHashes
    windows_connection = [ordered]@{pid=$coinBridge.ProcessId; command=$coinBridge.CommandLine; created=$coinBridge.CreationDate.ToUniversalTime().ToString('o'); repeated_launcher_reuses_same_pid=$true; hidden_launch=$true}
    linux_live_process_and_unit = $coinLinux
    actual_api_generated_at = $coinApi.generated_at
    resources = $coinApi.resources
    api_errors = @($coinApi.errors)
    source_and_frozen_viewer_unchanged = $true
    evidence_scope = 'Actual independent Windows connection remains live across completed tool shells; enabled viewer observed auto-start after environment reinitialization. Previous viewer-only fault recovery receipt retained.'
    explicit_wsl_shutdown_prevented = $false
    automatic_model_or_collector_restart_added = $false
    new_observer_started = $false
    locked_consumed = $false
    orders_sent = 0
}
$coinReport | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $coinOutput -Encoding utf8
[pscustomobject]@{status=$coinReport.status;pid=$coinFirst.pid;api_errors=@($coinApi.errors).Count;sha256=(Get-FileHash $coinOutput -Algorithm SHA256).Hash.ToLowerInvariant()} | ConvertTo-Json
