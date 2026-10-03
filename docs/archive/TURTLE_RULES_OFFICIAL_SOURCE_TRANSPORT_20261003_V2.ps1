param([Parameter(Mandatory=$true)][ValidateSet('Turtle','ATR')][string]$SourceName)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Net.Http
$pins=@{
  Turtle=@{url='https://raw.githubusercontent.com/jesse-ai/example-strategies/7c91e0a37bf62165790120d730442e4f6eb00364/TurtleRules/__init__.py';limit=65536}
  ATR=@{url='https://raw.githubusercontent.com/jesse-ai/jesse/417f8765225e3bfc12043d4b712f19fe15a3c078/jesse/indicators/atr.py';limit=16384}
}
$item=$pins[$SourceName]
$handler=[System.Net.Http.HttpClientHandler]::new()
$handler.AllowAutoRedirect=$false
$client=[System.Net.Http.HttpClient]::new($handler)
$client.Timeout=[TimeSpan]::FromSeconds(45)
$client.MaxResponseContentBufferSize=$item.limit
$null=$client.DefaultRequestHeaders.UserAgent.TryParseAdd('coin-pinned-official-code/1.0')
$started=[DateTimeOffset]::UtcNow
try {
  $response=$client.GetAsync($item.url).GetAwaiter().GetResult()
  if([int]$response.StatusCode -ne 200){throw ('Fixed source HTTP '+[int]$response.StatusCode)}
  $raw=$response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
  if($raw.Length -le 0 -or $raw.Length -gt $item.limit){throw 'Fixed source byte bound'}
  $digest=[System.Security.Cryptography.SHA256]::Create()
  try {$hash=([BitConverter]::ToString($digest.ComputeHash($raw))).Replace('-','').ToLowerInvariant()} finally {$digest.Dispose()}
  [ordered]@{url=$item.url;status_code=200;bytes=$raw.Length;sha256=$hash;started_utc=$started.ToString('o');finished_utc=[DateTimeOffset]::UtcNow.ToString('o');transport='WINDOWS_SYSTEM_HTTPS_DEFAULT_CERTIFICATE_VALIDATION_NO_CUSTOM_PROXY';body_base64=[Convert]::ToBase64String($raw)} | ConvertTo-Json -Compress
} finally {$client.Dispose();$handler.Dispose()}
