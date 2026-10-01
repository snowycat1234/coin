param([ValidateSet('start','status','stop')][string]$Action = 'status')
$ErrorActionPreference = 'Stop'
$taskRoot = 'D:\codex\coin'
$recordPath = Join-Path $taskRoot 'state\collector-public-v3-host.json'
$runner = '/mnt/d/codex/coin/scripts/collector_public_v3.sh'
$stopPath = Join-Path $taskRoot 'state\collector_public_v3.stop'

function Get-OwnedProcess {
    if (-not (Test-Path -LiteralPath $recordPath)) { return $null }
    $record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
    $owned = Get-CimInstance Win32_Process -Filter "ProcessId=$($record.id)"
    if ($owned -and $owned.Name -eq 'wsl.exe' -and
        $owned.CommandLine.Contains($runner) -and $owned.CommandLine.Contains('hpc_linux') -and
        $owned.CreationDate.ToUniversalTime().Ticks -eq [long]$record.createdUtcTicks) {
        return $owned
    }
    return $null
}

switch ($Action) {
    'start' {
        if (Get-OwnedProcess) { Write-Output 'Public v3 collection already running.'; exit 0 }
        $receipt = Get-Content -LiteralPath (Join-Path $taskRoot 'reports\PUBLIC_COLLECTOR_V3_ACCEPTANCE.json') -Raw | ConvertFrom-Json
        if ($receipt.status -ne 'PUBLIC_MARKET_DATA_ENGINEERING_ACCEPTANCE_PASS') {
            throw 'Public v3 engineering acceptance required.'
        }
        foreach ($source in $receipt.source_hashes.PSObject.Properties) {
            $path = Join-Path $taskRoot $source.Name
            $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower()
            if ($actual -ne $source.Value) { throw "Public v3 frozen source changed: $($source.Name)" }
        }
        foreach ($directory in @('state','logs')) {
            New-Item -ItemType Directory -Path (Join-Path $taskRoot $directory) -Force | Out-Null
        }
        if (Test-Path -LiteralPath $stopPath) { Remove-Item -LiteralPath $stopPath }
        foreach ($name in @('collector-public-v3.stdout.log','collector-public-v3.stderr.log')) {
            $path = Join-Path $taskRoot "logs\$name"
            if (Test-Path -LiteralPath $path) {
                Move-Item -LiteralPath $path -Destination "$path.$([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()).previous"
            }
        }
        $launched = Start-Process -FilePath 'wsl.exe' -WindowStyle Hidden -PassThru `
            -WorkingDirectory $taskRoot -ArgumentList @('-d','hpc_linux','--exec','bash',$runner) `
            -RedirectStandardOutput (Join-Path $taskRoot 'logs\collector-public-v3.stdout.log') `
            -RedirectStandardError (Join-Path $taskRoot 'logs\collector-public-v3.stderr.log')
        $owned = Get-CimInstance Win32_Process -Filter "ProcessId=$($launched.Id)"
        @{id=$launched.Id;createdUtcTicks=$owned.CreationDate.ToUniversalTime().Ticks;
          runner=$runner;distribution='hpc_linux'} | ConvertTo-Json |
            Set-Content -LiteralPath $recordPath -Encoding utf8
        Write-Output "Public v3 collector launched: host PID $($launched.Id)."
    }
    'status' {
        if (Get-OwnedProcess) { Write-Output 'Owned public v3 WSL foreground client is running.' }
        else { Write-Output 'Owned public v3 WSL foreground client is not running.' }
        & wsl.exe -d hpc_linux --exec bash /mnt/d/codex/coin/scripts/bounded.sh /mnt/d/codex/coin/.venv/bin/python -m quant.collector_public_v3
        exit $LASTEXITCODE
    }
    'stop' {
        if (-not (Get-OwnedProcess)) { Write-Output 'No owned public v3 collector.'; exit 0 }
        Set-Content -LiteralPath $stopPath -Value 'stop' -Encoding ascii
        Write-Output 'Graceful public v3 stop requested.'
    }
}
