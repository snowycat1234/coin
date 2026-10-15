"""Cached-module provenance probes; no files or financial state are changed."""
from contextlib import ExitStack
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from generated_helpers import f
import forecast_entry as e
import forecast_historical as historical


def import_probe(filename):
    spec = importlib.util.spec_from_file_location('_independent_generated_import_probe', f.HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


class CachedModuleProvenance(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.blocked = []
        for owner, name in ((f.V2.ENGINE.USDTLinearPerpetualAccount, '__init__'),
                            (historical.HistoricalForecastRiskAccount, '__init__'),
                            (subprocess, 'Popen')):
            self.blocked.append(self.stack.enter_context(patch.object(owner, name,
                side_effect=AssertionError('IMPORT_MUST_NOT_CONSTRUCT_OR_LAUNCH'))))

    def tearDown(self):
        for blocked in self.blocked:
            blocked.assert_not_called()

    def test_cached_source_entry_wrong_file_is_rejected(self):
        wrong = SimpleNamespace(__file__='/GENERATED_ONLY_WRONG_MODULE/expansion_entry.py')
        with patch.dict(sys.modules, {e._NAME: wrong}):
            with self.assertRaisesRegex(ValueError, 'CONFLICTING_DECLARED_FORECAST_SOURCE_ENTRY_IMPORT'):
                import_probe('forecast_entry.py')

    def test_cached_monitor_wrong_file_is_rejected_before_entry(self):
        with patch.object(f, '__file__', '/GENERATED_ONLY_WRONG_MODULE/forecast_monitor.py'):
            with self.assertRaisesRegex(ValueError, 'EXACT_LOCAL_FORECAST_MONITOR_MODULE_REQUIRED'):
                import_probe('forecast_entry.py')

    def test_cached_entry_wrong_file_is_rejected_before_historical_definitions(self):
        with patch.object(e, '__file__', '/GENERATED_ONLY_WRONG_MODULE/forecast_entry.py'):
            with self.assertRaisesRegex(ValueError, 'EXACT_LOCAL_FORECAST_MONITOR_AND_ENTRY_REQUIRED'):
                import_probe('forecast_historical.py')

    def test_cached_monitor_wrong_file_is_rejected_before_historical_definitions(self):
        with patch.object(f, '__file__', '/GENERATED_ONLY_WRONG_MODULE/forecast_monitor.py'):
            with self.assertRaisesRegex(ValueError, 'EXACT_LOCAL_FORECAST_MONITOR_AND_ENTRY_REQUIRED'):
                import_probe('forecast_historical.py')


if __name__ == '__main__':
    unittest.main()
