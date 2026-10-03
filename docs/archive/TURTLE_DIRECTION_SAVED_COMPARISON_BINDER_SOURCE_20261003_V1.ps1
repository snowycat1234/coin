$ErrorActionPreference='Stop'
$rootPath='D:\codex\coin'
$protocolPath='protocols/TURTLE_DIRECTION_ABLATION_20261003_V1.json'
$marketPath='reports/fast_research/TURTLE_DIRECTION_ABLATION_ACTUAL_20261003_V1.json'
$financePath='reports/fast_research/TURTLE_DIRECTION_FINANCIAL_INDEPENDENT_20261003_V1.json'
$planPath='protocols/TURTLE_DIRECTION_SAVED_COMPARISON_BINDING_20261003_V1.json'
$helperPath='scripts/investment/turtle_direction_saved_comparison.py'
function HashFile([string]$path){(Get-FileHash -LiteralPath (Join-Path $rootPath $path) -Algorithm SHA256).Hash.ToLowerInvariant()}
function SmallJson([string]$path){Get-Content -LiteralPath (Join-Path $rootPath $path) -Raw|ConvertFrom-Json -AsHashtable -DateKind String}
$spec=SmallJson $protocolPath;$market=SmallJson $marketPath;$finance=SmallJson $financePath
if($market.completed_cases -ne 8 -or $finance.completed_cases_verified -ne 8){throw 'Eight actual cases required'}
$pins=@{}
foreach($map in @($spec.frozen_sources,$finance.binding.source_hashes)){
    foreach($name in $map.Keys){
        if($name -eq 'state/dataset_lock.json'){throw 'Private lock export forbidden'}
        if($pins.ContainsKey($name) -and $pins[$name] -ne $map[$name]){throw 'Conflicting pins'}
        if((HashFile $name) -ne $map[$name]){throw ('Source changed: '+$name)}
        $pins[$name]=$map[$name]
    }
}
$extras=@($helperPath,$protocolPath,$marketPath,$financePath,
    'docs/archive/TURTLE_DIRECTION_SAVED_COMPARISON_SOURCE_20261003_V1.py',
    'docs/archive/TURTLE_DIRECTION_SAVED_COMPARISON_BINDER_SOURCE_20261003_V1.ps1',
    'scripts/investment/closing_exempt_saved_comparison.py',
    'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py',
    'scripts/investment/compare_perpetual_213_results.py',
    'reports/fast_research/CLOSING_EXEMPT_RESEARCH_ACTUAL_20261003_V1.json',
    'reports/fast_research/CLOSING_EXEMPT_SAVED_COMPARISON_20261003_V1.json')
foreach($name in $extras){$pins[$name]=HashFile $name}
if($pins[$helperPath] -ne 'f850671b01b3c809ef9a27ce798cffc91ef94c0d1a1b13eae9a385fd1d0a7197'){throw 'Held helper changed'}
$plan=@{
    ready_to_execute=$true;created_utc=[DateTimeOffset]::UtcNow.ToString('o')
    contract_id='D049_TURTLE_DIRECTION_SAVED_COMPARISON_V1';helper_sha256=$pins[$helperPath]
    budgets=@{new_owned_bytes=5000000;peak_RSS_bytes=1000000000;wall_seconds=120}
    run_dir='/home/xflops/coin-state/d049-turtle-direction-saved-comparison-20261003-v1'
    output_path='reports/fast_research/TURTLE_DIRECTION_SAVED_COMPARISON_20261003_V1.json'
    market_protocol=@{path=$protocolPath;sha256=$pins[$protocolPath]}
    roles=@{
        MARKET=@{path=$marketPath;sha256=$pins[$marketPath];required_status=$market.status;task_id=$market.binding.task_id}
        INDEPENDENT=@{path=$financePath;sha256=$pins[$financePath];required_status=$finance.status;task_id=$finance.binding.task_id}
    }
    frozen_sources=$pins
    local_non_git_hash_guard=@{'state/dataset_lock.json'='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'}
    market_ledger_IO=$false;old_accounts_replayed=$false;selected_direction_or_unit=$false
}
$absolute=Join-Path $rootPath $planPath
if(Test-Path -LiteralPath $absolute){throw 'Exclusive new comparison protocol required'}
[IO.File]::WriteAllText($absolute,($plan|ConvertTo-Json -Depth 60)+"`n",[Text.UTF8Encoding]::new($false))
Write-Output (HashFile $planPath)
