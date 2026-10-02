param([Parameter(Mandatory=$true)][string]$Url,
      [Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference = 'Stop'
$allowed = @(
    'https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&startTime=1754006400000&endTime=1754064001000&limit=3',
    'https://fapi.binance.com/fapi/v1/fundingRate?symbol=ETHUSDT&startTime=1754006400000&endTime=1754064001000&limit=3'
)
if ($Url -cnotin $allowed) { throw 'Only two exact official historical URLs are permitted' }
$statePrefix = '\\wsl.localhost\hpc_linux\home\xflops\coin-state\funding-semantics-probe-20261003-v2\'
$fullPath = [IO.Path]::GetFullPath($OutputPath)
if (!$fullPath.StartsWith($statePrefix, [StringComparison]::OrdinalIgnoreCase) -or
    [IO.Path]::GetFileName($fullPath) -cnotin @('BTCUSDT-official-response.json', 'ETHUSDT-official-response.json') -or
    [IO.File]::Exists($fullPath)) { throw 'Exclusive D-backed STATE response only' }
# Existing native framework and default Windows HTTPS/proxy settings. Redirects
# disabled; no TLS/certificate callback, proxy setting, credential, or retry.
Add-Type -AssemblyName System.Net.Http
$record = [ordered]@{status='NETWORK_OR_RESPONSE_FAILURE'; url=$Url; retries=0;
    transport='WINDOWS_SYSTEM_NET_HTTP_EXISTING_DEFAULT_SYSTEM_PROXY';
    TLS_verification='SYSTEM_DEFAULT_ENABLED'; redirects_followed=0}
$timer = [Diagnostics.Stopwatch]::StartNew()
$handler = $client = $request = $response = $stream = $memory = $cancel = $null
try {
    $handler = New-Object System.Net.Http.HttpClientHandler
    $handler.AllowAutoRedirect = $false
    $client = New-Object System.Net.Http.HttpClient($handler)
    $client.Timeout = [TimeSpan]::FromSeconds(20)
    $cancel = New-Object System.Threading.CancellationTokenSource
    $cancel.CancelAfter(20000)
    $request = New-Object System.Net.Http.HttpRequestMessage([System.Net.Http.HttpMethod]::Get, $Url)
    $request.Headers.UserAgent.ParseAdd('COIN-Funding-Semantics-ReadOnly/2')
    $request.Headers.Accept.ParseAdd('application/json')
    $response = $client.SendAsync($request, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead,
        $cancel.Token).GetAwaiter().GetResult()
    $record.http_status = [int]$response.StatusCode
    $record.final_url = $response.RequestMessage.RequestUri.AbsoluteUri
    $record.content_type = [string]$response.Content.Headers.ContentType
    $stream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
    $memory = New-Object IO.MemoryStream
    $buffer = New-Object byte[] 4096
    do {
        $amount = [Math]::Min(4096, 64001 - [int]$memory.Length)
        if ($amount -le 0) { throw 'Fixed 64KB official response limit exceeded' }
        $read = $stream.ReadAsync($buffer, 0, $amount, $cancel.Token).GetAwaiter().GetResult()
        if ($read -gt 0) { $memory.Write($buffer, 0, $read) }
    } while ($read -gt 0)
    if ($memory.Length -gt 64000) { throw 'Fixed 64KB official response limit exceeded' }
    [IO.File]::WriteAllBytes($fullPath, $memory.ToArray())
    $record.bytes = [int]$memory.Length
    $record.status = if ($record.http_status -eq 200) {'RETRIEVED'} else {'HTTP_FAILURE'}
} catch {
    $record.error_type = $_.Exception.GetType().FullName
    $record.reason = $_.Exception.Message
} finally {
    $record.elapsed_seconds = $timer.Elapsed.TotalSeconds
    $record.response_body_bytes = if ($null -ne $memory) {[int]$memory.Length} else {0}
    $record.network_byte_scope = 'RESPONSE_BODY_BYTES_ONLY_HEADERS_TLS_WIRE_BYTES_NOT_MEASURED'
    foreach ($item in @($stream,$memory,$response,$request,$client,$handler,$cancel)) {
        if ($null -ne $item) {$item.Dispose()}
    }
    $record.WindowsPeakWorkingSet64 = [Diagnostics.Process]::GetCurrentProcess().PeakWorkingSet64
    $record.memory_scope = 'CURRENT_WINDOWS_TRANSPORT_PROCESS_ONLY'
}
[Console]::Out.WriteLine(($record | ConvertTo-Json -Compress))
if ($record.status -eq 'RETRIEVED') {exit 0} else {exit 1}
