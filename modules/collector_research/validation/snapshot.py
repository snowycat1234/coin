"""Register two explicitly selected completed studies; never select by PnL."""
import json
from pathlib import Path
from .runtime import SOURCE,WORK,atomic,sha
from pipeline.common import code_digest

def snapshot(fraction,percent):
    entries={}
    for tag,value,expected in [('raw_fraction',fraction,1.),('raw_percent',percent,.01)]:
        study=Path(value).resolve()
        if not study.is_relative_to(WORK/'research'):raise ValueError('Study must belong to the specified external collector work directory')
        binding=json.loads((study/'BINDING.json').read_text())
        assert binding['code_sha256']==code_digest()
        assert float(binding['config']['FUNDING_RATE_SCALE'])==expected
        assert (study/'TARGETS_MANIFEST.json').is_file() and (study/'FINAL_MODEL.json').is_file()
        frozen=json.loads((study/'FROZEN_RESEARCH_WINNER.json').read_text())
        entries[tag]=(study,binding,frozen)
    config=dict(entries['raw_fraction'][1]['config']);config['FUNDING_RATE_SCALE']='UNKNOWN'
    other=dict(entries['raw_percent'][1]['config']);other['FUNDING_RATE_SCALE']='UNKNOWN'
    assert config==other,'Both studies need the same feature/protocol/model settings apart from funding interpretation'
    assert entries['raw_fraction'][1]['extra_knobs']==entries['raw_percent'][1]['extra_knobs']
    value=dict(pipeline_code_sha256=code_digest(),dataset_sha256=sha(WORK/'reports/DATASET_MANIFEST.json'),
        config=config,symbols=config['SYMBOLS'].split(','),extra_knobs=entries['raw_fraction'][1]['extra_knobs'],
        producer_role='EXPLICIT_EXISTING_STUDIES_NO_PNL_SELECTION',models_retrained=False)
    path=SOURCE/'BINDING.json'
    if path.exists():assert json.loads(path.read_text())==value,'Existing source snapshot differs; preserve it and use a new source-run'
    atomic(path,value)
    for tag,(study,binding,frozen) in entries.items():
        result=dict(study_dir=str(study),report=str(study/'FINAL_REPORT.md'),**frozen)
        target=SOURCE/tag/'RESEARCH.json'
        if target.exists():assert json.loads(target.read_text())==result
        atomic(target,result)
    print('Registered both explicit completed studies; no collection or training executed')
