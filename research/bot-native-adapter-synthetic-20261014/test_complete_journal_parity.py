"""Checks for the narrowly declared UUID/set-order journal comparison."""
import copy,importlib.util,pathlib,unittest
HERE=pathlib.Path(__file__).resolve().parent

def loaded(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class CompleteJournalParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json
        cls.audit=loaded(HERE/'audit_public_journals.py','complete_journal_audit')
        _,bodies=loaded(HERE/'saved_generated_journals/restore_journals.py','saved_journal_bytes').verify()
        cls.journal=json.loads(bodies['generated_journals/RANGE_GRID.json'])
    def test_set_serialization_order_only_is_equal(self):
        altered=copy.deepcopy(self.journal)
        for key in ['seen_native_legs','seen_native_funding','expired_sessions']:altered['adapter_state_final'][key].reverse()
        self.assertEqual(self.audit.canonical_text(altered),self.audit.canonical_text(self.journal))
    def test_financial_quantity_change_is_unequal(self):
        altered=copy.deepcopy(self.journal);altered['native_trades'][0]['decimal_strings']['quantity']='987654'
        self.assertNotEqual(self.audit.canonical_text(altered),self.audit.canonical_text(self.journal))
    def test_policy_event_change_is_unequal(self):
        altered=copy.deepcopy(self.journal);altered['policy_events'][0]['kind']='UNBOUND_POLICY_CHANGE'
        self.assertNotEqual(self.audit.canonical_text(altered),self.audit.canonical_text(self.journal))
    def test_numeric_and_boolean_type_substitution_is_unequal(self):
        original=copy.deepcopy(self.journal);altered=copy.deepcopy(original)
        original['type_probe']=True;altered['type_probe']=1
        self.assertNotEqual(self.audit.canonical_text(altered),self.audit.canonical_text(original))
        original['type_probe']=1;altered['type_probe']=1.0
        self.assertNotEqual(self.audit.canonical_text(altered),self.audit.canonical_text(original))
    def test_duplicate_seen_identity_is_rejected(self):
        altered=copy.deepcopy(self.journal);items=altered['adapter_state_final']['seen_native_legs'];items.append(copy.deepcopy(items[0]))
        with self.assertRaisesRegex(ValueError,'DUPLICATE_SET_DERIVED_IDENTITY'):self.audit.canonical(altered)
if __name__=='__main__':unittest.main(verbosity=2)
