"""Pure module-binding regression, no account or source-provider calls."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from generated_helpers import f

class ReviewerImportBindingTests(unittest.TestCase):
    def test_conflicting_cached_source_entry_cannot_replace_pinned_base(self):
        path=Path(f.__file__).with_name('forecast_entry.py')
        foreign=SimpleNamespace(__file__='/GENERATED_FOREIGN_MODULE/expansion_entry.py')
        spec=importlib.util.spec_from_file_location('_review_conflicting_forecast_entry',path)
        module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'_causal_forecast_exact_source_entry':foreign}):
            with self.assertRaisesRegex(ValueError,'EXACT.*(BASE|SOURCE|ENTRY)|CONFLICT'):
                spec.loader.exec_module(module)

if __name__=='__main__':unittest.main()
