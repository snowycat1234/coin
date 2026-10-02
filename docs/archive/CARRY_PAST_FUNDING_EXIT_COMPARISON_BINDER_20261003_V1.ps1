param([Parameter(Mandatory=$true)][string]$AuditHost)
$ErrorActionPreference='Stop'
$projectRoot='D:\codex\coin'
$master='protocols/CARRY_PAST_FUNDING_EXIT_D032_20261003_V1.json'
$auditPath='reports/fast_research/CARRY_PAST_FUNDING_EXIT_TWO_PERIOD_DECIMAL_AUDIT_20261003_V1.json'
$helper='scripts/investment/compare_carry_past_funding_exit.py'
$selfArchive='docs/archive/CARRY_PAST_FUNDING_EXIT_COMPARISON_BINDER_20261003_V1.ps1'
function Digest([string]$path){(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower()}
function WriteNew([string]$path,$value){
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($value|ConvertTo-Json -Depth 40)+"`n")
    $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew)
    try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
}
function ReadClosed($report){
    $taskPath='/home/xflops/coin-state/task-progress/task-'+$report.binding.task_id+'.json'
    $raw=& wsl.exe -d hpc_linux -- cat -- $taskPath
    if($LASTEXITCODE -ne 0){throw 'Task unavailable'}
    $value=($raw -join "`n")|ConvertFrom-Json
    if($value.id -ne $report.binding.task_id -or $value.status -ne 'completed' -or $value.exit_code -ne 0){throw 'Task not closed0'}
    return $value
}
if((Digest $PSCommandPath) -ne (Digest (Join-Path $projectRoot $selfArchive))){throw 'Binder archive changed'}
$spec=Get-Content -LiteralPath (Join-Path $projectRoot $master) -Raw|ConvertFrom-Json
$audit=Get-Content -LiteralPath (Join-Path $projectRoot $auditPath) -Raw|ConvertFrom-Json
if($audit.status -ne 'PASS_D032_TWO_PERIOD_DECIMAL_CONDITIONAL_ACCOUNTING_NOT_NATIVE_OR_LONG_TERM_APR' -or $audit.completed_cases_verified -ne 2){throw 'Independent audit incomplete'}
$auditTask=ReadClosed $audit
$value=[ordered]@{contract_id='D032_ECONOMIC_COMPARISON_BINDING_V1';scope='POST_RESULT_CONDITIONAL_ATTRIBUTION_NOT_CASHFLOW_OR_TRADING_SIGNAL';
    reader_authorized=$true;reader_authorization='Root autonomous authorized research: saved actually owned coupon attribution only after two new actual and independent actual exit0';
    helper_sha256=(Digest (Join-Path $projectRoot $helper));master_protocol_sha256=(Digest (Join-Path $projectRoot $master));
    audit_sha256=(Digest (Join-Path $projectRoot $auditPath));gate_rules=$spec.gate_rules;adoption_criteria=$spec.adoption_criteria;
    audit_host_result=$AuditHost;actual_audit_task=$auditTask;cases=@();
    source_change_before_comparison_freeze='Two static guards tightened: original ratio tolerance for Decimal/Float agreement; all prior risk rules must match. No executed comparison overwritten.';
    binder_archive=$selfArchive;binder_sha256=(Digest (Join-Path $projectRoot $selfArchive));
    no_old_NAV_IO=$true;no_old_account_or_source_QA_replay=$true;locked_consumed=$false}
$controls=@{'122D'='reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_122D_ACTUAL_20261003_V1.json';'90D'='reports/fast_research/CARRY_90D_PAIR_TRIM_ACTUAL_20261003_V1.json'}
foreach($period in @('122D','90D')){
    $relative="reports/fast_research/CARRY_PAST_FUNDING_EXIT_${period}_ACTUAL_20261003_V1.json"
    $actual=Get-Content -LiteralPath (Join-Path $projectRoot $relative) -Raw|ConvertFrom-Json
    $control=Get-Content -LiteralPath (Join-Path $projectRoot $controls[$period]) -Raw|ConvertFrom-Json
    $task=ReadClosed $actual
    if($auditTask.started_at -lt $task.ended_at){throw 'Audit before actual closure'}
    $proof=@($audit.cases|Where-Object period -eq $period)
    if($proof.Count -ne 1 -or $proof[0].actual_report_sha256 -ne (Digest (Join-Path $projectRoot $relative))){throw 'Wrong audited new report'}
    $outputs=[ordered]@{}
    foreach($row in $control.output_bindings){$outputs[$row.kind]=[ordered]@{path=$row.path;sha256=$row.sha256;bytes=$row.bytes;rows=$row.rows}}
    if($outputs.Count -ne 4){throw 'Wrong saved control output count'}
    $value.cases += [ordered]@{period=$period;new_actual_sha256=(Digest (Join-Path $projectRoot $relative));frozen_control_outputs=$outputs;actual_task=$task}
}
$out=Join-Path $projectRoot 'protocols/CARRY_PAST_FUNDING_EXIT_COMPARISON_BINDING_20261003_V1.json'
WriteNew $out $value
[ordered]@{status='FROZEN_ACTUAL_CLOSED0_COMPARISON_AND_CONDITIONAL_COUPON_READ_SCOPE';binding_sha256=(Digest $out);helper_sha256=$value.helper_sha256;audit_sha256=$value.audit_sha256}|ConvertTo-Json
