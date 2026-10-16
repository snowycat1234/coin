"""Separately authenticate this launcher and archive before running.

Example: python -I -S -B run_isolated_cold.py packet.zip
--trusted-zip-sha256 INDEPENDENT_SHA --receipt cold_receipt.json
"""
import argparse
import copy
import csv
import decimal
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import sys
import sysconfig
import tempfile
import zipfile

NAME = 'original_follow_pair_first6_compact_source_report_20261016_v1'
MAX_TOTAL = 4_500_000
MAX_MEMBERS = 600

def require(condition, message):
    if not condition:
        raise ValueError(message)

def archive_members(archive, trusted_sha):
    require(re.fullmatch('[0-9a-f]{64}', trusted_sha) is not None, 'TRUSTED_SHA256_REQUIRED')
    require(archive.is_file() and not archive.is_symlink() and archive.stat().st_size < MAX_TOTAL, 'ARCHIVE_BOUND')
    require(hashlib.sha256(archive.read_bytes()).hexdigest() == trusted_sha, 'OUTER_ARCHIVE_SHA256_MISMATCH')
    with zipfile.ZipFile(archive) as handle:
        members = handle.infolist()
        require(0 < len(members) <= MAX_MEMBERS, 'MEMBER_COUNT_BOUND')
        seen = set()
        total = 0
        for member in members:
            name = member.filename
            parts = name.split('/')
            require(parts[0] == NAME and len(parts) > 1 and all(p not in ('','.','..') for p in parts)
                    and '\\' not in name and ':' not in name and not name.startswith('/'), 'UNSAFE_MEMBER_PATH')
            require(name.casefold() not in seen, 'DUPLICATE_OR_CASE_COLLIDING_MEMBER')
            seen.add(name.casefold())
            require(stat.S_IFMT(member.external_attr >> 16) in (0,stat.S_IFREG), 'NONREGULAR_MEMBER')
            require(member.flag_bits & 1 == 0 and not member.is_dir(), 'ENCRYPTED_OR_DIRECTORY_MEMBER')
            require(0 <= member.file_size <= MAX_TOTAL, 'MEMBER_SIZE_BOUND')
            total += member.file_size
        require(total < MAX_TOTAL, 'TOTAL_EXPANSION_BOUND')
        return [(m.filename, handle.read(m)) for m in members]

def install_boundary(root, receipt):
    stdlib = Path(sysconfig.get_paths()['stdlib']).resolve()
    allowed_read = (root, stdlib)
    stdlib_zip = Path(sys.base_prefix)/('lib/python'+str(sys.version_info.major)+str(sys.version_info.minor)+'.zip')
    def inside(path, base):
        try:
            path.relative_to(base)
            return True
        except ValueError:
            return False
    def audit(event, args):
        if event == 'open':
            target, mode, flags = args
            if isinstance(target, int):
                raise PermissionError('COLD_FILE_DESCRIPTOR_OPEN_BLOCKED')
            path = Path(os.fsdecode(target)).resolve()
            writing = (isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
            if writing:
                if path != receipt:
                    raise PermissionError('COLD_WRITE_BLOCKED')
            elif not any(inside(path, base) for base in allowed_read) and path != stdlib_zip:
                raise PermissionError('COLD_EXTERNAL_READ_BLOCKED')
        elif event == 'exec':
            filename = Path(args[0].co_filename).resolve()
            if filename != root/'verify_packet.py' and not inside(filename,stdlib):
                raise PermissionError('COLD_HISTORICAL_EXEC_BLOCKED')
        elif event == 'import':
            name = args[0].split('.')[0]
            if name not in sys.stdlib_module_names and name not in sys.builtin_module_names:
                raise PermissionError('COLD_NONSTDLIB_IMPORT_BLOCKED')
        elif event in ('os.listdir','os.scandir'):
            path = Path(os.fsdecode(args[0])).resolve()
            if not any(inside(path, base) for base in allowed_read):
                raise PermissionError('COLD_EXTERNAL_DIRECTORY_READ_BLOCKED')
        elif event.startswith(('socket.','subprocess.','os.exec','os.spawn','os.fork','pty.')) or event in ('os.system','os.posix_spawn','ctypes.dlopen'):
            raise PermissionError('COLD_NETWORK_OR_PROCESS_BLOCKED')
        elif event in ('os.remove','os.rmdir','os.rename','os.mkdir','os.link','os.symlink','os.chmod','os.chown','shutil.rmtree'):
            raise PermissionError('COLD_MUTATION_BLOCKED')
    sys.addaudithook(audit)
    return audit

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archive',type=Path)
    parser.add_argument('--trusted-zip-sha256',required=True)
    parser.add_argument('--receipt',required=True,type=Path)
    args = parser.parse_args()
    archive = args.archive.resolve()
    receipt = args.receipt.resolve()
    require(not receipt.exists() and receipt.parent.is_dir(), 'FRESH_RECEIPT_REQUIRED')
    require(shutil.disk_usage(receipt.parent).free >= 1610612736 + MAX_TOTAL, 'FREE_DISK_FLOOR')
    members = archive_members(archive,args.trusted_zip_sha256)
    extraction = Path(tempfile.mkdtemp(prefix='follow_first6_compact_cold_')).resolve()
    for name, data in members:
        target = extraction/name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as handle:
            handle.write(data)
    root = extraction/NAME
    source = (root/'verify_packet.py').read_bytes()
    code = compile(source,str(root/'verify_packet.py'),'exec')
    os.environ.clear()
    os.environ.update({k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS')})
    sys.dont_write_bytecode = True
    sys.path[:] = [p for p in sys.path if p and 'site-packages' not in p and 'dist-packages' not in p]
    install_boundary(root,receipt)
    blocked = []
    for label, action in (
        ('external_read',lambda: open('/etc/passwd','rb')),
        ('external_directory',lambda: os.listdir('/etc')),
        ('process',lambda: os.system('true')),
        ('network',lambda: socket.socket()),
        ('unauthorized_write',lambda: open(root/'GENERATED_FORBIDDEN_WRITE','xb')),
        ('directory_mutation',lambda: os.mkdir(root/'GENERATED_FORBIDDEN_DIRECTORY')),
        ('historical_exec',lambda: exec(compile('raise RuntimeError("SHOULD_NOT_RUN")',str(root/'snapshots/inert.py'),'exec'))),
        ('nonstdlib_import',lambda: __import__('high365_forbidden_generated_probe')),
    ):
        try:
            action()
        except PermissionError:
            blocked.append(label)
        else:
            raise ValueError('COLD_NEGATIVE_CONTROL_NOT_BLOCKED:' + label)
    namespace = {'__name__':'compact_follow_first6_saved_checker','__file__':str(root/'verify_packet.py')}
    exec(code,namespace)
    result = namespace['verify'](root)
    result.update(outer_archive_SHA256=args.trusted_zip_sha256, cold_external_read_and_execution_boundary=True,
                  cold_boundary_rejected_controls=blocked,
                  extraction_path=str(root), CPU_affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
                  numerical_pools=1, launcher_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest() if Path(__file__).resolve().is_relative_to(root) else 'AUTHENTICATE_SEPARATELY')
    # The deliberately retained tiny extraction is reported for inspection;
    # removing it is outside the read-only verifier's authority boundary.
    with receipt.open('x') as handle:
        json.dump(result,handle,sort_keys=True,indent=2)
        handle.write('\n')
    print(json.dumps(result,sort_keys=True))

if __name__ == '__main__':
    main()
