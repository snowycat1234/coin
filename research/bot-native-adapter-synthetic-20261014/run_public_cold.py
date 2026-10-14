"""Manifest-first, bounded generated-only native-grid portable cold checks."""
from __future__ import annotations
import argparse,hashlib,json,os,pathlib,re,resource,signal,subprocess,sys,time
HERE=pathlib.Path(__file__).resolve().parent
AS=4*1024**3;RSS_STOP=2*1024**3;CPU_SECONDS=180;WALL_SECONDS=240;OUTPUT_BYTES=24*1024**2

def require(ok,reason):
    if not ok:raise ValueError(reason)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def relative(name):
    p=pathlib.PurePosixPath(name);require(not p.is_absolute() and '..' not in p.parts and str(p)==name,'UNSAFE_MEMBER_PATH');return pathlib.Path(name)
def verified_body(name,row):
    p=HERE/relative(name);require(not p.is_symlink() and p.resolve().is_relative_to(HERE),'UNSAFE_MEMBER_LINK')
    raw=p.read_bytes();require(len(raw)==row['bytes'] and sha(raw)==row['SHA256'],'PUBLIC_MEMBER_IDENTITY_'+name);return raw

def verify(expected):
    require(re.fullmatch('[0-9a-f]{64}',expected) is not None,'EXACT_PUBLIC_MANIFEST_SHA256_REQUIRED')
    raw=(HERE/'PUBLIC_PAYLOAD_MANIFEST.json').read_bytes();require(sha(raw)==expected,'PUBLIC_MANIFEST_IDENTITY')
    manifest=json.loads(raw);require(manifest['schema']=='NATIVE_GRID_SYNTHETIC_PORTABLE_PUBLIC_PAYLOAD_V1','PUBLIC_SCHEMA')
    require(manifest['historical_GO'] is False and manifest['original26_historical_closure_admitted'] is False,'PUBLIC_SCOPE')
    require(all(not name.endswith(('.npz','.npy','.zip')) for name in manifest['files']),'HISTORICAL_ARRAY_OR_PACKAGE_BODY_REFUSED')
    for name,row in manifest['files'].items():verified_body(name,row)
    portable=manifest['portable_source_freeze'];freeze_path=HERE/relative(portable['path'])
    require(sha(freeze_path.read_bytes())==portable['SHA256'],'PORTABLE_SOURCE_FREEZE_IDENTITY')
    catalog=json.loads((HERE/'ORIGINAL_CODE_CARRIER.json').read_text())
    for row in catalog['files']:
        require(row['repository']=='snowycat1234/coin' and re.fullmatch('[0-9a-f]{40}',row['commit']) is not None,'IMMUTABLE_PUBLIC_SOURCE_REF')
        data=verified_body(row['public_relative_path'],row)
        require(hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['GitBlobSHA1'],'ORIGINAL_GIT_BLOB_IDENTITY')
    return {'public_manifest_SHA256':expected,'public_members_verified':len(manifest['files']),'portable_source_freeze_SHA256':portable['SHA256'],'original_public_code_blobs_verified':len(catalog['files']),'historical_GO':False},HERE/relative(manifest['portable_directory'])

def limit_child():
    resource.setrlimit(resource.RLIMIT_AS,(AS,AS));resource.setrlimit(resource.RLIMIT_CPU,(CPU_SECONDS,CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_FSIZE,(OUTPUT_BYTES,OUTPUT_BYTES));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})

def group_rss(group):
    total=0
    for p in pathlib.Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            if os.getpgid(int(p.name))!=group:continue
            for line in (p/'status').read_text().splitlines():
                if line.startswith('VmRSS:'):total+=int(line.split()[1])*1024;break
        except (OSError,ValueError):pass
    return total

def output_size(root):return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
def bounded(stage,cwd,argv,env,out):
    start=time.monotonic();peak=0;stop=None
    with (out/(stage+'.txt')).open('x') as log:
        child=subprocess.Popen([sys.executable,'-B',*argv],cwd=cwd,env=env,preexec_fn=limit_child,start_new_session=True,stdout=log,stderr=subprocess.STDOUT)
        while child.poll() is None:
            peak=max(peak,group_rss(child.pid))
            if peak>RSS_STOP:stop='PROCESS_GROUP_RSS_LIMIT'
            elif time.monotonic()-start>WALL_SECONDS:stop='PROCESS_GROUP_WALL_LIMIT'
            elif output_size(out)>OUTPUT_BYTES:stop='TOTAL_OUTPUT_LIMIT'
            if stop:
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                break
            time.sleep(.05)
        code=child.wait()
    return {'stage':stage,'exit_code':code,'stop_reason':stop,'wall_seconds':time.monotonic()-start,'sampled_group_peak_RSS_bytes':peak}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--expected-manifest-sha256',required=True);parser.add_argument('--runtime-site',action='append',required=True);parser.add_argument('--output-directory',type=pathlib.Path,required=True)
    args=parser.parse_args()
    require(sys.platform.startswith('linux') and sys.version_info[:3]==(3,12,14),'EXACT_PYTHON31214_LINUX_RESOURCE_RUNTIME_REQUIRED')
    clean=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',POLARS_MAX_THREADS='1')
    clean.pop('PYTHONOPTIMIZE',None);clean.pop('PYTHONPATH',None);clean.pop('BOT_NATIVE_RUNTIME_SITES',None)
    if not __debug__:os.execve(sys.executable,[sys.executable,'-B',str(pathlib.Path(__file__).resolve()),*sys.argv[1:]],clean)
    identity,candidate=verify(args.expected_manifest_sha256)
    out=args.output_directory.resolve();require(not out.exists() and not out.is_symlink(),'OUTPUT_MUST_BE_NEW')
    require(not out.is_relative_to(candidate),'OUTPUT_MUST_BE_OUTSIDE_PORTABLE_SOURCE')
    sites=[str(pathlib.Path(x).resolve()) for x in args.runtime_site];require(all(pathlib.Path(x).is_dir() for x in sites),'EXPLICIT_RUNTIME_SITE_MISSING')
    out.mkdir(parents=True,exist_ok=False);env=dict(clean,BOT_NATIVE_RUNTIME_SITES=json.dumps(sites),PYTHONPATH=os.pathsep.join(sites))
    check_args=['portable_checks.py','--output-directory',str(out/'fresh_generated')]
    for site in sites:check_args+=['--runtime-site',site]
    # The old reviewer file keeps its original locator; only a nonexistent path is
    # inserted there. Explicit fresh candidate binding prevents warm-source fallback.
    review=HERE/'coin_bot_native_independent_review_20261014/test_native_adversarial.py'
    independent="import pathlib,sys,unittest\np=pathlib.Path(sys.argv[1]).resolve();sys.path.insert(0,str(p))\nfrom bind_sources import verify_code_only,configure_runtime\nverify_code_only();configure_runtime(__import__('json').loads(__import__('os').environ['BOT_NATIVE_RUNTIME_SITES']))\nimport native_adapter,bind_sources\nif pathlib.Path(native_adapter.__file__).resolve()!=p/'native_adapter.py' or pathlib.Path(bind_sources.__file__).resolve()!=p/'bind_sources.py':raise SystemExit('WRONG_PORTABLE_CANDIDATE_ORIGIN')\ns=pathlib.Path(sys.argv[2]);raw=s.read_bytes()\nif __import__('hashlib').sha256(raw).hexdigest()!='2219b171dac07b15e5a31669d16f942a09910ba123dc0aee59586c893678f59a':raise SystemExit('INDEPENDENT_SUITE_IDENTITY')\nns={'__name__':'verified_independent_suite','__file__':str(s)};exec(compile(raw,str(s),'exec'),ns)\nr=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ns['NativeAdversarial']))\nraise SystemExit(0 if r.wasSuccessful() else 1)"
    math_suite=HERE/'portable_independent_review/test_portable_math.py'
    math_command=independent.replace("'2219b171dac07b15e5a31669d16f942a09910ba123dc0aee59586c893678f59a'","\'36d1f1dd144aaf748b5b9f31fc0a154b58c1114bcbf38baab88571efe119a18a\'").replace("ns['NativeAdversarial']","ns['PortableMathematicalTests']")
    stages=[('complete_journal_comparison_5_tests',HERE,['test_complete_journal_parity.py']),('saved_transport_4_tests',HERE,['saved_generated_journals/test_journal_transport.py']),('portable_binding_and_20_tests_and_33_exports',candidate,check_args),('independent_7_math_transport_tests',HERE,['-c',math_command,str(candidate),str(math_suite)]),('unchanged_independent_26_tests',HERE,['-c',independent,str(candidate),str(review)]),('exact_33_body_parity_and_decimal_audit',HERE,['audit_public_journals.py','--candidate-output',str(out/'fresh_generated'),'--output',str(out/'fresh_decimal_audit')])]
    records=[]
    for stage,cwd,argv in stages:
        records.append(bounded(stage,cwd,argv,env,out))
        if records[-1]['exit_code'] or records[-1]['stop_reason']:break
    after,_=verify(args.expected_manifest_sha256);unchanged=after==identity
    passed=len(records)==len(stages) and unchanged and all(x['exit_code']==0 and x['stop_reason'] is None for x in records)
    receipt={'status':'PASS_BOUNDED_SYNTHETIC_ONLY_PORTABLE_COLD' if passed else 'FAIL_PORTABLE_COLD','identity':identity,'records':records,'public_bytes_unchanged':unchanged,'limits':{'address_space_bytes':AS,'group_RSS_stop_bytes':RSS_STOP,'CPU_seconds_per_process':CPU_SECONDS,'wall_seconds_per_stage':WALL_SECONDS,'total_output_bytes':OUTPUT_BYTES,'CPU_affinity_count':1,'threads':1},'historical_GO':False,'original26_historical_closure_admitted':False,'historical_target_arrays_shipped_or_read_by_new_cold':0,'risk_certification':False,'account_resume_fork_certified':False}
    (out/'PUBLIC_SAFE_COLD_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2));return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
