"""One training-only sklearn cluster fit; current features, no future PnL.

Three relative trend clusters plus an explicit past-price crash risk override.
Names are training-centre interpretations, not certified future market states.
"""
import numpy as np
import polars as pl
import sklearn
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import GaussianMixture

FEATURES=('return_20d','ma200_distance','vol_30d','market_breadth')
PARAMETERS=dict(n_components=3,covariance_type='diag',n_init=1,max_iter=200,
    tol=.001,reg_covar=.0001,random_state=20261005,init_params='random_from_data')

def fit_predict(features,train_start,train_end,score_start,score_end):
    btc=features.filter(pl.col('symbol')=='BTCUSDT').sort('close_us')
    train=btc.filter((pl.col('close_us')>=train_start)&(pl.col('close_us')<train_end))
    score=btc.filter((pl.col('close_us')>=score_start)&(pl.col('close_us')<score_end))
    if train.height<120 or score.height==0 or train_end>score_start:
        raise ValueError('Shared global regime requires a complete past fit period')
    x=train.select(FEATURES).to_numpy().astype(np.float64)
    z=score.select(FEATURES).to_numpy().astype(np.float64)
    if not np.isfinite(x).all() or not np.isfinite(z).all():
        raise ValueError('Finite completed BTC/cross-asset regime features')
    scaler=StandardScaler().fit(x)
    gmm=GaussianMixture(**PARAMETERS).fit(scaler.transform(x))
    if not gmm.converged_: raise ValueError('One fixed GMM fit did not converge; no retry/search')
    # Equal standardised trend/breadth means; no returns from the future label.
    order=sorted(range(3),key=lambda i:(float(gmm.means_[i,[0,1,3]].sum()),i))
    mapping={order[0]:'BEAR',order[1]:'SIDEWAYS',order[2]:'BULL'}
    centres=scaler.inverse_transform(gmm.means_)
    prob=gmm.predict_proba(scaler.transform(z)); ids=prob.argmax(axis=1)
    rows=[]
    for i,r in enumerate(score.iter_rows(named=True)):
        crash=r['return_1d']<-.05 and r['vol_30d']*365**.5>.8
        rows.append(dict(available_us=int(r['close_us']),cluster_id=int(ids[i]),
            regime='HIGH_VOL_CRASH' if crash else mapping[int(ids[i])],
            crash_override=crash,posterior_max=float(prob[i].max())))
    receipt=dict(library='scikit-learn',version=sklearn.__version__,features=list(FEATURES),
        parameters=PARAMETERS,train_rows=train.height,training_max_close_us=int(train['close_us'].max()),
        fit_data_cutoff_us=int(train_end),normalizer_fits=1,regime_fits=1,direction_fits=0,
        internal_kmeans_fits=0,iterations=int(gmm.n_iter_),converged=bool(gmm.converged_),
        class_mapping={str(k):v for k,v in mapping.items()},
        centre_features={mapping[i]:dict(zip(FEATURES,map(float,centres[i]),strict=True)) for i in range(3)},
        semantics='RELATIVE_TRAINING_TREND_CLUSTERS_NOT_TRUE_OR_FUTURE_BEAR_LABELS',
        crash_rule='PAST_BTC_1D_RETURN_LT_MINUS5PCT_AND30D_ANNUAL_VOL_GT80PCT',
        future_labels_or_account_results_used=False)
    return pl.DataFrame(rows),receipt,scaler,gmm

def allowed(regime,direction):
    if regime not in ('BULL','BEAR','SIDEWAYS','HIGH_VOL_CRASH'):
        raise ValueError('Unknown regime cannot be silently traded')
    return direction>0 and regime=='BULL' or direction<0 and regime=='BEAR'
