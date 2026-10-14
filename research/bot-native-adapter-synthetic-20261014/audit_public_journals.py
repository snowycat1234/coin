"""Run byte-exact independent Decimal journal audit against a declared fresh export."""
from __future__ import annotations
import argparse,hashlib,json,pathlib,re
HERE=pathlib.Path(__file__).resolve().parent
AUDIT_SHA256='c7c345f2cb674661b3566bcef785dad76c0aa4c6e731e05b750188ca095df8b7'
SAVED_SUMMARY_SHA256='c4b41450885af676098b7229688bf210f6c13bcd7f84705d94f73a705aa97528'

def require(ok,reason):
    if not ok:raise ValueError(reason)
def sha(raw):return hashlib.sha256(raw).hexdigest()
UUID_PATTERN=re.compile(r'^(CSH_BTC_GRID_REPLACE10:[0-9]+:)([0-9a-f]{32})(:[0-9]+)?$')
SET_PATHS={('adapter_state_final','seen_native_legs'),('adapter_state_final','seen_native_funding'),('adapter_state_final','expired_sessions'),('adapter_state_final','grid','seen_fill_ids')}

def canonical(journal):
    # Alpha-renaming retains session timestamps, order suffixes, and one-to-one
    # repeated-identifier consistency. No financial/event value is omitted.
    mapping={}
    for event in journal['policy_events']:
        candidates=[]
        if 'session_id' in event:candidates.append(event['session_id'])
        candidates.extend(event.get('orders',[]))
        for text in candidates:
            match=UUID_PATTERN.fullmatch(text)
            require(match is not None,'UNKNOWN_HELPER_SESSION_IDENTIFIER')
            identity=(match.group(1),match.group(2))
            if identity not in mapping:mapping[identity]='UUID_'+str(len(mapping)+1).zfill(4)
    def visit(value,path=()):
        if isinstance(value,dict):return {k:visit(v,path+(k,)) for k,v in value.items()}
        if isinstance(value,list):
            result=[visit(v,path+('*',)) for v in value]
            if path in SET_PATHS:
                require(len({json.dumps(v,sort_keys=True) for v in result})==len(result),'DUPLICATE_SET_DERIVED_IDENTITY')
                return sorted(result,key=lambda v:json.dumps(v,sort_keys=True))
            return result
        if isinstance(value,str) and UUID_PATTERN.fullmatch(value):
            permitted=(path in {('adapter_state_final','expired_sessions','*'),('adapter_state_final','grid','session_id')} or
                (len(path)==3 and path[:2]==('policy_events','*') and path[-1]=='session_id') or
                (len(path)==4 and path[:3]==('policy_events','*','orders')) or
                (len(path)==4 and path[:3]==('adapter_state_final','policy_events','*') and path[-1]=='session_id') or
                (len(path)==5 and path[:4]==('adapter_state_final','policy_events','*','orders')))
            require(permitted,'UNDECLARED_UUID_FIELD')
            match=UUID_PATTERN.fullmatch(value);identity=(match.group(1),match.group(2));require(identity in mapping,'UNBOUND_HELPER_UUID')
            return match.group(1)+mapping[identity]+(match.group(3) or '')
        return value
    return visit(journal)

def canonical_text(journal):
    return json.dumps(canonical(journal),sort_keys=True,separators=(',',':'),allow_nan=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--candidate-output',type=pathlib.Path,required=True);parser.add_argument('--output',type=pathlib.Path,required=True)
    args=parser.parse_args();require(__debug__,'OPTIMIZED_AUDIT_REFUSED')
    script=HERE/'coin_bot_native_independent_review_20261014/audit_exported_journals.py';raw=script.read_bytes();require(sha(raw)==AUDIT_SHA256,'ORIGINAL_AUDIT_SOURCE_SHA256')
    catalogue=json.loads((HERE/'saved_generated_journals/JOURNAL_BODY_MANIFEST.json').read_text())
    require(catalogue['generated_only'] is True and catalogue['historical_GO'] is False and len(catalogue['members'])==33,'SAVED_SCOPE')
    target=args.candidate_output.resolve();require(target.is_dir(),'MISSING_FRESH_EXPORT')
    require(sha((target/'GENERATED_SUMMARY.json').read_bytes())==SAVED_SUMMARY_SHA256,'FRESH_SUMMARY_NOT_IDENTICAL_TO_PRIOR_C249')
    restore=HERE/'saved_generated_journals/restore_journals.py';restore_raw=restore.read_bytes()
    require(sha(restore_raw)=='687e952589cadca281b594013d386880b39c05385c6110e4df986f4525f2a2b2','SAVED_BYTE_VERIFIER_IDENTITY')
    restore_scope={'__name__':'verified_saved_journal_transport','__file__':str(restore)}
    exec(compile(restore_raw,str(restore),'exec'),restore_scope)
    _,saved_bodies=restore_scope['verify']()
    actual_members={p.relative_to(target).as_posix() for p in (target/'generated_journals').iterdir() if p.is_file()}
    require(actual_members==set(catalogue['members']),'FRESH_EXPORT_MEMBER_SET')
    for name,meta in catalogue['members'].items():
        path=target/name;require(not path.is_symlink() and path.resolve().is_relative_to(target),'UNSAFE_EXPORT_MEMBER')
        old=json.loads(saved_bodies[name]);fresh=json.loads(path.read_bytes())
        require(canonical_text(old)==canonical_text(fresh),'COMPLETE_FRESH_JOURNAL_PARITY_'+name)
    require(not args.output.exists() and not args.output.is_symlink(),'AUDIT_OUTPUT_MUST_BE_NEW');args.output.mkdir(parents=True,exist_ok=False)
    scope={'__name__':'verified_unchanged_independent_decimal_audit','__file__':str(script)}
    exec(compile(raw,str(script),'exec'),scope)
    # Declared transport-only runtime rebinding. Original financial audit source is unchanged.
    scope['CANDIDATE']=target;scope['HERE']=args.output.resolve();scope['main']()
    result=json.loads((args.output/'JOURNAL_AUDIT_RECEIPT.json').read_text());require(result['status']=='PASS_EXACT_GENERATED_JOURNAL_AUDIT' and result['journals']==33,'INDEPENDENT_JOURNAL_AUDIT_FAILED')
    print(json.dumps({'status':'PASS_COMPLETE_33_JOURNAL_PARITY_AND_UNCHANGED_DECIMAL_AUDIT','audit_source_SHA256':AUDIT_SHA256,'complete_journals_equal_under_declared_identity_only_normalization':33,'saved_native_bytes_losslessly_exact':True,'historical_GO':False,'historical_closure_admitted':False,'account_resume_fork_certified':False},sort_keys=True))
if __name__=='__main__':main()
