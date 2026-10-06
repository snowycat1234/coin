from .final_report import decision,stable_relative_evidence,oracle_gaps,explicit_answers

def test_incomplete_locked_never_promotes_or_selects_another_model():
    dev=dict(chosen=dict(family='FIXED',mapping='NEUTRAL'),development_gate_pass=True)
    answer=decision(dev,[],[],[])
    assert answer['choice']=='B' and not answer['promotion'] and dev['chosen']['family']=='FIXED'

def test_relative_evidence_requires_four_folds_and_both_units():
    dev=[];locked=[]
    for scale in (1.,.01):
        for fold in range(5):dev.append(dict(family='A',seed='ENSEMBLE',funding_scale=scale,rank_IC_median=.1 if fold<4 else -.1,utility_rank=-.1))
        locked.append(dict(family='A',seed='ENSEMBLE',funding_scale=scale,rank_IC_median=.2,utility_rank=-.2))
    evidence=stable_relative_evidence(dev,locked,'A')
    assert all(r['stable_IC'] for r in evidence) and not any(r['stable_relative_utility'] for r in evidence)
    locked[-1]['rank_IC_median']=-.01
    assert not stable_relative_evidence(dev,locked,'A')[-1]['stable_IC']

def test_nonpositive_oracle_gap_has_no_capture_ratio():
    common=dict(window='w',funding_scale=1.,net_return_percent=0.,mapping='DIRECTIONAL',noncausal=False)
    rows=[dict(common,family='A',seed='ENSEMBLE',net_USDT=1.),dict(common,family='BASE_SMA200_SIGNED',seed='RULE',net_USDT=2.),
          dict(common,family='EXPERT_ORACLE',seed='NONCAUSAL',net_USDT=1.,noncausal=True)]
    assert oracle_gaps(rows,'A','DIRECTIONAL')[0]['diagnostic_capture_ratio'] is None

def test_all_questions_remain_explicit_when_locked_data_is_unavailable():
    dev=dict(chosen=dict(family='A',mapping='DIRECTIONAL'),rows=[],summaries=[dict(family='A',mapping=m,
             development_gate_pass=False,scenarios=[dict(funding_scale=s,complete=False) for s in (1.,.01)]) for m in ('DIRECTIONAL','NEUTRAL','COMBINED')])
    verdict=dict(choice='B',decision='CONTINUE RESEARCH, NOT YET PROMOTED',reason='NOT_EVALUABLE')
    answers=explicit_answers(dev,[],[],verdict,[])
    assert len(answers)==11 and answers[-1][1].startswith('B.')
    assert all('否' in answers[i][1] for i in (2,3)) and 'NOT_EVALUABLE' in answers[9][1]
