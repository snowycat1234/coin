param([ValidateSet('start','status','stop')][string]$Action = 'status')
$ErrorActionPreference = 'Stop'
$taskRoot = 'D:\codex\coin'
$hostRecord = Join-Path $taskRoot 'state\live-host.json'
$runner = '/mnt/d/codex/coin/scripts/live.sh'

function Get-OwnedLiveProcess {
    if (-not (Test-Path -LiteralPath $hostRecord)) { return $null }
    $record = Get-Content -LiteralPath $hostRecord -Raw | ConvertFrom-Json
    $liveProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($record.id)"
    if ($liveProcess -and $liveProcess.Name -eq 'wsl.exe' -and
        $liveProcess.CommandLine.Contains($runner) -and
        $liveProcess.CommandLine.Contains('hpc_linux') -and
        $liveProcess.CreationDate.ToUniversalTime().Ticks -eq [long]$record.createdUtcTicks) {
        return $liveProcess
    }
    return $null
}

switch ($Action) {
    'start' {
        if (Get-OwnedLiveProcess) { Write-Output 'Live runtime is already running.'; exit 0 }
        foreach ($directory in @('state','logs')) {
            New-Item -ItemType Directory -Path (Join-Path $taskRoot $directory) -Force | Out-Null
        }
        foreach ($name in @('live.stdout.log','live.stderr.log')) {
            $path = Join-Path $taskRoot "logs\$name"
            if (Test-Path -LiteralPath $path) {
                Move-Item -LiteralPath $path -Destination "$path.previous" -Force
            }
        }
        $launched = Start-Process -FilePath 'wsl.exe' -WindowStyle Hidden -PassThru `
            -WorkingDirectory $taskRoot `
            -ArgumentList @('-d','hpc_linux','--exec','bash',$runner) `
            -RedirectStandardOutput (Join-Path $taskRoot 'logs\live.stdout.log') `
            -RedirectStandardError (Join-Path $taskRoot 'logs\live.stderr.log')
        $liveProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($launched.Id)"
        @{id=$launched.Id;createdUtcTicks=$liveProcess.CreationDate.ToUniversalTime().Ticks;
          runner=$runner;distribution='hpc_linux'} | ConvertTo-Json |
          Set-Content -LiteralPath $hostRecord -Encoding utf8
        Write-Output "Live runtime launched: host PID $($launched.Id)."
    }
    'status' {
        if (Get-OwnedLiveProcess) { Write-Output 'WSL foreground client is running.' }
        else { Write-Output 'WSL foreground client is not running.' }
        & wsl.exe -d hpc_linux --exec bash /mnt/d/codex/coin/scripts/run.sh live-status
        exit $LASTEXITCODE
    }
    'stop' {
        if (-not (Get-OwnedLiveProcess)) { Write-Output 'No owned live process.'; exit 0 }
        # The app handles this stop request, checkpoints both ledgers and exits WSL.
        Set-Content -LiteralPath (Join-Path $taskRoot 'state\live.stop') -Value 'stop' -Encoding ascii
        Write-Output 'Graceful stop requested.'
    }
}
