"""Exclusive metadata-first official RSI dependency installation, no market IO."""
import argparse, hashlib, json, os, resource, shlex, subprocess, sys, time, tarfile, zipfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen
from quant import resources
ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
VENDOR=ROOT/'third_party/jesse_example_rsi2'; TARGET=STATE/'rsi2-kernel-jesse-rust-1.3.0-cp312-v1'
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False)
def fetch(url,maximum):
    with urlopen(url,timeout=45) as response:data=response.read(maximum+1)
    if len(data)>maximum:raise ValueError('Bounded official payload exceeded')
    return data
p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();work=a.run_dir.resolve();out=a.output.resolve()
if work.exists() or TARGET.exists() or not VENDOR.exists() or out.exists() or not work.is_relative_to(STATE) or not out.is_relative_to(ROOT/'reports/fast_research'):raise ValueError('Exclusive vendor/target/run/report required')
if sys.prefix!=str(STATE/'v8-clean-env-20261002-v2'):raise ValueError('Accepted base clean interpreter required')
work.mkdir();binding=dict(git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),task_id=os.environ['COIN_TASK_ID'],helper_source_sha256=sha(__file__),exact_command=shlex.join([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]]),base_environment_lock_sha256=sha(ROOT/'environments/v8/uv.lock'),base_sys_prefix=sys.prefix,data_scope='OFFICIAL_LICENSED_CODE_AND_WHEEL_ONLY_SYNTHETIC_NO_MARKET',models_fit=0,GPU=0,seed='NOT_APPLICABLE')
write(work/'RUN_BINDING.json',binding);write(work/'START.json',dict(binding,status='PREBOUND_START',created_utc=datetime.now(UTC).isoformat()))
report=dict(status='FAIL_OFFICIAL_RSI_DEPENDENCY_INSTALL',binding=binding,run_dir=str(work),target=str(TARGET),vendor=str(VENDOR),market_inputs_read=False,locked_consumed=False,orders_sent=0,models_fit=0)
started=time.monotonic()
def progress(phase,done,total,unit):
    path=STATE/'task-progress'/('task-'+os.environ['COIN_TASK_ID']+'.json')
    value=json.loads(path.read_text());value.update(phase=phase,completed=done,total=total,unit=unit,last_activity_at=time.time())
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False));os.replace(temporary,path)
try:
    progress('读取官方版本和许可证元数据',0,8,'文件')
    metadata_bytes=(STATE/'rsi2-dependency-install-20261002-v1/pypi-version-metadata.json').read_bytes()
    metadata=json.loads(metadata_bytes);info=metadata['info']
    assert info['version']=='1.3.0' and 'MIT' in (info['license'] or '')
    assert 'https://github.com/jesse-ai/jesse-rust' in json.dumps(info['project_urls'])
    wheel=next(record for record in metadata['urls'] if record['filename']=='jesse_rust-1.3.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl')
    sdist=next(record for record in metadata['urls'] if record['filename']=='jesse_rust-1.3.0.tar.gz')
    assert wheel['digests']['sha256']=='65c0e9edd3af5397642ca417da2ef7c23f311d6fa2bf6a2d46c729f656528cee'
    manifest=dict(status='LICENSE_AND_VERSION_REGISTERED_BEFORE_CODE_AND_WHEEL_DOWNLOAD',created_utc=datetime.now(UTC).isoformat(),
        pypi_metadata_sha256=hashlib.sha256(metadata_bytes).hexdigest(),package_name=info['name'],package_version='1.3.0',license=info['license'],requires_python=info['requires_python'],requires_dist=info['requires_dist'],
        official_repo='https://github.com/jesse-ai/jesse-rust',official_license_url='https://raw.githubusercontent.com/jesse-ai/jesse-rust/master/LICENSE',
        example_strategy_commit='7c91e0a37bf62165790120d730442e4f6eb00364',jesse_wrapper_commit='417f8765225e3bfc12043d4b712f19fe15a3c078',
        example_strategy_license='MIT',jesse_wrapper_license='MIT',wheel=wheel,sdist=sdist,installation='UV_PIP_TARGET_NO_DEPS_NO_BASE_ENV_MUTATION',
        base_environment_lock_sha256=binding['base_environment_lock_sha256'],numpy_compatibility='REQUIRES_ACTUAL_NUMPY2_CP312_ABI_SMOKE',market_qualification=False)
    assert sha(VENDOR/'DOWNLOAD_PREBIND_20261002_V1.json')=='15c77a78b18381a62539fbeab9addf1743b5ec841e3a9b80c3d36d24db1e3e31'
    report['download_prebind_sha256']=sha(VENDOR/'DOWNLOAD_PREBIND_20261002_V1.json')
    sources=[('rsi2_original.py','https://raw.githubusercontent.com/jesse-ai/example-strategies/7c91e0a37bf62165790120d730442e4f6eb00364/RSI2/__init__.py'),
        ('LICENSE','https://raw.githubusercontent.com/jesse-ai/example-strategies/7c91e0a37bf62165790120d730442e4f6eb00364/LICENSE'),
        ('rsi_indicator_original.py','https://raw.githubusercontent.com/jesse-ai/jesse/417f8765225e3bfc12043d4b712f19fe15a3c078/jesse/indicators/rsi.py'),
        ('JESSE_LICENSE','https://raw.githubusercontent.com/jesse-ai/jesse/417f8765225e3bfc12043d4b712f19fe15a3c078/LICENSE'),
        ('JESSE_REQUIREMENTS_ORIGINAL.txt','https://raw.githubusercontent.com/jesse-ai/jesse/417f8765225e3bfc12043d4b712f19fe15a3c078/requirements.txt')]
    records={}
    for index,(name,url) in enumerate(sources,1):
        data=(VENDOR/name).read_bytes();records[name]=dict(url=url,sha256=sha(VENDOR/name),bytes=len(data),reused_saved_source=True)
        if name.endswith('LICENSE') or name=='LICENSE':assert b'MIT License' in data
        progress('保存固定官方源码和许可证',index,8,'文件')
    records.update({item['name']:item for item in json.loads((VENDOR/'RECOVERY_SOURCE_BYTES_20261002_V2.json').read_text())})
    assert b'jesse-rust==1.3.0' in (VENDOR/'JESSE_REQUIREMENTS_ORIGINAL.txt').read_bytes()
    for index,record in enumerate((wheel,sdist),6):
        payload=(STATE/'rsi2-dependency-install-20261002-v2'/record['filename']).read_bytes()
        assert hashlib.sha256(payload).hexdigest()==record['digests']['sha256'] and len(payload)==record['size']
        path=work/record['filename'];path.write_bytes(payload);progress('下载并核对官方小型包',index,8,'文件')
    with tarfile.open(work/sdist['filename'],'r:gz') as archive:
        members=archive.getmembers();matched=[member for member in members if member.name=='jesse_rust-1.3.0/src/oscillators.rs']
        assert len(matched)==1
        selection=[('rsi_kernel_original.rs',matched[0]),('KERNEL_LICENSE',next(member for member in members if member.name.count('/')==1 and member.name.endswith('/LICENSE'))),
            ('KERNEL_CARGO_ORIGINAL.toml',next(member for member in members if member.name.count('/')==1 and member.name.endswith('/Cargo.toml')))]
        for name,member in selection:
            assert member.isfile() and member.size<100000
            data=archive.extractfile(member).read();(VENDOR/name).write_bytes(data)
            records[name]=dict(sdist_sha256=sdist['digests']['sha256'],sdist_member=member.name,sha256=sha(VENDOR/name),bytes=len(data))
    assert b'MIT License' in (VENDOR/'KERNEL_LICENSE').read_bytes()
    with zipfile.ZipFile(work/wheel['filename']) as package:
        assert 'MIT' in package.read('jesse_rust-1.3.0.dist-info/METADATA').decode()
    command=[str(ROOT/'.tools/bin/uv'),'pip','install','--no-deps','--target',str(TARGET),str(work/wheel['filename'])]
    report['exact_install_command']=shlex.join(command);progress('增量安装官方包，不升级冻结环境',7,8,'文件')
    with (work/'install.log').open('x') as stream:result=subprocess.run(command,cwd=ROOT,env={**os.environ,'UV_CACHE_DIR':str(work/'uv-cache')},stdout=stream,stderr=subprocess.STDOUT,check=False)
    report['installer_exit_code']=result.returncode
    if result.returncode!=0:raise ValueError('Official fixed wheel install failed, preserve log')
    extensions=list(TARGET.rglob('*.so'));assert len(extensions)==1
    installed={str(path.relative_to(TARGET)):dict(sha256=sha(path),bytes=path.stat().st_size) for path in TARGET.rglob('*') if path.is_file()}
    installed_binding=dict(status='OFFICIAL_FIXED_WHEEL_INSTALLED_REQUIRES_SEMANTIC_SMOKE',target=str(TARGET),package_version='1.3.0',wheel_sha256=wheel['digests']['sha256'],sdist_sha256=sdist['digests']['sha256'],
        download_prebind_sha256=report['download_prebind_sha256'],original_sources=records,installed_files=installed,extension_relative_path=str(extensions[0].relative_to(TARGET)),extension_sha256=sha(extensions[0]),base_environment_lock_sha256=binding['base_environment_lock_sha256'])
    write(VENDOR/'INSTALLED_KERNEL_BINDING_20261002_V1.json',installed_binding)
    assert sha(ROOT/'environments/v8/uv.lock')==binding['base_environment_lock_sha256']
    report.update(status='PASS_OFFICIAL_FIXED_RSI_CODE_WHEEL_INSTALL_NOT_YET_SEMANTIC_ACCEPTANCE',installed_binding_sha256=sha(VENDOR/'INSTALLED_KERNEL_BINDING_20261002_V1.json'),installed_binding=installed_binding,base_environment_unmodified=True)
    progress('已安装，等待NumPy2与官方语义实测',8,8,'文件')
except Exception as error:
    report.update(error_type=type(error).__name__,reason=str(error));raise
finally:
    report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,owned_bytes=sum(path.stat().st_size for directory in (work,TARGET,VENDOR) if directory.exists() for path in directory.rglob('*') if path.is_file()),resources=resources.status())
    write(out,report);print(json.dumps(dict(status=report['status'],output=str(out),sha256=sha(out))))

