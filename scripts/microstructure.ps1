param([ValidateSet('start','status','stop')][string]$Action = 'status')
$ErrorActionPreference = 'Stop'
$taskRoot = 'D:\codex\coin'
$recordPath = Join-Path $taskRoot 'state\microstructure-host.json'
$runner = '/mnt/d/codex/coin/scripts/microstructure.sh'

function Get-OwnedProcess {
    if (-not (Test-Path -LiteralPath $recordPath)) { return $null }
    $record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
    $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($record.id)"
    if ($taskProcess -and $taskProcess.Name -eq 'wsl.exe' -and
        $taskProcess.CommandLine.Contains($runner) -and
        $taskProcess.CommandLine.Contains('hpc_linux') -and
        $taskProcess.CreationDate.ToUniversalTime().Ticks -eq [long]$record.createdUtcTicks) {
        return $taskProcess
    }
    return $null
}

switch ($Action) {
    'start' {
        if (Get-OwnedProcess) { Write-Output 'Microstructure collection already running.'; exit 0 }
        $receipt = Get-Content -LiteralPath (Join-Path $taskRoot 'reports\A07_MICROSTRUCTURE_ACCEPTANCE.json') -Raw | ConvertFrom-Json
        if ($receipt.status -ne 'DATA_ENGINEERING_SHORT_ACCEPTANCE_PASS') { throw 'A07 acceptance required.' }
        $expected = $receipt.source_hashes.'src/quant/microstructure.py'
        $actual = (Get-FileHash -LiteralPath (Join-Path $taskRoot 'src\quant\microstructure.py') -Algorithm SHA256).Hash.ToLower()
        if ($expected -ne $actual) { throw 'Frozen A07 implementation changed.' }
        foreach ($directory in @('state','logs')) {
            New-Item -ItemType Directory -Path (Join-Path $taskRoot $directory) -Force | Out-Null
        }
        foreach ($name in @('microstructure.stdout.log','microstructure.stderr.log')) {
            $path = Join-Path $taskRoot "logs\$name"
            if (Test-Path -LiteralPath $path) {
                $archive = "$path.$([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()).previous"
                Move-Item -LiteralPath $path -Destination $archive
            }
        }
        $launched = Start-Process -FilePath 'wsl.exe' -WindowStyle Hidden -PassThru `
            -WorkingDirectory $taskRoot -ArgumentList @('-d','hpc_linux','--exec','bash',$runner) `
            -RedirectStandardOutput (Join-Path $taskRoot 'logs\microstructure.stdout.log') `
            -RedirectStandardError (Join-Path $taskRoot 'logs\microstructure.stderr.log')
        $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($launched.Id)"
        @{id=$launched.Id;createdUtcTicks=$taskProcess.CreationDate.ToUniversalTime().Ticks;
          runner=$runner;distribution='hpc_linux'} | ConvertTo-Json |
            Set-Content -LiteralPath $recordPath -Encoding utf8
        Write-Output "Public microstructure collector launched: host PID $($launched.Id)."
    }
    'status' {
        if (Get-OwnedProcess) { Write-Output 'Owned WSL foreground client is running.' }
        else { Write-Output 'Owned WSL foreground client is not running.' }
        & wsl.exe -d hpc_linux --exec bash /mnt/d/codex/coin/scripts/bounded.sh /mnt/d/codex/coin/.venv/bin/python -m quant.microstructure
        exit $LASTEXITCODE
    }
    'stop' {
        if (-not (Get-OwnedProcess)) { Write-Output 'No owned microstructure process.'; exit 0 }
        & wsl.exe -d hpc_linux --exec pkill -TERM -f '^/mnt/d/codex/coin/.venv/bin/python -u -m quant.microstructure --run$'
        if ($LASTEXITCODE -ne 0) { throw 'Graceful stop request failed.' }
        Write-Output 'Graceful collector stop requested.'
    }
}
