# Keep a foreground WSL client attached while authorized public collectors run.
# No auto-login task, system power change, resource increase, or network action.
$ErrorActionPreference = 'Stop'
$runtimeArgs = @('-d','hpc_linux','--exec','/mnt/d/codex/coin/scripts/bounded.sh','/usr/bin/sleep','2147483647')
$existing = @(Get-CimInstance Win32_Process -Filter "Name='wsl.exe'" | Where-Object {
    $_.CommandLine -like '*hpc_linux*' -and $_.CommandLine -like '*scripts/bounded.sh*' -and $_.CommandLine -like '*/usr/bin/sleep 2147483647*'
})
# Store WSL may expose both the System32 launcher and its packaged child.
# They are one attached client tree, rather than two independent holders.
$holderIds = @($existing | ForEach-Object { $_.ProcessId })
$existing = @($existing | Where-Object { $_.ParentProcessId -notin $holderIds })
if ($existing.Count -gt 1) { throw 'Multiple runtime holders; inspect before changing them' }
if ($existing.Count -eq 1) {
    $process = Get-Process -Id $existing[0].ProcessId
    $reused = $true
} else {
    $process = Start-Process -FilePath "$env:WINDIR/System32/wsl.exe" -ArgumentList $runtimeArgs -WindowStyle Hidden -PassThru
    $reused = $false
}
$value = [ordered]@{ purpose='AUTHORIZED_RESEARCH_WSL_RUNTIME_HOLDER'; host_pid=$process.Id; host_start_utc=$process.StartTime.ToUniversalTime().ToString('o'); reused=$reused; command=$runtimeArgs; gpu_used=$false; resource_limit_changed=$false; system_power_settings_changed=$false; auto_login_task_created=$false }
$value | ConvertTo-Json -Compress
