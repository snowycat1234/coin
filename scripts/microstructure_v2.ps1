param([ValidateSet('start','status','stop')][string]$Action = 'status')
$ErrorActionPreference = 'Stop'
$taskRoot = 'D:\codex\coin'
$taskRecordPath = Join-Path $taskRoot 'state\microstructure-v2-host.json'
$taskRunner = '/mnt/d/codex/coin/scripts/microstructure_v2.sh'

function Get-OwnedV2Process {
    if (-not (Test-Path -LiteralPath $taskRecordPath)) { return $null }
    $taskRecord = Get-Content -LiteralPath $taskRecordPath -Raw | ConvertFrom-Json
    $taskOwned = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskRecord.id)"
    if ($taskOwned -and $taskOwned.Name -eq 'wsl.exe' -and
        $taskOwned.CommandLine.Contains($taskRunner) -and
        $taskOwned.CommandLine.Contains('hpc_linux') -and
        $taskOwned.CreationDate.ToUniversalTime().Ticks -eq [long]$taskRecord.createdUtcTicks) {
        return $taskOwned
    }
    return $null
}

switch ($Action) {
    'start' {
        if (Get-OwnedV2Process) { Write-Output 'V2 public collection already running.'; exit 0 }
        $taskAcceptance = Get-Content -LiteralPath (Join-Path $taskRoot 'reports\A09_MICROSTRUCTURE_V2_ACCEPTANCE_20261001.json') -Raw | ConvertFrom-Json
        if ($taskAcceptance.status -ne 'A09_MICROSTRUCTURE_V2_CORRECTNESS_ENGINEERING_PASS') {
            throw 'A09 v2 correctness and real public short-smoke acceptance required.'
        }
        foreach ($taskSource in $taskAcceptance.source_hashes.PSObject.Properties) {
            $taskActual = (Get-FileHash -LiteralPath (Join-Path $taskRoot $taskSource.Name) -Algorithm SHA256).Hash.ToLower()
            if ($taskActual -ne $taskSource.Value) { throw ('Accepted v2 source changed: ' + $taskSource.Name) }
        }
        foreach ($taskDirectory in @('state','logs')) {
            New-Item -ItemType Directory -Path (Join-Path $taskRoot $taskDirectory) -Force | Out-Null
        }
        foreach ($taskName in @('microstructure-v2.stdout.log','microstructure-v2.stderr.log')) {
            $taskLog = Join-Path $taskRoot ('logs\' + $taskName)
            if (Test-Path -LiteralPath $taskLog) {
                Move-Item -LiteralPath $taskLog -Destination ($taskLog + '.' + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() + '.previous')
            }
        }
        $taskLaunched = Start-Process -FilePath 'wsl.exe' -WindowStyle Hidden -PassThru `
            -WorkingDirectory $taskRoot -ArgumentList @('-d','hpc_linux','--exec','bash',$taskRunner) `
            -RedirectStandardOutput (Join-Path $taskRoot 'logs\microstructure-v2.stdout.log') `
            -RedirectStandardError (Join-Path $taskRoot 'logs\microstructure-v2.stderr.log')
        $taskOwned = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskLaunched.Id)"
        @{ id=$taskLaunched.Id; createdUtcTicks=$taskOwned.CreationDate.ToUniversalTime().Ticks;
           runner=$taskRunner; distribution='hpc_linux'; version='microstructure_l1_v2' } |
            ConvertTo-Json | Set-Content -LiteralPath $taskRecordPath -Encoding utf8NoBOM
        Write-Output "V2 public collector launched: host PID $($taskLaunched.Id)."
    }
    'status' {
        if (Get-OwnedV2Process) { Write-Output 'Owned v2 WSL client is running.' }
        else { Write-Output 'Owned v2 WSL client is not running.' }
        & wsl.exe -d hpc_linux --exec bash /mnt/d/codex/coin/scripts/bounded.sh /mnt/d/codex/coin/.venv/bin/python -m quant.microstructure_v2
        exit $LASTEXITCODE
    }
    'stop' {
        if (-not (Get-OwnedV2Process)) { Write-Output 'No owned v2 microstructure process.'; exit 0 }
        & wsl.exe -d hpc_linux --exec pkill -TERM -f '^/mnt/d/codex/coin/.venv/bin/python -u -m quant.microstructure_v2 --run$'
        if ($LASTEXITCODE -ne 0) { throw 'Graceful v2 stop request failed.' }
        Write-Output 'Graceful v2 collector stop requested.'
    }
}
