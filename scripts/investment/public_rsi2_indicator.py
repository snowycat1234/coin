"""Pinned Jesse scalar RSI wrapper with the official jesse-rust wheel.

The original FunctionDef nodes are compiled without modifying their bodies.
Two-dimensional scalar calls retain Jesse's default last-240-candle slice.
One-dimensional source calls and sequential calls retain upstream semantics.
No indicator recurrence, seed, or flat-price branch is implemented here.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Union

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "third_party/jesse_example_rsi2"
SCALAR_CANDLE_WINDOW = 240
PACKAGE_VERSION = "1.3.0"
KERNEL_TARGET = Path("/home/xflops/coin-state/rsi2-kernel-jesse-rust-1.3.0-cp312-v1")
BASE_LOCK_SHA256 = "97335dc3dbb04d7dbc67425f91d4e941a0cfd2c84e5f2adcd852514ec4600de6"
INSTALLED_BINDING_SHA256 = "4035a57485f63bc7e4470f91b7fdea950e3b99a07638e959d32013b705f23b2a"
PINNED_HASHES = {
    "rsi2_original.py": "fd463da53b6ac78138a0886268f654973daa569dd2094c6aa96796a8a5015f70",
    "rsi_indicator_original.py": "a82266677770c3c3905c87000f81e662973ae6363b542816ae6af67a691cd922",
    "JESSE_HELPERS_ORIGINAL.py": "d54afd8da37965cd87b6341d2362af5f92c4bbbf18ae961ad1361a31dc89e86b",
    "JESSE_CONFIG_ORIGINAL.py": "cd1e76d64fe0cac25e9fb31c5f378c666aaaa8199314cdcad6844fff09af746f",
    "JESSE_CONSTANTS_ORIGINAL.py": "1851c5a8cada93e1791825d0010079afd35b083657f7075e4ea7034ea0774ebe",
    "JESSE_REQUIREMENTS_ORIGINAL.txt": "d66cec190bb666305db6896a192629d839518dcce3e23ff0668991dd90fbd058",
    "rsi_kernel_original.rs": "25a07d9c665a30bd2c56606b07b9d83fd59b67c8b1771bf0ccae2c3f0ca6b208",
    "LICENSE": "80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d",
    "JESSE_LICENSE": "8985ca8447e233f34397a52fe77989c02e27b8145d43bd8c715ae9c7a96056d4",
    "KERNEL_LICENSE": "17753bd10c1f6cfd62d9b3206f3a5149ac92c94139f25733cf20c6142c5bf1a7",
    "KERNEL_CARGO_ORIGINAL.toml": "186f7560f3c7b9c5cb2a9fe4c7cd079548a55d28e2639edcdcb700cbfa6cc0cd",
}
_CONTEXT = None


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _fixed_get_config(key, default):
    if key != "env.data.warmup_candles_num" or default != SCALAR_CANDLE_WINDOW:
        raise ValueError("Only the pinned Jesse default scalar window is supported")
    return default


def _function(path, name):
    nodes = [n for n in ast.parse(path.read_text()).body
             if isinstance(n, ast.FunctionDef) and n.name == name and not n.decorator_list]
    if len(nodes) != 1:
        raise ValueError("Expected exactly one original undecorated upstream function")
    return nodes[0]


def _context():
    global _CONTEXT
    if _CONTEXT is not None:
        return _CONTEXT
    if sys.version_info[:2] != (3, 12) or _sha(ROOT / "environments/v8/uv.lock") != BASE_LOCK_SHA256:
        raise ValueError("Pinned CPython 3.12 and unchanged base environment lock required")
    for name, expected in PINNED_HASHES.items():
        if _sha(VENDOR / name) != expected:
            raise ValueError(f"Pinned official source changed: {name}")
    binding_path = VENDOR / "INSTALLED_KERNEL_BINDING_20261002_V1.json"
    if _sha(binding_path) != INSTALLED_BINDING_SHA256:
        raise ValueError("Supplementary installation binding changed")
    binding = json.loads(binding_path.read_text())
    if binding["package_version"] != PACKAGE_VERSION or Path(binding["target"]) != KERNEL_TARGET:
        raise ValueError("Wrong official package version or supplementary target")
    for relative in ("jesse_rust/__init__.py", binding["extension_relative_path"],
                     "jesse_rust-1.3.0.dist-info/METADATA"):
        if _sha(KERNEL_TARGET / relative) != binding["installed_files"][relative]["sha256"]:
            raise ValueError(f"Official installed artifact changed: {relative}")
    if "jesse_rust" in sys.modules:
        package = sys.modules["jesse_rust"]
        if Path(package.__file__).resolve() != (KERNEL_TARGET / "jesse_rust/__init__.py").resolve():
            raise ValueError("An unbound jesse_rust package is already imported")
    else:
        spec = importlib.util.spec_from_file_location(
            "jesse_rust", KERNEL_TARGET / "jesse_rust/__init__.py",
            submodule_search_locations=[str(KERNEL_TARGET / "jesse_rust")])
        package = importlib.util.module_from_spec(spec)
        sys.modules["jesse_rust"] = package
        try:
            spec.loader.exec_module(package)
        except BaseException:
            sys.modules.pop("jesse_rust", None)
            raise
    extension = sys.modules["jesse_rust.jesse_rust"]
    if Path(extension.__file__).resolve() != (KERNEL_TARGET / binding["extension_relative_path"]).resolve():
        raise ValueError("An unbound compiled kernel is loaded")
    constants = ast.parse((VENDOR / "JESSE_CONSTANTS_ORIGINAL.py").read_text())
    mappings = [node for node in constants.body if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "CANDLE_SOURCE_MAPPING" for t in node.targets)]
    if len(mappings) != 1:
        raise ValueError("Original source mapping must be unique")
    nodes = [mappings[0], _function(VENDOR / "JESSE_HELPERS_ORIGINAL.py", "get_candle_source"),
             _function(VENDOR / "JESSE_HELPERS_ORIGINAL.py", "slice_candles"),
             _function(VENDOR / "rsi_indicator_original.py", "rsi")]
    namespace = {"np": np, "Union": Union, "get_config": _fixed_get_config,
                 "rsi_rust": package.rsi, "rsi_last_rust": package.rsi_last}
    tree = ast.Module(body=nodes, type_ignores=[])
    exec(compile(tree, str(VENDOR / "rsi_indicator_original.py"), "exec"), namespace)
    receipt = {
        "package_version": PACKAGE_VERSION,
        "package_file": str(Path(package.__file__).resolve()),
        "extension_file": str(Path(extension.__file__).resolve()),
        "extension_sha256": binding["extension_sha256"],
        "installed_binding_sha256": INSTALLED_BINDING_SHA256,
        "wheel_sha256": binding["wheel_sha256"], "sdist_sha256": binding["sdist_sha256"],
        "base_environment_lock_sha256": BASE_LOCK_SHA256,
        "numpy_version": np.__version__, "python_version": sys.version,
        "official_functions_ast_sha256": hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest(),
        "official_sources": dict(PINNED_HASHES), "scalar_2d_window": SCALAR_CANDLE_WINDOW,
        "one_dimensional_scalar_slice": "NONE_UPSTREAM_SEMANTICS",
        "kernel_flat_branch": "OFFICIAL_RUST_AVG_LOSS_ZERO_RETURNS_100",
    }
    _CONTEXT = namespace, receipt
    return _CONTEXT


def _input(candles, period):
    if isinstance(period, (bool, np.bool_)) or not isinstance(period, (int, np.integer)) or period < 1:
        raise ValueError("A positive integer RSI period is required")
    values = np.asarray(candles)
    if values.ndim not in (1, 2) or (values.ndim == 2 and values.shape[1] != 6):
        raise ValueError("Expected a one-dimensional source or Jesse six-column candles")
    closes = values if values.ndim == 1 else values[:, 2]
    if not np.all(np.isfinite(closes)):
        raise ValueError("Missing/nonfinite close is not an indicator input")
    return values


def rsi(candles, period=2):
    """Original Jesse nonsequential scalar call, including its 2D 240-bar slice."""
    values = _input(candles, period)
    return _context()[0]["rsi"](values, period=int(period), sequential=False)


def rsi_series(closes, period=2):
    """Official aligned full-source series; it does not apply a scalar window."""
    values = _input(closes, period)
    if values.ndim != 1:
        raise ValueError("rsi_series accepts a one-dimensional source only")
    return _context()[0]["rsi"](values, period=int(period), sequential=True)


def kernel_receipt():
    """Runtime identity for protocols, including the compiled artifact and wrapper AST."""
    return dict(_context()[1])
