"""One deterministic two-writer/freshness fixture; all files stay in STATE."""
import ast
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path('/mnt/d/codex/coin')


def test_sampler_preserves_live_phase_without_sharing_publisher_temporary(monkeypatch, tmp_path):
    assert tmp_path.is_relative_to(Path('/home/xflops/coin-state'))
    spec = importlib.util.spec_from_file_location('isolated_sampler_publishers',
        ROOT / 'tools/task_progress/task_progress_sample.py')
    sampler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sampler)
    progress = tmp_path / 'task-progress'
    progress.mkdir()
    pid, ticks, task = 123456, 98765, 'synthetic-two-writers'
    clock = [100.]
    target = progress / f'sample-{pid}.json'
    stage = dict(pid=pid, start_ticks=ticks, task_id=task, phase='实际账户计算',
        completed=2, total=4, unit='账户', metrics={'真实完成': 2}, updated_at=100.)
    unknown = dict(phase=sampler.UNKNOWN_PHASE, completed=None, total=None,
        unit='', metrics={}, pid=pid, task_id=task, updated_at=100.)
    # Run exactly the frozen publisher heartbeat, without importing its research dependencies.
    tree = ast.parse((ROOT / 'scripts/research_v7/oracle_flow_ceiling.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Progress')
    beat = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'heartbeat')
    paths = []

    def replace(source, destination):
        paths.append(Path(source))
        if Path(source).suffix == '.tmp' and Path(source).name == f'sample-{pid}.tmp':
            # Deterministic adverse interleaving: sampler publishes after the stage
            # writer creates its temp, before that writer renames it.
            sampler.write_snapshot(dict(unknown))
        os.replace(source, destination)

    fake_os = SimpleNamespace(getpid=lambda: pid, replace=replace,
        environ={'COIN_TASK_ID': task})
    monkeypatch.setattr(sampler, 'STATE', progress)
    monkeypatch.setattr(sampler, 'START_TICKS', ticks)
    monkeypatch.setattr(sampler, 'os', fake_os)
    monkeypatch.setattr(sampler, 'sys', SimpleNamespace(_current_frames=lambda: {}))

    def stop_after_one(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(sampler, 'time', SimpleNamespace(time=lambda: clock[0], sleep=stop_after_one))
    publisher_env = dict(STATE=tmp_path, json=json, os=fake_os,
        time=SimpleNamespace(time=lambda: clock[0]))
    exec(compile(ast.fix_missing_locations(ast.Module([beat], type_ignores=[])),
        'frozen-Progress-heartbeat-only', 'exec'), publisher_env)
    stop = SimpleNamespace(done=False)
    stop.is_set = lambda: stop.done
    stop.wait = lambda _seconds: setattr(stop, 'done', True)
    publisher_env['heartbeat'](SimpleNamespace(pid=pid, value=dict(stage), stop=stop))
    assert paths == [target.with_suffix('.tmp'), target.with_suffix('.stack-sampler.tmp')]
    assert len(set(paths)) == 2
    assert not any(p.exists() for p in paths)
    assert json.loads(target.read_text()) == stage

    def sample_once():
        with pytest.raises(KeyboardInterrupt):
            sampler.sample_loop(999999)

    # Preserve explicit data without refreshing its timestamp or inventing counts.
    for now in (102., 106.):
        clock[0] = now
        before = target.read_bytes()
        sample_once()
        assert target.read_bytes() == before
    # A stale, future-dated, or different identity sample must become unknown.
    for modified, now in (({}, 106.01), ({'updated_at': 109.}, 108.),
            ({'pid': pid + 1}, 102.), ({'start_ticks': ticks + 1}, 102.),
            ({'task_id': 'different-task'}, 102.), ({'phase': sampler.UNKNOWN_PHASE}, 102.)):
        target.write_text(json.dumps({**stage, **modified}))
        clock[0] = now
        sample_once()
        actual = json.loads(target.read_text())
        assert actual['phase'] == sampler.UNKNOWN_PHASE
        assert actual['completed'] is None and actual['total'] is None
        assert actual['metrics'] == {}
        assert actual['pid'] == pid and actual['start_ticks'] == ticks
        assert actual['task_id'] == task and actual['updated_at'] == now
    target.write_text('{invalid-json')
    sample_once()
    assert json.loads(target.read_text())['completed'] is None
