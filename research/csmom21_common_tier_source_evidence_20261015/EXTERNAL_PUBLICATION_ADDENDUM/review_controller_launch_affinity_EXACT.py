"""Pure recording real-controller affinity regression; no source/claims/launch."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys,unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v5'))
import run_cs as d
import cs_process_runtime as r
import cs_common as c

class StopAfterCPUValidation(Exception):pass

class LaunchAffinityReview(unittest.TestCase):
    def test_host_observation_uses_actual_current_controller_affinity(self):
        for allowed in ({7},{4,5}):
            with patch.object(r.os,'sched_getaffinity',return_value=allowed):
                self.assertEqual(r.host_observation()['allowed_CPUs'],sorted(allowed))

    def test_real_controller_cpu7_refuses_before_output_lease_claim_or_pool(self):
        host=dict(allowed_CPUs=[7],MemAvailable_bytes=6000000000,cgroup_observations={})
        go=c.canonical(dict(worker_CPUs=[4,5],requested_worker_count=2))
        with patch.object(d,'wires',return_value=(b'{}',{},dict(go=go))),patch.object(r,'host_observation',return_value=host),\
             patch.object(d,'ordinary') as ordinary,patch.object(r,'controller_lease') as lease,\
             patch.object(d.supersession,'reserve') as claim,patch.object(r,'run_pool') as pool:
            with self.assertRaisesRegex(ValueError,'DISTINCT_ACTUALLY_ALLOWED_WORKER_CPUS_REQUIRED'):d.controller(SimpleNamespace(output='/GENERATED_ONLY'))
            for mock in (ordinary,lease,claim,pool):mock.assert_not_called()

    def test_real_controller_affinity4_5_passes_cpu_validation_without_effects(self):
        host=dict(allowed_CPUs=[4,5],MemAvailable_bytes=6000000000,cgroup_observations={})
        go=c.canonical(dict(worker_CPUs=[4,5],requested_worker_count=2))
        with patch.object(d,'wires',return_value=(b'{}',{},dict(go=go))),patch.object(r,'host_observation',return_value=host),\
             patch.object(r,'choose_worker_count',wraps=r.choose_worker_count) as choose,\
             patch.object(d,'ordinary',side_effect=StopAfterCPUValidation),patch.object(r,'controller_lease') as lease,\
             patch.object(d.supersession,'reserve') as claim,patch.object(r,'run_pool') as pool:
            with self.assertRaises(StopAfterCPUValidation):d.controller(SimpleNamespace(output='/GENERATED_ONLY'))
            choose.assert_called_once_with(2,[4,5],host)
            for mock in (lease,claim,pool):mock.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
