"""Code-only scheduler lineage and pure finite resource checks; no processes."""
import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v5'))
import cs_process_runtime as runtime
HERE=Path(runtime.__file__).parent


def functions(raw):
    return {n.name:n for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}


class SchedulerCodeReview(unittest.TestCase):
    def test_exact_original_D_scheduler_source_pin_and_only_declared_transport_AST_changes(self):
        receipt=json.loads((HERE/'NATIVE_PROCESS_PROVENANCE.json').read_bytes())
        old_raw=(ROOT/receipt['source']).read_bytes()
        self.assertEqual(sha256(old_raw).hexdigest(),receipt['source_SHA256'])
        old=functions(old_raw);new=functions(Path(runtime.__file__).read_bytes())
        self.assertEqual(set(new),set(receipt['selected_functions']))
        for name,meta in receipt['selected_functions'].items():
            before=ast.dump(old[name],include_attributes=False)
            self.assertEqual(sha256(before.encode()).hexdigest(),meta['original_AST_SHA256'],name)
            if meta['transport_only_replacements']:
                for a,b in receipt['substitutions'].items():before=before.replace(repr(a),repr(b))
            self.assertEqual(before,ast.dump(new[name],include_attributes=False),name)

    def test_exact_resource_limits_and_distinct_CPU_validation(self):
        self.assertEqual(runtime.LIMITS,dict(maximum_live_workers=2,threads_per_worker=1,per_case_wall_seconds=600,
            per_case_CPU_seconds=600,per_case_RSS_stop_bytes=2000000000,per_case_AS_bytes=4000000000,
            per_case_output_bytes=250000000,aggregate_live_worker_RSS_stop_bytes=3500000000))
        host=dict(allowed_CPUs=[4,7],MemAvailable_bytes=6000000000,cgroup_observations={})
        self.assertEqual(runtime.choose_worker_count(2,[4,7],host),2)
        for cpus in ([4,4],[4,8],[4],[],['4',7]):
            with self.subTest(cpus=cpus),self.assertRaises(ValueError):runtime.choose_worker_count(2,cpus,host)
        h=deepcopy(host);h['MemAvailable_bytes']=3000000000
        self.assertEqual(runtime.choose_worker_count(2,[4,7],h),1)
        h['MemAvailable_bytes']=2200000000
        with self.assertRaisesRegex(RuntimeError,'MEMORY'):runtime.choose_worker_count(2,[4,7],h)
        h=deepcopy(host);h['cgroup_observations']={'/sys/fs/cgroup/cpu.max':'100000 100000'}
        self.assertEqual(runtime.choose_worker_count(2,[4,7],h),1)

    def test_pure_environment_pool_threads_one(self):
        env=runtime.environment()
        self.assertTrue(all(env[key]=='1' for key in runtime.THREAD_ENV))
        self.assertEqual(env['PYTHONDONTWRITEBYTECODE'],'1')

    def test_no_import_time_launch_or_claim_calls(self):
        tree=ast.parse(Path(runtime.__file__).read_bytes())
        top=[]
        for n in tree.body:
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):continue
            top.extend(x for x in ast.walk(n) if isinstance(x,ast.Call))
        forbidden={'Popen','run_pool','_run_pool','claim_launch','controller_lease','apply_limits','mkdir','save','write_bytes'}
        for call in top:
            name=call.func.attr if isinstance(call.func,ast.Attribute) else call.func.id if isinstance(call.func,ast.Name) else ''
            self.assertNotIn(name,forbidden)

if __name__=='__main__':unittest.main(verbosity=2)
