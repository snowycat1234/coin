param([Parameter(Mandatory=$true)][ValidateSet('BTCUSDT','ETHUSDT')][string]$SourceName)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Net.Http
$pins=@{
  BTCUSDT=@{url='https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=BTCUSDT';limit=50000}
  ETHUSDT=@{url='https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=ETHUSDT';limit=50000}
}
$item=$pins[$SourceName]
$handler=[System.Net.Http.HttpClientHandler]::new()
$handler.AllowAutoRedirect=$false
$client=[System.Net.Http.HttpClient]::new($handler)
$client.Timeout=[TimeSpan]::FromSeconds(20)
$client.MaxResponseContentBufferSize=$item.limit
$null=$client.DefaultRequestHeaders.UserAgent.TryParseAdd('coin-pinned-official-code/1.0')
$started=[DateTimeOffset]::UtcNow
try {
  $response=$client.GetAsync($item.url).GetAwaiter().GetResult()
  $raw=$response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
  if($raw.Length -le 0 -or $raw.Length -gt $item.limit){throw 'Fixed source byte bound'}
  $digest=[System.Security.Cryptography.SHA256]::Create()
  try {$hash=([BitConverter]::ToString($digest.ComputeHash($raw))).Replace('-','').ToLowerInvariant()} finally {$digest.Dispose()}
  [ordered]@{url=$item.url;status_code=[int]$response.StatusCode;bytes=$raw.Length;sha256=$hash;started_utc=$started.ToString('o');finished_utc=[DateTimeOffset]::UtcNow.ToString('o');transport='WINDOWS_SYSTEM_HTTPS_DEFAULT_CERTIFICATE_VALIDATION_NO_CUSTOM_PROXY';peak_RAM_bytes=[Diagnostics.Process]::GetCurrentProcess().PeakWorkingSet64;body_base64=[Convert]::ToBase64String($raw)} | ConvertTo-Json -Compress
} finally {$client.Dispose();$handler.Dispose()}
