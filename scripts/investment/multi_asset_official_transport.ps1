param([Parameter(Mandatory=$true)][string]$Url,
      [Parameter(Mandatory=$true)][string]$OutputPath,
      [Parameter(Mandatory=$true)][int]$MaximumBytes)
$ErrorActionPreference='Stop'
# Default Windows HTTPS is the minimal replacement for WSL Errno101. JSON/CSV,
# CHECKSUM verification and scientific parsing are exclusively bounded WSL.
if ($Url -cnotmatch '^https://data\.binance\.vision/data/futures/um/monthly/(?:klines/[A-Z0-9]{2,24}USDT/(?:1d|1m)/[A-Z0-9]{2,24}USDT-(?:1d|1m)-2024-0[2-9]|markPriceKlines/[A-Z0-9]{2,24}USDT/1m/[A-Z0-9]{2,24}USDT-1m-2024-09|fundingRate/[A-Z0-9]{2,24}USDT/[A-Z0-9]{2,24}USDT-fundingRate-2024-09)\.zip(?:\.CHECKSUM)?$') {
    throw 'Only fixed official first-period USD-M archives/checksums'
}
if ($MaximumBytes -notin @(4096,64000,16000000)) {throw 'Registered per-response byte bound'}
$root='\\wsl.localhost\hpc_linux\home\xflops\coin-state\'
$fullPath=[IO.Path]::GetFullPath($OutputPath)
$suffix=$fullPath.Substring($root.Length)
if (!$fullPath.StartsWith($root,[StringComparison]::OrdinalIgnoreCase) -or
    $suffix -cnotmatch '^d050-multiasset-(pool|market-source)-20261004-v[1-9][0-9]*\\' -or
    [IO.File]::Exists($fullPath) -or [IO.Path]::GetFileName($fullPath) -cne ([Uri]$Url).Segments[-1]) {
    throw 'Exclusive D-backed own first-period source file'
}
Add-Type -AssemblyName System.Net.Http
$record=[ordered]@{status='NETWORK_OR_RESPONSE_FAILURE';url=$Url;retries=0;
    transport='WINDOWS_DEFAULT_SYSTEM_HTTPS';TLS_verification='SYSTEM_DEFAULT_ENABLED';redirects_followed=0}
$timer=[Diagnostics.Stopwatch]::StartNew()
$handler=$client=$request=$response=$stream=$file=$cancel=$null
try {
    $handler=New-Object System.Net.Http.HttpClientHandler
    $handler.AllowAutoRedirect=$false
    $client=New-Object System.Net.Http.HttpClient($handler)
    $client.Timeout=[TimeSpan]::FromSeconds(20)
    $cancel=New-Object System.Threading.CancellationTokenSource
    $cancel.CancelAfter(20000)
    $request=New-Object System.Net.Http.HttpRequestMessage([System.Net.Http.HttpMethod]::Get,$Url)
    $request.Headers.UserAgent.ParseAdd('COIN-Official-Source/1')
    $response=$client.SendAsync($request,[System.Net.Http.HttpCompletionOption]::ResponseHeadersRead,
        $cancel.Token).GetAwaiter().GetResult()
    $record.http_status=[int]$response.StatusCode
    $record.final_url=$response.RequestMessage.RequestUri.AbsoluteUri
    $stream=$response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
    $file=[IO.File]::Open($fullPath,[IO.FileMode]::CreateNew)
    $buffer=New-Object byte[] 65536
    $total=0
    do {
        $amount=[Math]::Min(65536,$MaximumBytes+1-$total)
        if ($amount -le 0) {throw 'Fixed official source byte limit'}
        $read=$stream.ReadAsync($buffer,0,$amount,$cancel.Token).GetAwaiter().GetResult()
        if ($read -gt 0) {$total+=$read;$file.Write($buffer,0,$read)}
    } while ($read -gt 0)
    if ($total -gt $MaximumBytes) {throw 'Fixed official source byte limit'}
    $record.bytes=$total
    $record.status=if ($record.http_status -eq 200) {'RETRIEVED'} else {'HTTP_FAILURE'}
} catch {
    $record.error_type=$_.Exception.GetType().FullName
    $record.reason=$_.Exception.Message
} finally {
    $record.elapsed_seconds=$timer.Elapsed.TotalSeconds
    foreach ($item in @($file,$stream,$response,$request,$client,$handler,$cancel)) {
        if ($null -ne $item) {$item.Dispose()}
    }
    $record.WindowsPeakWorkingSet64=[Diagnostics.Process]::GetCurrentProcess().PeakWorkingSet64
    $record.memory_scope='CURRENT_WINDOWS_TRANSPORT_PROCESS_ONLY'
}
[Console]::Out.WriteLine(($record | ConvertTo-Json -Compress))
if ($record.status -eq 'RETRIEVED') {exit 0} else {exit 1}
