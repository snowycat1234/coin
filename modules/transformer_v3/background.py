"""Autonomous research plus full protected-evidence integrity closeout."""
import gzip,json,sys,time
from pathlib import Path
from modules.transformer_v2.train import atomic,sha
from .pipeline import main as run_pipeline,committed,progress
from .preserve import verify

def main():
    repo=Path(__file__).resolve().parents[2]
    if not committed(repo,'modules/transformer_v3/background.py'):raise ValueError('Commit background entry before dispatch')
    state=Path(sys.argv[sys.argv.index('--state')+1]).resolve()
    run_pipeline()
    try:
        progress(state,'VERIFY_ALL_PROTECTED_V2_EVIDENCE_AFTER_RESEARCH')
        receipt=json.loads((state/'PHASE0_V2_PRESERVATION.json').read_text());manifest=state/'V2_PROTECTED_FILES.json.gz'
        if sha(manifest)!=receipt['manifest_sha256']:raise ValueError('Protected original inventory changed')
        with gzip.open(manifest,'rt',encoding='utf-8') as f:entries=json.load(f)
        started=time.time()
        for i in range(0,len(entries),100):
            verify(entries[i:i+100]);progress(state,'VERIFY_ALL_PROTECTED_V2_EVIDENCE_AFTER_RESEARCH',completed=min(i+100,len(entries)),total=len(entries))
        proof=dict(status='PASS_ALL_PROTECTED_V2_BYTES_UNCHANGED',files=len(entries),manifest_sha256=sha(manifest),
            protected_bytes=sum(e['bytes'] for e in entries),started_at=started,finished_at=time.time())
        path=state/'FINAL_V2_PRESERVATION_AUDIT.json'
        if path.exists():
            prior=json.loads(path.read_text())
            if prior['manifest_sha256']!=proof['manifest_sha256']:raise ValueError('Preserve earlier integrity closeout')
        else:atomic(path,proof)
        progress(state,'COMPLETE_SERVER_RESEARCH_AND_PROTECTED_EVIDENCE_AUDIT',
            final_report=str(state/'TRANSFORMER_V3_FINAL_REPORT.md'),final_results=str(state/'TRANSFORMER_V3_FINAL_RESULTS.json'),
            source_branch='research/transformer-v3-oracle-policy',publication='CODE_ALREADY_PUSHED; GENERATED_PROTOCOL_AND_FINAL_REPORTS_RETAINED_ON_SERVER_FOR_PUBLICATION')
    except BaseException as exc:
        progress(state,'FAILED_PROTECTED_EVIDENCE_CLOSEOUT',error=str(exc));raise

if __name__=='__main__':main()
