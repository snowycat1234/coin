$ErrorActionPreference='Stop'
Set-Location 'D:/codex/coin'
function TaskDigest([string]$Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
$failure='docs/archive/PUBLIC_DONCHIAN_DAILY_ROOT_METADATA_FAILURE_20261003_V1.json'
$proof=[ordered]@{status='ACTUAL_ROOT_METADATA_FAILURE_BEFORE_ACCEPTANCE_NOT_ECONOMIC_FAILURE';task_id='2ca06a5cd25048c09f53fd997b4bc62e';session_id=31133;host_final_chunk='4fbeaf';exit_code=1;helper='docs/archive/PUBLIC_DONCHIAN_DAILY_ROOT_CLOSE_SOURCE_20261003_V1.py';helper_sha256=TaskDigest 'docs/archive/PUBLIC_DONCHIAN_DAILY_ROOT_CLOSE_SOURCE_20261003_V1.py';protocol='protocols/PUBLIC_DONCHIAN_DAILY_ROOT_BINDING_20261003_V1.json';protocol_sha256=TaskDigest 'protocols/PUBLIC_DONCHIAN_DAILY_ROOT_BINDING_20261003_V1.json';error_type='ValueError';reason='Owned directory contains no symlink';read_only_symlink_inspection_host_chunk='73986f';actual_link='/home/xflops/coin-state/d037-public-daily-smoke-20261003-v1/pytest/test_daily_public_native_routecurrent';actual_target='/home/xflops/coin-state/d037-public-daily-smoke-20261003-v1/pytest/test_daily_public_native_route0';all_other_six_owned_directories_had_no_links=$true;market_accounts_or_QA_replayed=$false;root_acceptance_written=$false;disk_guard_changed=$false}
if(Test-Path -LiteralPath $failure){throw 'Exclusive failure proof'}
[IO.File]::WriteAllText((Join-Path (Get-Location) $failure),($proof|ConvertTo-Json -Depth 8)+"`n",[Text.UTF8Encoding]::new($false))
$factory='docs/archive/PUBLIC_DONCHIAN_DAILY_ROOT_METADATA_REPAIR_SOURCE_20261003_V2.ps1'
if(Test-Path -LiteralPath $factory){throw 'Exclusive repair archive'}
[IO.File]::WriteAllBytes((Join-Path (Get-Location) $factory),[IO.File]::ReadAllBytes($PSCommandPath))
$helper='.cache/d037_root_close_20261003_v2.py';$archive='docs/archive/PUBLIC_DONCHIAN_DAILY_ROOT_CLOSE_SOURCE_20261003_V2.py'
$txt=[IO.File]::ReadAllText((Join-Path (Get-Location) '.cache/d037_root_close_20261003_v1.py'))
$txt=$txt.Replace('PUBLIC_DONCHIAN_DAILY_ROOT_CLOSE_SOURCE_20261003_V1.py','PUBLIC_DONCHIAN_DAILY_ROOT_CLOSE_SOURCE_20261003_V2.py').Replace('PUBLIC_DONCHIAN_DAILY_ROOT_ACCEPTANCE_20261003_V1.json','PUBLIC_DONCHIAN_DAILY_ROOT_ACCEPTANCE_20261003_V2.json').Replace('GITHUB_PUBLIC_DONCHIAN_DAILY_SOURCE_BINDING_20261003_V1.json','GITHUB_PUBLIC_DONCHIAN_DAILY_SOURCE_BINDING_20261003_V2.json').Replace('PUBLIC_DONCHIAN_DAILY_USED_ACTUAL_METADATA_20261003_V1','PUBLIC_DONCHIAN_DAILY_USED_ACTUAL_METADATA_20261003_V2')
$old="    files=list(p.rglob('*'));check(not p.is_symlink() and not any(f.is_symlink() for f in files),'Owned directory contains no symlink')"
$replacement=@'
    files=list(p.rglob('*'));check(not p.is_symlink(),'Owned root must be a real directory')
    for f in files:
        if f.is_symlink():
            expected=STATE/'d037-public-daily-smoke-20261003-v1/pytest/test_daily_public_native_routecurrent'
            target=STATE/'d037-public-daily-smoke-20261003-v1/pytest/test_daily_public_native_route0'
            check(f==expected and p==expected.parent.parent and f.resolve(strict=True)==target and target.is_dir()
                and not target.is_symlink() and target.is_relative_to(p),'Only exact same-owned pytest current alias')
'@
if(-not $txt.Contains($old)){throw 'Unique exact frozen metadata selector'}
$txt=$txt.Replace($old,$replacement)
if((Test-Path -LiteralPath $helper) -or (Test-Path -LiteralPath $archive)){throw 'Exclusive repair entry'}
[IO.File]::WriteAllText((Join-Path (Get-Location) $helper),$txt,[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllBytes((Join-Path (Get-Location) $archive),[IO.File]::ReadAllBytes((Join-Path (Get-Location) $helper)))
$plan=Get-Content protocols/PUBLIC_DONCHIAN_DAILY_ROOT_BINDING_20261003_V1.json -Raw|ConvertFrom-Json -AsHashtable
$plan.helper_sha256=TaskDigest $archive
$plan.project_sources[$factory]=TaskDigest $factory
$plan.project_sources['docs/archive/PUBLIC_DONCHIAN_DAILY_ROOT_CLOSE_SOURCE_20261003_V1.py']=TaskDigest 'docs/archive/PUBLIC_DONCHIAN_DAILY_ROOT_CLOSE_SOURCE_20261003_V1.py'
$plan.project_sources['protocols/PUBLIC_DONCHIAN_DAILY_ROOT_BINDING_20261003_V1.json']=TaskDigest 'protocols/PUBLIC_DONCHIAN_DAILY_ROOT_BINDING_20261003_V1.json'
$plan.preserved_failures+=@{report=$failure;report_sha256=TaskDigest $failure;task_id=$proof.task_id}
$path='protocols/PUBLIC_DONCHIAN_DAILY_ROOT_BINDING_20261003_V2.json';if(Test-Path -LiteralPath $path){throw 'Exclusive root binding'}
[IO.File]::WriteAllText((Join-Path (Get-Location) $path),($plan|ConvertTo-Json -Depth 14)+"`n",[Text.UTF8Encoding]::new($false))
[ordered]@{binding=$path;sha256=TaskDigest $path;helper_sha256=TaskDigest $archive;repair_scope='Only exact known same-owned pytest directory alias; financial/disk guard unchanged'}|ConvertTo-Json -Compress
