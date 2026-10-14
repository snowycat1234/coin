"""Isolated 120-second generated-only process, with source hashes and preserved attempts."""
import os, sys, argparse, pathlib, json, hashlib, datetime, time, resource, signal, traceback
assert os.environ.get('ROOT_CAUSAL_TEST_GO') == 'REVIEWED_GENERATED_ONLY'
assert sys.version_info[:3] == (3, 12, 14) and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and not sys.flags.optimize
ap = argparse.ArgumentParser()
ap.add_argument('--code-root', required=True); ap.add_argument('--output', required=True)
ap.add_argument('--v3-root', required=True); ap.add_argument('--runtime-sites-json', required=True)
ap.add_argument('--manifest-sha', required=True)
args = ap.parse_args()
P = pathlib.Path; HERE = P(__file__).resolve().parent; ROOT = P(args.code_root).resolve(); V3 = P(args.v3_root).resolve()
OUT = P(args.output).resolve(); assert not OUT.exists(); OUT.mkdir()
START = datetime.datetime.now(datetime.timezone.utc); BEG = time.monotonic(); DEAD = START+datetime.timedelta(seconds=120)
os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
for key, val in ((resource.RLIMIT_CPU, 120), (resource.RLIMIT_AS, 4000000000), (resource.RLIMIT_FSIZE, 25000000)):
    resource.setrlimit(key, (val, val))
def bounds(*unused):
    if time.monotonic()-BEG >= 120: raise TimeoutError('ACTUAL_PROCESS_WALL120')
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 > 2000000000: raise MemoryError('RSS2GB')
    if sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()) > 25000000: raise OSError('OUTPUT25MB')
signal.signal(signal.SIGALRM, bounds); signal.setitimer(signal.ITIMER_REAL, .1, .1)
def sha(body): return hashlib.sha256(body).hexdigest()
r = {'PID': os.getpid(), 'start_UTC': START.isoformat(), 'deadline_UTC': DEAD.isoformat(),
     'historical_GO': False, 'market_data_read': False, 'published_sources_modified': False,
     'scope': 'PRESERVED_V3_21_PLUS_CAUSAL_NATIVE_INTEGRATION_GENERATED_ONLY'}
print('CAUSAL_SYNTHETIC_START', json.dumps(r), flush=True)
rc = 1
try:
    manifest_body = (HERE/'SOURCE_MANIFEST.json').read_bytes(); assert sha(manifest_body) == args.manifest_sha
    manifest = json.loads(manifest_body)
    roots = {'adapter': HERE, 'v3': V3, 'dependencies': ROOT}
    for group, files in manifest['files'].items():
        for name, record in files.items():
            body = (roots[group]/name).read_bytes()
            assert len(body) == record['bytes'] and sha(body) == record['SHA256'], (group, name)
    for k in ('PYTHONOPTIMIZE', 'PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP'): os.environ.pop(k, None)
    for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'POLARS_MAX_THREADS'): os.environ[k] = '1'
    sites = json.loads(args.runtime_sites_json); assert sites and all(P(x).is_absolute() and P(x).is_dir() for x in sites)
    repo = ROOT/'native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d/repo'
    fine = ROOT/'native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d/fine'
    sys.path[:0] = [str(HERE), str(V3), *sites, str(fine), str(repo), str(repo/'src')]
    import numpy, polars
    assert (numpy.__version__, polars.__version__) == ('2.3.5', '1.44.2')
    import ast, types, unittest
    def selected(module, path, names):
        tree = ast.parse(path.read_bytes()); nodes = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names: nodes.append(node)
            elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets): nodes.append(node)
        assert len(nodes) == len(names), (module, names)
        mod = types.ModuleType(module); mod.__file__ = str(path)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), mod.__dict__); sys.modules[module] = mod
    selected('scripts.investment.perpetual_directional', repo/'scripts/investment/perpetual_directional.py', {'MINUTE', 'DAY', 'need'})
    selected('scripts.investment.public_sma_perpetual', repo/'scripts/investment/public_sma_perpetual.py', {'SYMBOLS', 'require', 'symbol_order'})
    sys.path.insert(0, str(ROOT/'coin_h090_finite_native_20261014/dependencies'))
    import terminal_adapter
    native = types.ModuleType('native_control'); native.NATIVE = terminal_adapter.EarlierTerminalSimulator; sys.modules['native_control'] = native
    def forbid(event, args):
        if event in ('socket.connect', 'subprocess.Popen', 'os.system'): raise RuntimeError('GENERATED_ONLY_NO_NETWORK_OR_CHILDREN')
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            path = P(os.fsdecode(args[0]))
            if path.suffix.lower() in ('.npz', '.npy', '.parquet', '.csv', '.zip', '.gz'):
                raise RuntimeError('GENERATED_ONLY_NO_DATA_CONTAINER_READ:'+str(path))
    sys.addaudithook(forbid)
    import test_synthetic, test_causal_integration
    names = ['test_synthetic.Tests.'+name for name in sorted(vars(test_synthetic.Tests)) if name.startswith('test_')]
    names += ['test_causal_integration.Tests.'+name for name in sorted(vars(test_causal_integration.Tests)) if name.startswith('test_')]
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    with (OUT/'TEST_LOG.txt').open('x') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2, failfast=True).run(suite)
    r.update(tests_run=result.testsRun, fixed_nodes=names,
        errors=[{'test': str(t), 'traceback': s} for t, s in result.errors],
        failures=[{'test': str(t), 'traceback': s} for t, s in result.failures],
        status='PASS_PRESERVED_V3_AND_CAUSAL_NATIVE_INTEGRATION' if result.wasSuccessful() else 'FAILED_PRESERVED')
    rc = 0 if result.wasSuccessful() else 1
    # Recheck immutable sources after all tests, including source/scheduler/account code.
    for group, files in manifest['files'].items():
        for name, record in files.items():
            assert sha((roots[group]/name).read_bytes()) == record['SHA256'], ('AFTER_TEST', group, name)
    r['source_hashes_verified_before_and_after'] = True
    r['source_manifest_SHA256'] = sha(manifest_body)
except BaseException as exc:
    r.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
signal.setitimer(signal.ITIMER_REAL, 0)
u = resource.getrusage(resource.RUSAGE_SELF)
r['resource'] = {'exit': rc, 'end_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'wall_seconds': time.monotonic()-BEG, 'CPU_seconds': u.ru_utime+u.ru_stime, 'peak_RSS_bytes': u.ru_maxrss*1024}
r['files'] = {p.name: {'bytes': p.stat().st_size, 'SHA256': sha(p.read_bytes())} for p in OUT.iterdir() if p.is_file()}
(OUT/'TEST_RECEIPT.json').write_text(json.dumps(r, indent=2)+'\n')
print('CAUSAL_SYNTHETIC_TERMINAL', json.dumps(r)); sys.exit(rc)
