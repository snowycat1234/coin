$ErrorActionPreference = 'Stop'
$env:GIT_TERMINAL_PROMPT = '0'
$env:GCM_INTERACTIVE = 'never'
$remoteHost = [uri]'https://github.com'
$proxyAddress = [System.Net.WebRequest]::GetSystemWebProxy().GetProxy($remoteHost)
$readArgs = @('-C','D:/codex/coin','-c','credential.helper=','-c','credential.helper=!wsl.exe -d hpc_linux --cd D:/codex/coin -- scripts/bounded.sh .tools/bin/gh auth git-credential','-c','http.version=HTTP/1.1','-c','http.lowSpeedTime=30','-c','http.lowSpeedLimit=1')
if ($proxyAddress.AbsoluteUri -ne $remoteHost.AbsoluteUri) {
    $readArgs += @('-c', ('http.proxy=' + $proxyAddress.AbsoluteUri))
}
$readArgs += @('ls-remote','origin','refs/heads/main')
& 'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe' @readArgs
exit $LASTEXITCODE
