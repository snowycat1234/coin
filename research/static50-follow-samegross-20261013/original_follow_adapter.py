"""Load the original public equations unchanged from their exact reference tree."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent

def original():
    manifest = json.loads((HERE / 'ORIGINAL_REFERENCE.json').read_text())
    for relative, expected in manifest['files_SHA256'].items():
        p = HERE / relative
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            raise ValueError('Original formula source identity changed: ' + relative)
    repo = HERE / 'reference/repo'
    sys.path.insert(0, str(repo))
    path = repo / 'research/failed-breakout-rejection-20261012/core.py'
    spec = importlib.util.spec_from_file_location('exact_original_rejected_break_core', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
