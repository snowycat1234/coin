param([ValidateSet('start','status')][string]$Action = 'status')
$ErrorActionPreference = 'Stop'
$taskRoot = 'D:\codex\coin'
$taskOwnerPath = Join-Path $taskRoot 'state\a07-resource-observer-host.json'
$taskRunner = '/mnt/d/codex/coin/scripts/observe_a07_resources.py'

function Get-ObserverProcess {
    if (-not (Test-Path -LiteralPath $taskOwnerPath)) { return $null }
    $taskOwner = Get-Content -LiteralPath $taskOwnerPath -Raw | ConvertFrom-Json
    $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskOwner.id)"
    if ($taskProcess -and $taskProcess.Name -eq 'wsl.exe' -and
        $taskProcess.CommandLine.Contains($taskRunner) -and
        $taskProcess.CommandLine.Contains('hpc_linux') -and
        $taskProcess.CreationDate.ToUniversalTime().Ticks -eq [long]$taskOwner.createdUtcTicks) {
        return $taskProcess
    }
    return $null
}

switch ($Action) {
    'start' {
        if (Get-ObserverProcess) { Write-Output 'Owned A07 resource observer is running.'; exit 0 }
        $taskReceiptPath = Join-Path $taskRoot 'reports\A07_RESOURCE_OBSERVER_ACCEPTANCE_20261001.json'
        $taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json
        if ($taskReceipt.status -ne 'A07_RESOURCE_OBSERVER_SHORT_ENGINEERING_PASS') {
            throw 'Resource observer engineering acceptance required.'
        }
        foreach ($taskSource in $taskReceipt.source_hashes.PSObject.Properties) {
            $taskActual = (Get-FileHash -LiteralPath (Join-Path $taskRoot $taskSource.Name) `
                -Algorithm SHA256).Hash.ToLower()
            if ($taskActual -ne $taskSource.Value) { throw "Observer source changed: $($taskSource.Name)" }
        }
        $taskLaunch = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        $taskDirectory = "/mnt/d/codex/coin/reports/generated/A07_RESOURCE_WINDOW_$taskLaunch"
        $taskArguments = @('-d','hpc_linux','--exec','bash',
            '/mnt/d/codex/coin/scripts/bounded.sh','/mnt/d/codex/coin/.venv/bin/python',
            '-u',$taskRunner,'--directory',$taskDirectory)
        $taskProcess = Start-Process -FilePath 'wsl.exe' -WindowStyle Hidden -PassThru `
            -WorkingDirectory $taskRoot -ArgumentList $taskArguments `
            -RedirectStandardOutput (Join-Path $taskRoot "logs\a07-observer-$taskLaunch.stdout.log") `
            -RedirectStandardError (Join-Path $taskRoot "logs\a07-observer-$taskLaunch.stderr.log")
        $taskOwned = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskProcess.Id)"
        @{id=$taskProcess.Id;createdUtcTicks=$taskOwned.CreationDate.ToUniversalTime().Ticks;
          distribution='hpc_linux';runner=$taskRunner;directory=$taskDirectory} | ConvertTo-Json |
            Set-Content -LiteralPath $taskOwnerPath -Encoding utf8
        Write-Output "A07 sampled resource observer launched: host PID $($taskProcess.Id)."
    }
    'status' {
        if (Get-ObserverProcess) { Write-Output 'Owned A07 resource observer is running.' }
        else { Write-Output 'Owned A07 resource observer is not running.' }
        if (Test-Path -LiteralPath $taskOwnerPath) { Get-Content -LiteralPath $taskOwnerPath }
    }
}
