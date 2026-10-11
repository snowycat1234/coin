"""Prepare a fresh public-source reproduction; fit only with explicit --run.

This post-result convenience wrapper adds no scientific recipe. It reuses the
source-bound runner unchanged and never repeats the training GP fit.
"""
import argparse
import json
import subprocess
import urllib.request
from pathlib import Path

from modules.slow_momentum_cpd.run import ROOT, recover_archive, sha, write_json
from modules.slow_momentum_cpd.cost_training import ARCHIVE
from modules.slow_momentum_cpd.repaired_cost import load, preservation, run
from modules.slow_momentum_cpd.repaired_data import EXPERIMENT, recover_prices

CONFIG_SHA='d54f4b20133bd281c04d1ae3eeb4f9f51a7de14d0d0cf54d439ff9f520aef891'


def main():
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--run',action='store_true')
    a=p.parse_args();state=a.state.resolve()
    if not state.is_relative_to(Path('/workspace')) or (state/'STARTED.json').exists() or (state/'SOURCE_PUBLIC_READBACK.json').exists():
        raise ValueError('Use a fresh independent /workspace STATE; no overwrite/resume')
    state.mkdir(parents=True,exist_ok=True)
    protocol=json.loads((ROOT/'research/slow-momentum-cpd-20261011/PROTOCOL.json').read_text())
    recover_archive(ROOT,ARCHIVE,protocol)  # exact existing pinned Git objects only
    config,artifacts,_,identity=load(CONFIG_SHA)
    observed=recover_prices(state)
    # Source verification uses actual1mGitobjects, rather than trusting patched
    # prices alone. Receipt timings/checkout SHA need not equal the original run.
    if observed['records']!=artifacts['DATA_REPAIR.json']['records'] or observed['repaired_training_close_sha256']!=artifacts['DATA_REPAIR.json']['repaired_training_close_sha256']:
        raise ValueError('Reproduced true source prices differ')
    unchanged=preservation()
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip()
    names=list(config['source_files'])+[str((EXPERIMENT/'prefit'/n).relative_to(ROOT)) for n in config['prefit_artifacts']]
    names += [str((EXPERIMENT/'CONFIG.json').relative_to(ROOT)),str((EXPERIMENT/'prefit/TESTS_FROZEN.xml').relative_to(ROOT)),str(Path(__file__).resolve().relative_to(ROOT))]
    files={}
    for name in names:
        with urllib.request.urlopen(f'https://raw.githubusercontent.com/snowycat1234/coin/{head}/{name}',timeout=30) as response:
            raw=response.read(1048576)
        if raw!=(ROOT/name).read_bytes():raise ValueError('Public source differs: '+name)
        files[name]=dict(sha256=sha(raw),bytes=len(raw))
    write_json(state/'SOURCE_PUBLIC_READBACK.json',dict(status='PASS',published_commit=head,config_sha256=CONFIG_SHA,files=files))
    write_json(state/'REPRODUCTION_PREFLIGHT.json',dict(status='PASS',source_commit=head,config_sha256=CONFIG_SHA,
        verified_files=len(files),training_identity=identity,preservation=unchanged,raw_source_prices_recovered=True,
        GP_fits=0,model_initializations=0,training_updates=0,validation_reads=0,provider_downloads=0,
        default_action='CHECK_ONLY; --run explicitly starts a separate fresh experiment'))
    print(json.dumps(dict(status='PASS',action='RUN' if a.run else 'CHECK_ONLY',source_commit=head,endpoints=identity['eligible_endpoints'])),flush=True)
    if a.run:run(state,CONFIG_SHA,head)


if __name__=='__main__':main()
