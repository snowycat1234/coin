# Keep the existing D-hosted WSL window available after transient tool shells close.
# No training, source migration, observer, Windows Python or paid service is started.
$ErrorActionPreference = 'Stop'
$coinRoot = 'D:\codex\coin'
$coinExisting = @(Get-CimInstance Win32_Process -Filter "Name = 'wsl.exe'" |
    Where-Object { $_.CommandLine -match 'hpc_linux' -and
        $_.CommandLine -match '/mnt/d/codex/coin/scripts/bounded.sh' -and
        $_.CommandLine -match 'sleep infinity' })
if ($coinExisting.Count -eq 0) {
    $coinProcess = Start-Process -FilePath 'wsl.exe' -ArgumentList @(
        '-d', 'hpc_linux', '--exec', 'bash', '/mnt/d/codex/coin/scripts/bounded.sh',
        'sleep', 'infinity') -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput "$coinRoot\.cache\wsl-progress-keepalive.stdout.log" `
        -RedirectStandardError "$coinRoot\.cache\wsl-progress-keepalive.stderr.log"
    $coinPid = $coinProcess.Id
} else {
    $coinPid = $coinExisting[0].ProcessId
}
[pscustomobject]@{
    pid = $coinPid
    purpose = 'Keep D-hosted WSL alive; enabled bounded viewer service starts inside WSL.'
    explicit_wsl_shutdown_prevented = $false
} | ConvertTo-Json
