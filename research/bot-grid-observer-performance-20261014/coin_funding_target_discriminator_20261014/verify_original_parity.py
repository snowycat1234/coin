"""Previously published UNLAGGED original target reproduction only.

No funding candidate, same-lag-control target, wallet, future return, charge
funding, cost or account output is calculated. This is source arithmetic QA.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from target_core import HERE,paired_targets
from inputs import load


def verify():
    result={}
    for year,(t,p,d,h,m,_,saved,cov_saved) in load().items():
        def unlagged(at,valid,price):
            k=int(np.searchsorted(t,at));score=p[k]/p[k-21]-1.
            return {'PRICE_ONLY':score,'FUNDING_ADJUSTED':score},True,{'original_source_parity_only':True}
        arms,cov,proof=paired_targets(t,p,d,h,m,unlagged)
        for a in arms:np.testing.assert_array_equal(arms[a],saved)
        assert arms['PRICE_ONLY'].tobytes()==saved.tobytes()
        if cov_saved is not None:assert cov.tobytes()==cov_saved.tobytes()
        assert not proof['daily_required_source_not_ready'].any()
        result[str(year)]={'status':'BIT_EXACT_PUBLISHED_ORIGINAL_STATIC50_TARGET_PARITY',
            'days':len(d),'cash_days':int((np.abs(saved).sum(1)==0).sum()),
            'original_target_array_sha256':hashlib.sha256(saved.tobytes()).hexdigest(),
            'covariance_sha256':hashlib.sha256(cov.tobytes()).hexdigest(),
            'saved_covariance_bit_parity':True if cov_saved is not None else 'NO_DUPLICATE_SAVED_COVARIANCE_PACKET_REQUIRED',
            'new_candidate_or_lagcontrol_targets_evaluated':0}
    return {'status':'PASS_FOUR_YEAR_ORIGINAL_SOURCE_TARGET_ARITHMETIC_PARITY_ONLY',
            'years':result,'new_candidate_or_lagcontrol_target_passes':0,'wallets':0,'fits':0,'future_outcome_arrays_read':0}


if __name__=='__main__':
    report=verify();path=HERE/'ORIGINAL_TARGET_PARITY_RECEIPT.json';assert not path.exists()
    path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
