"""Run already-imported generated tests with zero external-I/O/call guard."""
import io
import json
from pathlib import Path
import sys
import unittest
import test_overlay
import metadata_binding

HERE = str(Path(__file__).resolve().parent)
WORKSPACE = str(Path(HERE).parent)
COUNTERS = {"actual_source_reads": 0, "network_calls": 0,
            "actual_financial_or_source_module_calls": 0, "process_calls": 0}


def guard(event, args):
    if event == "open":
        # After imports the tests have no reason to open any file at all.
        COUNTERS["actual_source_reads"] += 1
        raise RuntimeError("Generated test sandbox rejects all post-import file opens")
    if event.startswith("socket.") or event.startswith("http.") or event.startswith("urllib."):
        COUNTERS["network_calls"] += 1
        raise RuntimeError("Generated tests reject network calls")
    if event.startswith("subprocess.") or event in ("os.system", "os.exec", "os.posix_spawn"):
        COUNTERS["process_calls"] += 1
        raise RuntimeError("Generated tests reject subprocesses")


def profile(frame, event, arg):
    if event != "call":
        return
    filename = frame.f_code.co_filename
    if filename.startswith(WORKSPACE + "/") and not filename.startswith(HERE + "/"):
        COUNTERS["actual_financial_or_source_module_calls"] += 1
        raise RuntimeError("Actual source/financial workspace modules are outside generated tests")


suite = unittest.defaultTestLoader.loadTestsFromModule(test_overlay)
# StringIO prevents unittest from opening any output artifacts.
stream = io.StringIO()
sys.addaudithook(guard)
sys.setprofile(profile)
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
sys.setprofile(None)
print(stream.getvalue(), end="")
print(json.dumps({"schema":"GENERATED_ONLY_TEST_EXECUTION_V1", "tests_run":result.testsRun,
    "failures":len(result.failures), "errors":len(result.errors),
    "successful":result.wasSuccessful(), "counters":COUNTERS}, sort_keys=True))
sys.exit(0 if result.wasSuccessful() and not any(COUNTERS.values()) else 1)
