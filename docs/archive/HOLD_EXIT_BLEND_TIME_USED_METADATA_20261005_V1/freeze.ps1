$ErrorActionPreference = 'Stop'
$root = 'D:/codex/coin'
$out = "$root/protocols/HOLD_EXIT_BLEND_TIME_20261005_V1.json"
if (Test-Path -LiteralPath $out) { throw 'Protocol exists' }
$p = Get-Content -LiteralPath "$root/protocols/DONCHIAN_TIME_STABILITY_20261005_V1.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$p.experiment_id = 'D074-HOLD-EXIT-BLEND-TIME-20261005-V1'
$p.git_parent = '748b4bc1d80fdba5c2f9b794b91f1ada9ed82810'
$p.question = 'Does the fixed shared-wallet blend versus HOLD8 reduce drawdown across time, or depend on a few seen intervals?'
$p.decision = 'No stability or independent alpha claim if intervals include zero or tranches reverse; retain defensive capability only, without weight search or investment promotion.'
$p | Add-Member -NotePropertyName include_drawdown_episodes -NotePropertyValue $true
$p | Add-Member -NotePropertyName drawdown_semantics -NotePropertyValue 'Daily endpoint episodes; initial capital at start_us; real endpoint clocks for duration; equality recovers/updates latest peak; recovery excluded from underwater count; unresolved endings right censored; not minute MDD.'
function Digest([string]$path) { $alg=[Security.Cryptography.SHA256]::Create(); try { return ([BitConverter]::ToString($alg.ComputeHash([IO.File]::ReadAllBytes($path)))).Replace('-','').ToLowerInvariant() } finally { $alg.Dispose() } }
function Receipt([string]$name) { return @{ path='/mnt/d/codex/coin/'+$name; sha256=(Digest "$root/$name") } }
$p.baseline_report = Receipt 'reports/fast_research/HOLD_RISK8_20261005_V1.json'
$p.challenger_report = Receipt 'reports/fast_research/HOLD_EXIT_BLEND_20261005_V1.json'
$p.accepted_financial_reports = @((Receipt 'reports/fast_research/HOLD_RISK8_20261005_V1_FINANCIAL.json'), (Receipt 'reports/fast_research/HOLD_EXIT_BLEND_20261005_V1_FINANCIAL.json'))
$p.accepted_pair_diagnostic = Receipt 'reports/fast_research/HOLD_EXIT_BLEND_20261005_V1_DIAGNOSTIC.json'
foreach ($prop in $p.source_hashes.PSObject.Properties) { $prop.Value=(Digest "$root/$($prop.Name)") }
$p.created_utc = [DateTime]::UtcNow.ToString('o')
$encoding = New-Object System.Text.UTF8Encoding($false)
$pre = @'

## D074运行前决定：保存连续日账本的配对回撤与时间依赖

D073固定组合比HOLD8略少收益、较低实际波动与回撤，但November贡献超过全期净收益。只读四条件八份已接受日NAV，复用既有时间诊断和块bootstrap，加入真实endpoint时钟、起始10k及未恢复右删失的每日回撤片段。对照HOLD8；固定三段101日、十月、7/30/60日块（60为主要描述）、每条件每块2000抽样、seed20261005。24k抽样不增加历史，不修正此前选择偏差；实际risk不同，不宣称匹配风险alpha或稳定APR。
预算：0新市场账户/模型/HPO/API/下载/QA，8×303行；主体RSS600MB/wall120s/output1MB，共享5GB/swap0/GPU0与D40GB不变。仅一次保存账本诊断及独立Scalar/Decimal/边界核验；遇日期/身份/现金桥/positiveNAV/资源错误即保留失败停止。原303日已见开发历史、资金单位F/P和跨场所代理条件保持，不搜索混合权重或挑日期。
决定：区间含零或固定段反转则不声称持续净增量；较低历史回撤只保留防御挑战者，不能当稳定独立收益。依据实际结果决定下一主任务，不再机械新增参数实验。
'@
[IO.File]::AppendAllText("$root/docs/RESEARCH_DECISION_LOG.md", $pre+"`n", $encoding)
[IO.File]::WriteAllText($out, ($p|ConvertTo-Json -Depth 15)+"`n", $encoding)
Write-Output (Digest $out)
