"""Pure serial continuation CPU/total-state limits. No finance or cap changes."""
def choose_cpu(admission):
 candidates=sorted(set(admission['allowed_cpus'])-set(admission.get('external_busy_cpus',[])))
 if not candidates:raise RuntimeError('No currently admitted unoccupied CPU')
 return candidates[0]
def require_live_cpu(cpu,external):
 if cpu in external['external_busy_cpus']:raise RuntimeError('External reserved CPU overlaps resume worker')
def require_combined_state(source_bytes,destination_bytes,cap=250_000_000):
 if any(type(n)!=int or n<0 for n in (source_bytes,destination_bytes,cap)) or source_bytes+destination_bytes>cap:
  raise RuntimeError('Original plus recovery state exceed same-wallet250MB cap')
 return source_bytes+destination_bytes
def terminal_status(failed,remaining):return 'STOP_PARTIAL' if failed or remaining else 'ALL_CASES_FINISHED'
