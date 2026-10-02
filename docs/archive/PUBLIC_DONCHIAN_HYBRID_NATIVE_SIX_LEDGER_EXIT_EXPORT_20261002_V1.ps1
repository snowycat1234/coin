$ErrorActionPreference='Stop'
$repo='D:\codex\coin'
$state='\\wsl.localhost\hpc_linux\home\xflops\coin-state\test-hybrid-native-fee-independent-audit-20261002-v1'
$report=Join-Path $repo 'reports\fast_research\PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1.json'
$receipt=Join-Path $repo 'reports\fast_research\PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_AUDIT_EXIT_AND_CODE_BINDING_20261002_V1.json'
$archive=Join-Path $repo 'docs\archive\PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_CHECKER_20261002_V1.py'
$exportArchive=Join-Path $repo 'docs\archive\PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_EXIT_EXPORT_20261002_V1.ps1'
function Digest([string]$path){(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
function Need([bool]$ok,[string]$message){if(-not $ok){throw $message}}
function StatePath([string]$linux){Need ($linux.StartsWith('/home/xflops/coin-state/')) 'Only own/audit task STATE metadata'; '\\wsl.localhost\hpc_linux'+$linux.Replace('/','\')}
Need (-not (Test-Path -LiteralPath $receipt)) 'New receipt only'
Need ((Digest $report) -ceq 'a1af8448c0b44b6e79cbb0123f942bde05b773f90ebb01b0a7b751c4f23f77c9') 'Audit report frozen'
$a=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
Need ($a.status -ceq 'PASS_HYBRID_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_AND_CAUSAL_SCOPE' -and $a.completed_ledgers_verified -eq 6 -and $a.ledgers.Count -eq 6) 'Six new independent ledger blocks'
Need ((Digest (Join-Path $state 'audit.py')) -ceq $a.independent_source_sha256 -and $a.independent_source_sha256 -ceq 'd79bc8a156987786e190e606d27a1656dc059137e739cbc919780e7b12e77135') 'Frozen checker source'
$binding=Get-Content -LiteralPath (Join-Path $state 'RUN_BINDING.json') -Raw | ConvertFrom-Json
Need ((Digest (Join-Path $state 'RUN_BINDING.json')) -ceq $a.run_binding_sha256 -and $binding.task_id -ceq $a.independent_task_id -and $binding.checker_sha256 -ceq $a.independent_source_sha256) 'Actual audit RUN_BINDING'
$taskPath=Join-Path '\\wsl.localhost\hpc_linux\home\xflops\coin-state\task-progress' ('task-'+$a.independent_task_id+'.json')
$task=Get-Content -LiteralPath $taskPath -Raw | ConvertFrom-Json
Need ($task.id -ceq $a.independent_task_id -and $task.status -ceq 'completed' -and $task.exit_code -eq 0 -and $task.pid -gt 0 -and $task.start_ticks -gt 0) 'Real auditor completed0'
$parents=@()
foreach($period in $a.period_bindings){
 $rp=Join-Path $repo ([System.IO.Path]::GetFileName($period.report_path))
 $rp=Join-Path $repo ('reports\fast_research\'+[System.IO.Path]::GetFileName($period.report_path))
 Need ((Digest $rp) -ceq $period.report_sha256) 'Actual report bytes retained'
 $parent=Get-Content -LiteralPath $rp -Raw | ConvertFrom-Json
 $pt=StatePath $period.actual_task.path
 $actualTask=Get-Content -LiteralPath $pt -Raw | ConvertFrom-Json
 Need ((Digest $pt) -ceq $period.actual_task.sha256 -and $actualTask.id -ceq $parent.binding.task_id -and $actualTask.status -ceq 'completed' -and $actualTask.exit_code -eq 0 -and $actualTask.pid -gt 0 -and $actualTask.start_ticks -gt 0) 'Two parent actual completed0 bindings'
 foreach($source in $parent.binding.source_hashes.PSObject.Properties){Need ((Digest (Join-Path $repo $source.Name)) -ceq $source.Value) 'Source SHA unchanged'}
 $parents+=@{period=$period.label;report_path=$period.report_path;report_sha256=$period.report_sha256;actual_host_session_id=$period.actual_host_session_id;actual_task=$actualTask;actual_task_sha256=Digest $pt}
}
Need ($parents.Count -eq 2) 'Two explicit parent periods'
Need (-not (Test-Path -LiteralPath $archive) -and -not (Test-Path -LiteralPath $exportArchive)) 'New pure-code archives only'
Copy-Item -LiteralPath (Join-Path $state 'audit.py') -Destination $archive
Copy-Item -LiteralPath $PSCommandPath -Destination $exportArchive
Need ((Digest $archive) -ceq $a.independent_source_sha256 -and (Digest $exportArchive) -ceq (Digest $PSCommandPath)) 'Archived original pure-code bytes'
$value=@{version='PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_AUDIT_EXIT_AND_CODE_BINDING_20261002_V1';status='PASS_ACTUAL_EXIT0_AND_PURE_CODE_BYTE_BINDING';scope='Metadata and pure-code export only; zero extra ledger/raw-source/test/model reads';audit_report_path='reports/fast_research/PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1.json';audit_report_sha256=Digest $report;audit_status=$a.status;completed_ledgers_verified=6;actual_auditor_host_session_id=95966;actual_auditor_task=$task;actual_auditor_task_sha256=Digest $taskPath;run_binding_path=$a.binding.exact_command.Split(' ')[0].Replace('/audit.py','/RUN_BINDING.json');run_binding_sha256=$a.run_binding_sha256;checker_archive_path='docs/archive/PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_CHECKER_20261002_V1.py';checker_archive_sha256=Digest $archive;checker_archive_bytes=(Get-Item -LiteralPath $archive).Length;metadata_export_archive_path='docs/archive/PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_EXIT_EXPORT_20261002_V1.ps1';metadata_export_sha256=Digest $exportArchive;financial_block_sha256=$binding.financial_block_sha256;financial_block_bytes_identical=$binding.financial_block_bytes_identical;actual_manifest_sha256=$binding.actual_manifest_sha256;parent_actual_tasks=$parents;peak_RSS_bytes=$a.peak_RSS_bytes;candidate_status='NO_QUALIFIED_CANDIDATE';native_Bybit_market_or_filters_proven=$false;registry_written=$false;additional_market_tests_ledger_replays=0;created_utc=[DateTime]::UtcNow.ToString('o')}
[System.IO.File]::WriteAllText($receipt,($value | ConvertTo-Json -Depth 12),[System.Text.UTF8Encoding]::new($false))
[PSCustomObject]@{status=$value.status;receipt=$receipt;receipt_sha256=Digest $receipt;checker_archive=$archive;checker_sha256=Digest $archive;export_archive=$exportArchive;export_sha256=Digest $exportArchive} | ConvertTo-Json