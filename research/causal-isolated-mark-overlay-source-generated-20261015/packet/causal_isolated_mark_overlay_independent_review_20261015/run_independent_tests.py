"""Independent guarded fake tests. Preload only code and frozen metadata."""
import io
import json
import linecache
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / (sys.argv[1] if len(sys.argv) > 1 else "causal_isolated_mark_overlay_20261015")
sys.path.insert(0, str(SOURCE))
import test_independent_overlay as tests
tests.METADATA_BLOBS = tuple((SOURCE / "evidence" / p).read_bytes() for p in (
    "ORIGINAL_MARK_Q3_RECOVERY.json", "EXACT_JULY_MARK_GAP_ALLOWLIST.json", "FULL2022_GAP_TAXONOMY.json"))
# Keep failure rendering inside the same zero-runtime-I/O contract.
for p in (HERE / "test_independent_overlay.py", HERE / "run_independent_tests.py", SOURCE / "overlay.py"):
    source_text = p.read_text()
    linecache.cache[str(p)] = (len(source_text), None, source_text.splitlines(keepends=True), str(p))
COUNTERS = {"post_import_file_opens": 0, "network_calls": 0,
            "process_calls": 0, "external_workspace_module_calls": 0}


def guard(event, args):
    if event == "open":
        COUNTERS["post_import_file_opens"] += 1
        raise RuntimeError("Independent fake-only tests forbid runtime file opens")
    if event.startswith(("socket.", "http.", "urllib.")):
        COUNTERS["network_calls"] += 1
        raise RuntimeError("Independent tests forbid network")
    if event.startswith("subprocess.") or event in ("os.system", "os.exec", "os.posix_spawn"):
        COUNTERS["process_calls"] += 1
        raise RuntimeError("Independent tests forbid child processes")


def profile(frame, event, arg):
    filename = frame.f_code.co_filename
    if event == "call" and filename.startswith(str(HERE.parent) + "/"):
        if not filename.startswith((str(HERE) + "/", str(SOURCE) + "/")):
            COUNTERS["external_workspace_module_calls"] += 1
            raise RuntimeError("Independent tests forbid external source/financial modules")


suite = unittest.defaultTestLoader.loadTestsFromModule(tests)
stream = io.StringIO()
sys.addaudithook(guard)
sys.setprofile(profile)
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
sys.setprofile(None)
print(stream.getvalue(), end="")
print(json.dumps({"schema": "INDEPENDENT_GENERATED_ONLY_TEST_EXECUTION_V1", "tests_run": result.testsRun,
    "failures": len(result.failures), "errors": len(result.errors), "successful": result.wasSuccessful(),
    "counters": COUNTERS}, sort_keys=True))
sys.exit(0 if result.wasSuccessful() and not any(COUNTERS.values()) else 1)
