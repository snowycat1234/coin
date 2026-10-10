"""Correct one read-only journal pathname; finish original accounts without replay.

The frozen auditor requested account/minute.parquet, whereas the original
save_case writes account/minute_nav_inventory.parquet. Only that path is
translated. Original frozen runner, auditor and financial sources stay intact.
"""
import argparse,fcntl,hashlib,json,os,resource,signal,socket,sys
from pathlib import Path
import numpy as np
import q4_native92 as run


class OriginalJournalPath(type(Path())):
    def __truediv__(self,key):
        if key=='account/minute.parquet':key='account/minute_nav_inventory.parquet'
        return super().__truediv__(key)


def verify(directory,state):
    from verify_q4_native92 import verify as unchanged
    return unchanged(OriginalJournalPath(directory),state)


def finish(state,arm):
    import polars as pl
    run.source_check(state);fractions,budgets,gate=run.check(state,arm);output=state/'q4-native92'/arm;binding=run.read(output/'BINDING.json');execution=run.read(output/'EXECUTION.json');plan=run.read(run.PUBLIC/(arm+'.json'));ledger=state/'q4-native92-ledger'/gate['request_sha256']
    run.require(execution['status']=='COMPLETE_CONDITIONAL_ACCOUNT' and execution['completed_minutes']==131046 and run.read(ledger)['status']=='COMPLETE_CONDITIONAL_ACCOUNT' and binding['plan_sha256']==run.sha(run.PUBLIC/(arm+'.json')) and binding['request_sha256']==gate['request_sha256'] and gate==plan['mapping_preflight'],'Only completed original unaudited account may finish; no wallet advance')
    audit=verify(output,state);run.write_once(output/'INDEPENDENT_AUDIT.json',run.encoded(audit));sim,pointer=run.restore(output/'recovery',binding,run.window(state));minute=pl.read_parquet(output/'account/minute_nav_inventory.parquet');summary=run.read(output/'account/summary.json')
    run.require(np.array_equal(minute.drop('close_us').to_numpy(),np.concatenate(sim.minute_chunks)) and np.array_equal(pl.read_parquet(output/'account/targets.parquet')['target_weight'].to_numpy().reshape(92,5),fractions),'Original numeric checkpoint and request journals differ')
    run.require(sim.account.trades==run.read(output/'account/trades.json') and sim.funding_journal==run.read(output/'account/funding.json') and abs(float(sim.account.nav())-summary['NAV'])<1e-8 and all(p.quantity==0 for p in sim.account.positions.values()),'Original restored account and paid final journals differ')
    recovery=dict(status='PASS_ORIGINAL92_PARTIAL_TERMINAL_FULL_SNAPSHOT_RECOVERY',state_hash=sim.state_hash(),completed_decisions=92,completed_minutes=131046,account_snapshot_exact=True,minute_journal_bit_exact=True,wallet_advanced_after_restore=False,terminal_paid_flat=True)
    run.write_once(output/'RECOVERY_AUDIT.json',run.encoded(recovery));run.write_once(output/'READ_ONLY_COMPLETION.json',run.encoded(dict(status='PASS_COMPLETED_ORIGINAL_ACCOUNT_WITH_CORRECTED_JOURNAL_PATH',original_runner_and_auditor_preserved=True,only_path_translation=dict(requested='account/minute.parquet',actual_original='account/minute_nav_inventory.parquet'),completion_source_SHA256=run.sha(Path(__file__)),account_advanced=False,completed_wallet_rerun=False,financial_parameters_changed=False)))
    run.atomic(ledger,run.encoded(dict(status='COMPLETE_AND_AUDITED',binding=binding)));print(json.dumps(dict(status='COMPLETE_AND_AUDITED_NO_REPLAY',arm=arm,net_PnL=summary['net_PnL'],minute_max_drawdown=summary['minute_max_drawdown'],terminal=audit['terminal'])),flush=True)


def start(state,arm,commit):
    # The original run owns all financial execution. Catch only the known
    # final read-only pathname error after its full paid-flat completion.
    run.require(not (state/'q4-native92'/arm).exists(),'No completed or reserved account may start again')
    try:run.run(state,arm,commit)
    except FileNotFoundError as ex:
        expected=state/'q4-native92'/arm/'account/minute.parquet'
        run.require(str(expected) in str(ex) and (state/'q4-native92'/arm/'account/minute_nav_inventory.parquet').is_file(),'Unexpected missing input must stop')
        finish(state,arm)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('finish','start'));p.add_argument('--state',type=Path,required=True);p.add_argument('--arm',choices=tuple(run.ARMS),required=True);p.add_argument('--plan-commit');a=p.parse_args()
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    def offline(*args,**kwargs):raise RuntimeError('Q4 original-account completion forbids network')
    socket.create_connection=offline;socket.socket.connect=offline;locks=a.state/'q4-native92-locks';locks.mkdir(exist_ok=True)
    with (locks/a.arm).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.command=='finish':finish(a.state,a.arm)
        else:run.require(a.plan_commit is not None,'Published original plan commit required');start(a.state,a.arm,a.plan_commit)
