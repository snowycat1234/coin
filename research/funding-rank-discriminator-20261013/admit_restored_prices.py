"""Hash/provenance and original-mask admission only, never score baskets."""
import hashlib
import io
import json
from pathlib import Path
import zipfile
import numpy as np
from core import DAY, SYMBOLS

HERE = Path(__file__).resolve().parent
PINS = {
    'FUNDING_DIRECTION_INPUTS.zip': ('0d2cf51769f2c9444c83b1715c5a6fd730d282e96cc4e84d1feaecf482ffdcd2', 389393),
    'CORE5_WARMUP_MASKS.npz': ('13d2cd62d6baf3059d991c11f2d2bd887a6faf571c206b11c4b3ba1e8a438bb2', 5980),
    'Y2024_TARGETS.npz': ('4f3b615b524de3220df3c10595ba2a7723f6e62dcff59b31ed82cb9476a9b5d5', 79421)
}
MEMBERS = {
    'Y2023.npz': ('1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f', 109106),
    'Y2025.npz': ('88a698ceed87603a36ca2bcf4ae76d805aa90085b344bbeee47e58a8c9770add', 131057),
    'Y2023_RAW_EVENTS.json': ('1b86be73f82c3800eead9d527fbdb35c671a93f00ca69d825593d8c1e84eb8e6', 303444),
    'Y2025_RAW_EVENTS.json': ('40d78f2d1650c8b18e7086b3714c857617756597832e057d4207d8d00aea06cf', 305896),
    'PREPARATION.json': ('c24bf0885bdc80ce8c161180099ffca5d3901db630f74b0f2c0be75f780faf47', 985184)
}


def verify(raw, pin):
    assert len(raw) == pin[1] and hashlib.sha256(raw).hexdigest() == pin[0]


def ready200(t, p, decisions):
    """Original full200/real31 CSH admission, no availability experiment."""
    out = np.zeros((len(decisions), 5), bool)
    for i, d in enumerate(decisions):
        k = int(np.searchsorted(t, d))
        if k < 199 or k >= len(t) or t[k] != d or np.any(np.diff(t[k-199:k+1]) != DAY):
            continue
        out[i] = np.all(np.isfinite(p[k-199:k+1]) & (p[k-199:k+1] > 0), axis=0)
    return out


def inspect():
    root = HERE / 'inputs_restored'
    for name, pin in PINS.items():
        verify((root/name).read_bytes(), pin)
    cubes = {}
    with zipfile.ZipFile(root/'FUNDING_DIRECTION_INPUTS.zip') as z:
        assert set(z.namelist()) == set(MEMBERS) and z.testzip() is None
        for name, pin in MEMBERS.items():
            raw = z.read(name); verify(raw, pin)
            if name in ('Y2023.npz','Y2025.npz'):
                with np.load(io.BytesIO(raw), allow_pickle=False) as a:
                    # Whitelist causal prices/clocks only. No forward price,
                    # funding outcome, CARRY/SHORT, fit or payoff arrays read.
                    assert tuple(a['symbol_order']) == SYMBOLS
                    t, p = a['close_available_us'].copy(), a['close'].copy()
                    assert t.dtype == np.int64 and p.shape == (len(t),5) and np.all(np.diff(t)==DAY)
                    cubes[name]=(t,p)
    t3,p3=cubes['Y2023.npz'];t5,p5=cubes['Y2025.npz']
    # Some independent underlying source revisions can differ. Report them
    # explicitly; never combine numerical copies without exact parity.
    assert np.array_equal(t3,t5[:len(t3)])
    prefix_equal=np.array_equal(p3,p5[:len(p3)],equal_nan=True)
    with np.load(root/'CORE5_WARMUP_MASKS.npz',allow_pickle=False) as a:
        assert tuple(a['symbol_order']) == SYMBOLS
        d=a['decision_us'].copy(); expected=np.column_stack([a[s+'_200close'] for s in SYMBOLS])
        derived=ready200(t3,p3,d)
        assert np.array_equal(derived,expected), 'Exact saved2021 original200 mask parity failed'
        assert np.array_equal(derived.all(1),a['CORE5_200close'])
    #2024 target producer45052aac... explicitly used exactY2025.npz SHA.
    # Check its existing covariance bytes against only past actual closes;
    # this is source identity, not a new target or basket evaluation.
    with np.load(root/'Y2024_TARGETS.npz',allow_pickle=False) as a:
        assert tuple(a['symbol_order'])==SYMBOLS
        d4=a['decision_us'].copy();saved_cov=a['annual_covariance'].copy()
    cov=[]
    for at in d4:
        k=int(np.searchsorted(t5,at));assert t5[k]==at
        past=p5[k-30:k+1];r=np.diff(past,axis=0)/past[:-1]
        cov.append(np.cov(r,rowvar=False,ddof=1)*365)
    exact_cov=np.array_equal(np.array(cov),saved_cov)
    assert exact_cov, 'Saved2024 original source covariance parity failed'
    inventories={}
    from datetime import datetime,timezone
    for year, name in [(2021,'Y2023.npz'),(2023,'Y2023.npz'),(2024,'Y2025.npz'),(2025,'Y2025.npz')]:
        t,p=cubes[name];first=int(datetime(year,1,1,tzinfo=timezone.utc).timestamp()*1000000)
        end=int(datetime(year+1,1,1,tzinfo=timezone.utc).timestamp()*1000000)
        d=np.arange(first,end,DAY,dtype=np.int64);m=ready200(t,p,d)
        inventories[str(year)]={'days':len(d),'close_member':name,'original_allfive200_ready_days':int(m.all(1).sum()),'original_asset200_ready_days':m.sum(0).tolist(),'mask_rule':'EXACT_REAL200_CONTIGUOUS_FINITE_POSITIVE_CURRENT_CLOSE_WITH_NO_MIN4','historical_basket_evaluations':0}
    return {'status':'PASS_RESTORED_PRICE_ORIGINAL_MASK_ADMISSION_ONLY','restored_bytes':sum(x[1] for x in PINS.values()),'files':PINS,'sealed_members':MEMBERS,'price_prefix_2023_vs2025_equal_including_NaN':prefix_equal,'2021_saved_original200_mask_bit_exact':True,'2024_original_saved_covariance_bit_exact':exact_cov,'inventory':inventories,'funding2021_2024':'NOT_RESTORED_NOT_ADMITTED','funding2023_2025':'EXACT_SEALED_RAW_MEMBERS_PRESENT_SOURCE_COVERAGE_REVIEW_PENDING','historical_basket_evaluations':0,'wallets':0,'fits':0,'provider_requests':0,'numpy_version':np.__version__}


if __name__=='__main__':
    r=inspect();path=HERE/'PRICE_MASK_ADMISSION_RECEIPT.json'
    assert not path.exists();path.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2))
