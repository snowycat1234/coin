"""Read-only process identity from supported status.PPid, never command names."""
from __future__ import annotations
import os
from pathlib import Path


def own_process_ids(proc_root=Path('/proc'), root_pid=None):
    root_pid=os.getpid() if root_pid is None else int(root_pid)
    parent={}
    for directory in Path(proc_root).iterdir():
        if not directory.name.isdigit():continue
        try:
            fields=dict(line.split(':',1) for line in (directory/'status').read_text().splitlines() if ':' in line)
            pid=int(fields['Pid']);ppid=int(fields['PPid'])
            if pid==int(directory.name) and pid>0 and ppid>=0:parent[pid]=ppid
        except (FileNotFoundError,ProcessLookupError,PermissionError,KeyError,ValueError):
            # Missing identity cannot silently classify a financial process as
            # owned. The caller still scans its cmdline as a possible external.
            continue
    descendants={root_pid}
    changed=True
    while changed:
        new={pid for pid,ppid in parent.items() if ppid in descendants}
        changed=bool(new-descendants);descendants.update(new)
    # A financial parent, sibling or orphan remains external. Never exclude
    # an ancestor merely because it launched this process.
    return descendants


def fixed_external_observation(original_gate, proc_root=Path('/proc')):
    """Preserve all original detection/reservations except the own-ID filter."""
    proc_root=Path(proc_root);owned=own_process_ids(proc_root);packs=[];histories=[]
    for directory in proc_root.iterdir():
        if not directory.name.isdigit() or int(directory.name) in owned:continue
        try:
            args=(directory/'cmdline').read_bytes().decode().split('\0');pid=int(directory.name)
            if any(arg.endswith(original_gate.PACK_RELATIVE) or arg.endswith(original_gate.PACK_VERIFY_RELATIVE) for arg in args):
                packs.append({'pid':pid,'reserved_bytes':original_gate.PACK_RESERVED_BYTES,'allowed_cpus':sorted(os.sched_getaffinity(pid))})
            elif any(any(arg.endswith(marker) for marker in original_gate.PRIOR_RUNNERS) for arg in args):
                histories.append(pid)
        except (FileNotFoundError,ProcessLookupError,PermissionError,UnicodeError):pass
    task=original_gate.task_reservation()
    return {**task,'guard_pack_processes':packs,'prior_historical_processes':histories,
        'external_reserved_bytes':max(task['task_reserved_bytes'],len(packs)*original_gate.PACK_RESERVED_BYTES),
        'external_busy_cpus':sorted(set(task['task_busy_cpus'])|{cpu for row in packs for cpu in row['allowed_cpus']})}
