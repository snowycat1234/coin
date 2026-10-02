"""Clarify persisted UTC boundaries after a clock incident; no healthy-time claim."""
import json
from datetime import UTC, datetime
from quant.paths import ROOT
from quant.research_fast.dataset import file_sha

source = ROOT/'reports/fast_research/V8_L1_CLOCK_INCIDENT_RECOVERY_20261002_V2.json'
receipt = json.loads(source.read_text())
old, gap = receipt['old_checkpoint'], receipt['restart_gap_audit']['payload']
result = {
    'status': 'CLOCK_INCIDENT_GAP_SCOPE_CLARIFICATION',
    'created_utc': datetime.now(UTC).isoformat(),
    'recovery_report': str(source), 'recovery_report_sha256': file_sha(source),
    'restart_gap_checkpoint_to_session_seconds': receipt['restart_gap_seconds'],
    'last_original_actual_packet_received_us': old['last_received_us'],
    'last_original_checkpoint_asof_us': old['asof_us'],
    'checkpoint_minus_last_original_actual_packet_seconds': (old['asof_us']-old['last_received_us'])/1e6,
    'old_actual_packet_to_new_session_wall_timestamp_seconds': (gap['end_us']-old['last_received_us'])/1e6,
    'old_actual_packet_to_new_first_accepted_packet_seconds': 'UNKNOWN_FIRST_PACKET_NOT_IN_ACCEPTANCE_RECEIPT',
    'old_session_observed_monotonic_seconds': old['observed_monotonic_seconds'],
    'clock_incident': receipt['original_clock_incident'],
    'meaning': 'RESTART_GAP is the frozen checkpoint-to-new-session audit interval, not the complete packet-absence interval. Wall-clock incident timestamps do not certify elapsed healthy real time.',
    'certified_real_time_days': 0, 'healthy_time_spliced': False,
    'old_partial_windows_are_complete': False, 'qualified_candidate': 'NONE'}
target = ROOT/'reports/fast_research/V8_L1_CLOCK_GAP_SCOPE_20261002_V1.json'
with target.open('x') as stream:
    json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
print(json.dumps({k: result[k] for k in ('status', 'restart_gap_checkpoint_to_session_seconds',
    'checkpoint_minus_last_original_actual_packet_seconds', 'old_actual_packet_to_new_session_wall_timestamp_seconds')}), flush=True)
