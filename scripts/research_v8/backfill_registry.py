"""Catalog all prior small reports, including failures; never infer a trial count."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path('/mnt/d/codex/coin')
sys.path.insert(0, str(ROOT))
from scripts.research_v8.registry import FIELDS, append_event, read_verified


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    registry = ROOT / 'reports/experiment_registry.jsonl'
    existing = {r['event_id'] for r in read_verified(registry.read_bytes() if registry.exists() else b'')}
    count = 0
    # Inventory report bytes only. Do not load data, predictions, checkpoints or holdout.
    for path in sorted((ROOT / 'reports').rglob('*')):
        if not path.is_file() or path.suffix not in ('.json', '.xml', '.md') or path == args.output:
            continue
        relative = str(path.relative_to(ROOT))
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        event_id = 'legacy-artifact:' + relative + ':' + sha
        if event_id in existing:
            continue
        try:
            document = json.loads(raw) if path.suffix == '.json' else {}
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            document = {'status': 'MALFORMED_HISTORICAL_ARTIFACT',
                        'parse_error': type(error).__name__}
        if not isinstance(document, dict):
            document = {}
        event = dict.fromkeys(FIELDS)
        event.update(event_type='LEGACY_ARTIFACT_INVENTORY', event_id=event_id,
            experiment_id='legacy:' + relative, artifact_path=relative, artifact_sha256=sha,
            git_commit=document.get('git_commit') or document.get('commit'),
            protocol_hash=document.get('protocol_hash') or document.get('protocol_sha256'),
            seed=document.get('seed'), success_failure=document.get('status') or 'UNKNOWN',
            reason_for_next_experiment='UNKNOWN_HISTORICAL; no retrospective causal attribution',
            result_influenced_later_choice='UNKNOWN_HISTORICAL', classification='SCREENING_OR_ENGINEERING',
            current_state='NO_QUALIFIED_CANDIDATE',
            missing_metadata_policy='null means UNKNOWN, not zero; artifact is not necessarily one trial',
            historical_parse_error=document.get('parse_error'),
            trial_count_eligible=False, result_values_copied=False)
        append_event(registry, event)
        count += 1
        if count % 25 == 0:
            print(json.dumps({'phase': '旧成功/失败/中断工件登记', 'completed': count,
                              'total': None, 'unit': '工件'}), flush=True)
    records = read_verified(registry.read_bytes())
    report = {'status': 'PASS_APPEND_ONLY_LEGACY_ARTIFACT_CATALOG_WITH_UNKNOWN_FIELDS',
              'new_records': count, 'total_records': len(records),
              'registry_sha256_at_acceptance': hashlib.sha256(registry.read_bytes()).hexdigest(),
              'registry_prefix_bytes_at_acceptance': registry.stat().st_size,
              'unique_event_ids': len({r['event_id'] for r in records}),
              'trial_count_complete': False, 'statistical_correction_eligible': False,
              'limitations': ['Artifact catalog is not a complete reconstructed trial history.',
                             'One experiment can have many artifacts, seeds, folds and failed starts.',
                             'Unknown historical metadata must be reconciled before DSR/PBO/SPA claims.'],
              'source_hashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [Path(__file__), ROOT/'scripts/research_v8/registry.py']},
              'locked_consumed': False, 'models_fit': 0, 'orders_sent': 0}
    with args.output.open('x') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({'status': report['status'], 'new_records': count}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
