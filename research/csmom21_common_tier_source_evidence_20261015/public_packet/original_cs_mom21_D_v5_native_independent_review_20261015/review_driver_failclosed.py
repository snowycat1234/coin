"""Pure recording/static driver tests; no processes, claims, outputs or sources."""
import ast
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v5'))
import run_cs as driver
import cs_saved as saved


def fake_args():
    a=SimpleNamespace(preparation='/GENERATED_ONLY_NOT_A_FILE',preparation_sha='a'*64,output='/FAKE_OUT',cpu=4)
    for name in driver.WIRE_NAMES:
        setattr(a,name.replace('-','_'),'/GENERATED_ONLY_'+name)
        setattr(a,name.replace('-','_')+'_sha','b'*64)
    return a


class DriverFailClosedReview(unittest.TestCase):
    def test_failed_external_admission_precedes_controller_effects(self):
        denied=Mock(side_effect=ValueError('FAKE_INVALID_EXTERNAL_AUTHORITY'))
        with patch.object(driver,'wires',denied),patch.object(driver.r,'controller_lease') as lease,\
             patch.object(driver.r,'claim_launch') as claim,patch.object(driver.r,'run_pool') as pool,\
             patch.object(driver.r,'save') as save,patch.object(Path,'mkdir') as mkdir:
            with self.assertRaisesRegex(ValueError,'FAKE_INVALID'):driver.controller(fake_args())
            for x in (lease,claim,pool,save,mkdir):x.assert_not_called()
    def test_failed_worker_admission_cannot_reach_source_or_account(self):
        with patch.object(driver.r,'apply_limits') as limits,\
             patch.object(driver,'wires',side_effect=ValueError('FAKE_INVALID_EXTERNAL_AUTHORITY')),\
             patch.object(driver,'worker_claim') as claim,patch.object(driver,'load_saved_year') as loader:
            with self.assertRaisesRegex(ValueError,'FAKE_INVALID'):driver.case(fake_args())
            limits.assert_called_once_with(4);claim.assert_not_called();loader.assert_not_called()
    def test_failed_saved_admission_cannot_read_checkpoint_or_targets(self):
        import cs_native  # Code-pin reads are permitted before the saved-body spy.
        with patch.object(driver,'wires',side_effect=ValueError('FAKE_INVALID_EXTERNAL_AUTHORITY')),\
             patch.object(Path,'read_bytes',side_effect=AssertionError('SAVED_BODY_READ_BEFORE_AUTH')) as reader:
            with self.assertRaisesRegex(ValueError,'FAKE_INVALID'):
                saved.validate_saved_terminal('/GENERATED_ONLY',args=fake_args(),cell_id='FAKE_CELL')
            reader.assert_not_called()
    def test_commands_bind_every_external_hash_and_exact_pinned_launcher(self):
        args=fake_args();command=driver.command(args,cell_id='FAKE_CELL',directory=Path('/GENERATED_ONLY_CASE'),cpu=5)
        self.assertEqual(command[:4],[sys.executable,'-B',str(driver.HERE/'run_cs.py'),'--case'])
        for name in driver.WIRE_NAMES:
            flag='--'+name
            self.assertEqual(command[command.index(flag)+1],getattr(args,name.replace('-','_')))
            self.assertEqual(command[command.index(flag+'-sha')+1],getattr(args,name.replace('-','_')+'_sha'))
        self.assertEqual(command[command.index('--cpu')+1],'5');self.assertNotIn('--generated',command)
    def test_actual_driver_has_no_generated_or_callback_admission_flags(self):
        tree=ast.parse(Path(driver.__file__).read_bytes())
        main=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='main')
        flags=[call.args[0].value for call in ast.walk(main) if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute)
               and call.func.attr=='add_argument' and call.args and isinstance(call.args[0],ast.Constant)]
        for name in ('--generated','--generated-scope','--validator','--callback','--source-scope'):
            self.assertNotIn(name,flags)

if __name__=='__main__':unittest.main(verbosity=2)
