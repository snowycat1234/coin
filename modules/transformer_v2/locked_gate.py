"""Require committed complete development evidence before any locked data read."""
import json,subprocess,time
from pathlib import Path
from .train import atomic,sha

def authorize_locked(state,repo):
    state,repo=Path(state),Path(repo)
    freeze_path=state/'LOCKED_CANDIDATE_FREEZE.json'
    freeze=json.loads(freeze_path.read_text())
    protocol=repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json'
    assert freeze['status']=='FROZEN_AFTER_DEVELOPMENT_BEFORE_LOCKED_READ' and not freeze['locked_read']
    assert freeze['protocol_sha256']==sha(protocol)
    for name,key in [('TRANSFORMER_V2_DEV_RESULTS.json','development_results_sha256'),('TRANSFORMER_V2_DEV_REPORT.md','development_report_sha256')]:
        assert sha(state/name)==freeze[key]
        committed=subprocess.check_output(['git','-C',str(repo),'show','HEAD:reports/transformer_v2/'+name])
        assert committed==(state/name).read_bytes(),'Development evidence must be committed before locked release'
    committed=subprocess.check_output(['git','-C',str(repo),'show','HEAD:reports/transformer_v2/LOCKED_CANDIDATE_FREEZE.json'])
    assert committed==freeze_path.read_bytes()
    results=json.loads((state/'TRANSFORMER_V2_DEV_RESULTS.json').read_text())
    assert results['status']=='DEVELOPMENT_COMPLETE_LOCKED_NOT_READ' and not results['locked_consumed']
    assert results['chosen']==freeze['chosen']
    final=json.loads((state/'FINAL_FITS.json').read_text());audit=json.loads((state/'TRANSFORMER_V2_FINAL_FIT_AUDIT.json').read_text())
    assert final['status']=='COMPLETE' and final['completed']==24 and audit['status']=='ALL24_FINAL_PAST_ONLY_FITS_AUDITED'
    assert audit['final_fits_sha256']==sha(state/'FINAL_FITS.json') and not audit['locked_read']
    exposure=json.loads((state/'DEV_EXPOSURE_RESULTS.json').read_text())
    assert exposure['status']=='COMPLETE' and not exposure['errors'] and not exposure['locked_read']
    assert exposure['candidate_freeze_sha256']==sha(freeze_path)
    committed=subprocess.check_output(['git','-C',str(repo),'show','HEAD:reports/transformer_v2/DEV_EXPOSURE_RESULTS.json'])
    assert committed==(state/'DEV_EXPOSURE_RESULTS.json').read_bytes(),'Exposure diagnostics must be committed before locked release'
    oracles=json.loads((state/'DEV_ORACLE_RESULTS.json').read_text())
    assert oracles['status']=='COMPLETE' and not oracles['errors'] and not oracles['locked_read'] and oracles['no_candidate_or_gate_change']
    assert oracles['candidate_freeze_sha256']==sha(freeze_path)
    committed=subprocess.check_output(['git','-C',str(repo),'show','HEAD:reports/transformer_v2/DEV_ORACLE_RESULTS.json'])
    assert committed==(state/'DEV_ORACLE_RESULTS.json').read_bytes(),'Horizon diagnostics must be committed before locked release'
    # Existing release is validated and reused; never open a second experiment.
    path=state/'LOCKED_READ_AUTHORIZATION.json'
    binding=dict(protocol_sha256=sha(protocol),candidate_freeze_sha256=sha(freeze_path),
                 development_report_sha256=sha(state/'TRANSFORMER_V2_DEV_REPORT.md'),
                 development_results_sha256=sha(state/'TRANSFORMER_V2_DEV_RESULTS.json'),
                 final_fits_sha256=sha(state/'FINAL_FITS.json'),final_fit_audit_sha256=sha(state/'TRANSFORMER_V2_FINAL_FIT_AUDIT.json'),
                 development_exposure_controls_sha256=sha(state/'DEV_EXPOSURE_RESULTS.json'),
                 development_oracle_support_sha256=sha(state/'DEV_ORACLE_RESULTS.json'),
                 git_commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),
                 range=['2026-03-01','2026-08-31'],formal_result_limit=1)
    if path.exists():
        old=json.loads(path.read_text());assert all(old[k]==v for k,v in binding.items() if k!='git_commit');return old
    binding.update(status='AUTHORIZED_ONE_LOCKED_EXPERIMENT',authorized_at=time.time(),economic_results_read=False,model_ranking_read=False)
    atomic(path,binding);return binding

def require_release(state,protocol_sha256):
    path=Path(state)/'LOCKED_READ_AUTHORIZATION.json'
    if not path.exists():raise RuntimeError('Locked data access refused: no committed development release')
    release=json.loads(path.read_text())
    assert release['status']=='AUTHORIZED_ONE_LOCKED_EXPERIMENT' and release['protocol_sha256']==protocol_sha256
    assert release['formal_result_limit']==1 and release['range']==['2026-03-01','2026-08-31']
    return release
