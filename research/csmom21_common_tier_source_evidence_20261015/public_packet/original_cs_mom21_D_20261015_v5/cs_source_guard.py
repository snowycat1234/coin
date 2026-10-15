"""Whole-invocation source boundary with observed attempts, including failures.

The source graph never imports financial code. Existing loaded finance classes
are denied dynamically, and local finance imports cannot introduce new ones.
No counter below is a claimed constant: each deny path increments observed state.
"""
import builtins
import fcntl
import http.client
import importlib
import importlib.machinery
import importlib.util
import io
import json
import multiprocessing.process
import os
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request
from contextlib import ExitStack
from copy import deepcopy
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
_ACTIVE_GUARD = None
def current_guard():return _ACTIVE_GUARD

class SourceBoundaryViolation(RuntimeError):
    pass


class SourceOnlyGuard:
    CATEGORIES = ('financial_constructors', 'financial_account_advance',
        'native_simulator_construct_or_advance', 'historical_scope_mints',
        'actual_provider_calls', 'process_launches', 'network_calls',
        'canonical_financial_claims_or_leases', 'financial_GO_writes',
        'financial_imports', 'outside_source_writes', 'nonallowlisted_file_reads')
    ADVANCE = ('update_marks', 'execute_fill', 'apply_funding', 'monitor', 'advance_day',
               'attempt', 'funding_through', 'from_snapshot', 'fork_for_preview')
    def __init__(self, write_roots=(), read_paths=()):
        self.attempts = dict.fromkeys(self.CATEGORIES, 0)
        self.targets, self.checkpoints, self.installed = [], [], []
        self.write_roots = tuple(Path(p).absolute() for p in write_roots)
        self.read_paths = frozenset(Path(p).absolute() for p in read_paths)
        self.observed_read_paths = {}
        self.active = False
        self._stack, self._seen = ExitStack(), set()
    def deny(self, category, target):
        self.attempts[category] += 1
        self.targets.append(dict(category=category, target=str(target)))
        raise SourceBoundaryViolation('SOURCE_ONLY_FORBIDDEN:' + category + ':' + str(target))
    def _block(self, obj, name, category):
        key = id(obj), name
        if key in self._seen or not hasattr(obj, name):
            return
        self._seen.add(key)
        target = getattr(obj, '__name__', type(obj).__name__) + '.' + name
        def blocked(*args, **kwargs):
            self.deny(category, target)
        try:
            self._stack.enter_context(patch.object(obj, name, blocked))
        except (AttributeError, TypeError):
            raise SourceBoundaryViolation('UNPATCHABLE_BOUNDARY:' + target)
        self.installed.append(dict(category=category, target=target))
    def _discover_loaded_boundaries(self):
        # Snapshot dictionaries: do not invoke module/class descriptors or imports.
        for module in tuple(sys.modules.values()):
            if module is None:
                continue
            namespace = vars(module)
            filename = namespace.get('__file__', '')
            local = isinstance(filename, str) and str(ROOT) + '/' in filename
            for name, obj in tuple(namespace.items()):
                if not local and not namespace.get('__source_guard_fixture__', False):
                    continue
                if isinstance(obj, type):
                    if name.endswith('Account'):
                        self._block(obj, '__init__', 'financial_constructors')
                        for method in self.ADVANCE:
                            self._block(obj, method, 'financial_account_advance')
                    if 'Simulator' in name:
                        self._block(obj, '__init__', 'native_simulator_construct_or_advance')
                        for method in self.ADVANCE:
                            self._block(obj, method, 'native_simulator_construct_or_advance')
                    if 'HistoricalExecutionScope' in name or name == 'CaseExecutionScope':
                        self._block(obj, '__init__', 'historical_scope_mints')
                    if 'Provider' in name:
                        for method in ('__call__', '__iter__', '__next__', '_bind_historical_scope'):
                            self._block(obj, method, 'actual_provider_calls')
                elif callable(obj):
                    if name in ('make_account', 'make_owned_account', 'construct_case', '_construct_case', 'make_case', 'build_case', '_account_for_cost', '_default_constructor_callback', 'validate_case_inputs'):
                        self._block(module, name, 'financial_constructors')
                    elif name in ('claim_launch', 'controller_lease'):
                        self._block(module, name, 'canonical_financial_claims_or_leases')
    def _require_clean_financial_graph(self):
        # Class monkeypatches cannot revoke a previously captured bound method.
        # Actual source stages therefore require a fresh source-only process,
        # before any local account/simulator/provider class has been imported.
        for module in tuple(sys.modules.values()):
            if module is None:
                continue
            namespace = vars(module); filename = namespace.get('__file__', '')
            local = isinstance(filename, str) and str(ROOT) + '/' in filename
            if not local and not namespace.get('__source_guard_fixture__', False):
                continue
            for name, obj in tuple(namespace.items()):
                if isinstance(obj, type) and (name.endswith('Account') or 'Simulator' in name or 'Provider' in name
                        or 'HistoricalExecutionScope' in name or name == 'CaseExecutionScope'):
                    self.deny('financial_imports', 'PRELOADED_FINANCIAL_GRAPH_REQUIRES_FRESH_SOURCE_ONLY_PROCESS:' + name)
    def _check_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        # A new local module may only be this source package or its six flat modules.
        components = name.split('.')
        forbidden = ('cs_native', 'run_cs', 'full_d', 'run_full', 'expansion', 'expansion_entry',
            'native_runtime', 'guard50_exit', 'guard50_exit_entry',
            'perpetual_account', 'minute_provider', 'source_window_interface')
        if any(c in forbidden or c.startswith(('bounded_native_', 'traditional_D_', 'traditional_three_tier_', 'selector_')) for c in components):
            self.deny('financial_imports', name)
        if level == 0:
            top = components[0]
            local_file = ROOT / (top + '.py')
            local_dir = ROOT / top
            own = top == HERE.name or top in {'cs_entry', 'cs_source', 'cs_common', 'cs_config', 'cs_codec',
                'cs_signal', 'cs_quality', 'cs_source_bridge', 'cs_source_guard', 'prepare_cs_source', 'frozen_grid'}
            if not own and (local_file.exists() or local_dir.is_dir()) and top not in sys.stdlib_module_names:
                self.deny('financial_imports', name)
        return self._original_import(name, globals, locals, fromlist, level)
    def _check_read(self, path):
        if isinstance(path, int):
            # Existing verified no-follow file descriptors are wrapped by fdopen.
            return
        if not isinstance(path, (str, bytes, os.PathLike)):
            self.deny('nonallowlisted_file_reads', 'UNKNOWN_PATH_TYPE')
        p = Path(os.path.abspath(os.fsdecode(path)))
        inside_workspace = p == ROOT or ROOT in p.parents
        source_output = any(p == root or root in p.parents for root in self.write_roots)
        if inside_workspace and p not in self.read_paths and not source_output:
            self.deny('nonallowlisted_file_reads', p)
        if inside_workspace:
            self.observed_read_paths[str(p)] = self.observed_read_paths.get(str(p), 0)+1
    def _check_write(self, path):
        if not isinstance(path, (str, bytes, os.PathLike)):
            self.deny('outside_source_writes', 'UNKNOWN_FILE_DESCRIPTOR_WRITE')
        p = Path(os.path.abspath(os.fsdecode(path)))
        parts, name = {x.upper() for x in p.parts}, p.name.upper()
        if 'EXECUTION_CLAIMS' in parts or name in ('LAUNCH_CLAIM.JSON', 'CONTROLLER_LEASE.LOCK'):
            self.deny('canonical_financial_claims_or_leases', p)
        if name.startswith(('ROOT_GO', 'FINANCIAL_GO', 'ADMISSION_GO')) and 'INVALID' not in name and 'UNAPPROVED' not in name:
            self.deny('financial_GO_writes', p)
        if not any(p == root or root in p.parents for root in self.write_roots):
            self.deny('outside_source_writes', p)
    def _check_json(self, value):
        if isinstance(value, dict):
            action = str(value.get('action', ''))
            schema = str(value.get('schema', ''))
            invalid = (action == 'INVALID_TEMPLATE_NOT_ROOT_AUTHORIZATION' and
                       str(value.get('status', '')).startswith('INVALID_') and
                       value.get('historical_execution_authorized') is False)
            source = (schema == 'ROOT_SOURCE_TARGET_CSMOM21_COMMON_TIER_V2' and
                      action in ('PREPARE_EXACT_FIRST6_2022_2023_ALL_THREE_TIERS_CS_SOURCE_TARGETS_ONLY',
                                 'PREPARE_EXACT_REMAINING9_2021_2024_2025_ALL_THREE_TIERS_CS_SOURCE_TARGETS_ONLY') and
                      value.get('historical_execution_authorized') is False and
                      value.get('account_construction_authorized') is False)
            if not invalid and (value.get('historical_execution_authorized') is True or
                value.get('financial_execution_authorized') is True or
                (('GO' in schema.upper() or 'AUTHORIZATION' in schema.upper()) and not source)):
                self.deny('financial_GO_writes', 'EXECUTABLE_FINANCIAL_AUTHORITY_CONTENT')
            for child in value.values():
                self._check_json(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                self._check_json(child)
    def _writer(self, stream, mode):
        if not any(c in mode for c in 'wax+'):
            return stream
        guard = self
        class CheckedWriter:
            def __init__(self):
                self.prefix, self.inspect = b'', None
            def __getattr__(self, name):
                if name in ('buffer', 'raw'):
                    return guard._writer(getattr(stream, name), 'wb')
                if name == 'detach':
                    def denied_detach(*args, **kwargs):
                        guard.deny('outside_source_writes', 'DETACH_WRITER_FORBIDDEN')
                    return denied_detach
                return getattr(stream, name)
            def seek(self, *args, **kwargs):
                if self.inspect:
                    guard.deny('outside_source_writes', 'JSON_SEEK_MUTATION_FORBIDDEN')
                return stream.seek(*args, **kwargs)
            def truncate(self, *args, **kwargs):
                if self.inspect:
                    guard.deny('outside_source_writes', 'JSON_TRUNCATE_MUTATION_FORBIDDEN')
                return stream.truncate(*args, **kwargs)
            def __enter__(self):
                stream.__enter__()
                return self
            def __exit__(self, *args):
                return stream.__exit__(*args)
            def write(self, value):
                raw = value.encode() if isinstance(value, str) else bytes(value)
                if self.inspect is None and raw.strip():
                    self.inspect = raw.lstrip()[:1] in (b'{', b'[')
                if self.inspect:
                    self.prefix += raw
                    if len(self.prefix) > 8388608:
                        guard.deny('outside_source_writes', 'JSON_SIZE_CAP')
                    try:
                        decoded = json.loads(self.prefix)
                    except (ValueError, UnicodeError):
                        pass
                    else:
                        guard._check_json(decoded)
                return stream.write(value)
            def writelines(self, values):
                for value in values:
                    self.write(value)
        return CheckedWriter()
    def __enter__(self):
        global _ACTIVE_GUARD
        if self.active or _ACTIVE_GUARD is not None:
            raise SourceBoundaryViolation('GUARD_NOT_REENTRANT')
        self.active = True
        _ACTIVE_GUARD = self
        try:
            self._require_clean_financial_graph()
            self._discover_loaded_boundaries()
            grid=sys.modules.get('frozen_grid')
            if grid is not None:
                self._block(grid,'_vendor','financial_imports')
                self._block(grid,'_load','financial_imports')
            self._original_import = builtins.__import__
            self._stack.enter_context(patch.object(builtins, '__import__', self._check_import))
            original_import_module = importlib.import_module
            def import_module(name, package=None):
                resolved = importlib.util.resolve_name(name, package) if name.startswith('.') else name
                self._check_import(resolved, fromlist=('*',))
                return original_import_module(name, package)
            self._stack.enter_context(patch.object(importlib, 'import_module', import_module))
            # No source operation needs a direct filename loader. The exact
            # original signal/tier/quality routines use selected pure ASTs.
            self._block(importlib.util, 'spec_from_file_location', 'financial_imports')
            for loader in (importlib.machinery.SourceFileLoader, importlib.machinery.SourcelessFileLoader):
                self._block(loader, 'exec_module', 'financial_imports')
            for name in ('Popen', 'run', 'call', 'check_call', 'check_output'):
                self._block(subprocess, name, 'process_launches')
            for name in ('system', 'fork', 'forkpty', 'posix_spawn', 'posix_spawnp', 'execv', 'execve', 'execvp', 'execvpe', 'execl', 'execlp', 'execle', 'execlpe'):
                self._block(os, name, 'process_launches')
            self._block(multiprocessing.process.BaseProcess, 'start', 'process_launches')
            self._block(fcntl, 'flock', 'canonical_financial_claims_or_leases')
            self._block(fcntl, 'lockf', 'canonical_financial_claims_or_leases')
            for obj, names in ((socket, ('create_connection', 'getaddrinfo', 'gethostbyname', 'gethostbyname_ex')),
                (socket.socket, ('connect', 'connect_ex', 'sendto', 'send', 'sendall')),
                (urllib.request, ('urlopen',)), (urllib.request.OpenerDirector, ('open',)),
                (http.client.HTTPConnection, ('connect',)), (http.client.HTTPSConnection, ('connect',))):
                for name in names:
                    self._block(obj, name, 'network_calls')
            for obj in (builtins, io):
                original = obj.open
                def opened(file, mode='r', *args, _original=original, **kwargs):
                    if any(c in mode for c in 'wax+'):
                        self._check_write(file)
                    if 'r' in mode or '+' in mode:
                        self._check_read(file)
                    return self._writer(_original(file, mode, *args, **kwargs), mode)
                self._stack.enter_context(patch.object(obj, 'open', opened))
            original_os_open, original_mkdir = os.open, os.mkdir
            def os_open(path, flags, *args, **kwargs):
                if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                    self._check_write(path)
                    self.deny('outside_source_writes', 'RAW_WRITABLE_DESCRIPTOR_FORBIDDEN')
                if not flags & os.O_WRONLY:
                    self._check_read(path)
                return original_os_open(path, flags, *args, **kwargs)
            def mkdir(path, *args, **kwargs):
                self._check_write(path)
                return original_mkdir(path, *args, **kwargs)
            self._stack.enter_context(patch.object(os, 'open', os_open))
            self._stack.enter_context(patch.object(os, 'mkdir', mkdir))
            self._block(os, 'write', 'outside_source_writes')
            for deletion in ('remove', 'unlink', 'rmdir'):
                self._block(os, deletion, 'outside_source_writes')
            for name in ('rename', 'replace', 'link', 'symlink'):
                original = getattr(os, name)
                def moved(src, dst, *args, _original=original, _name=name, **kwargs):
                    self._check_write(src)
                    self._check_write(dst)
                    if _name in ('link', 'symlink'):
                        self.deny('outside_source_writes', 'LINKS_FORBIDDEN')
                    return _original(src, dst, *args, **kwargs)
                self._stack.enter_context(patch.object(os, name, moved))
            for name in ('dump', 'dumps'):
                original = getattr(json, name)
                def dump(value, *args, _original=original, **kwargs):
                    self._check_json(value)
                    return _original(value, *args, **kwargs)
                self._stack.enter_context(patch.object(json, name, dump))
            return self
        except BaseException:
            self._stack.close()
            self.active = False
            _ACTIVE_GUARD = None
            raise
    def checkpoint(self, label):
        if any(self.attempts.values()):
            raise SourceBoundaryViolation('FORBIDDEN_ATTEMPTS_FATAL_EVEN_IF_CAUGHT')
        # Record only meaningful phase changes, not every per-member budget check.
        if label != 'SOURCE_SCOPE_CHECK':
            self.checkpoints.append(dict(label=label, attempts=dict(self.attempts)))
    def __exit__(self, kind, value, tb):
        global _ACTIVE_GUARD
        self._stack.close()
        _ACTIVE_GUARD = None
        self.active = False
        if any(self.attempts.values()):
            raise SourceBoundaryViolation('FORBIDDEN_ATTEMPTS_FATAL_EVEN_IF_CAUGHT') from value
        return False
    def receipt(self, status, error=None):
        return dict(schema='OBSERVED_PORTABLE_CS_SOURCE_GUARD_V2', status=status, error=error,
            forbidden_attempts=dict(self.attempts), attempted_targets=deepcopy(self.targets),
            installed_blockers=deepcopy(self.installed), checkpoints=deepcopy(self.checkpoints),
            guard_active=self.active, observed_workspace_read_paths=dict(self.observed_read_paths),
            historical_execution_authorized=False,
            financial_execution_authorized=False)
