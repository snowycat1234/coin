"""Generated literal source-schema funding regression only, no actual sources."""
from pathlib import Path
from copy import deepcopy
import ast,json,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
PACKAGE=Path(sys.argv.pop(1)).resolve()
sys.path.insert(0,str(PACKAGE))
import cs_common as c,cs_source as source,cs_config as config
CONTRACTS=json.loads((PACKAGE/'SOURCE_CONTRACT_MAP.json').read_bytes())
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')

def literal2022():
    values=[]
    for i in range(5550):
        values.append(dict(symbol=SYMBOLS[i%5],calc_time_ms=1640995200000+(i//5)*60000,
            raw_rate=(-.0001,0.,.0002)[i%3],reported_interval_hours=2.0 if i<99 else 4.0 if i<101 else 8.0))
    return values

def exact_bridge_projection(values):
    # Execute only the original list-comprehension AST over invented dicts.
    # No capture function, source scope, file reader, ZIP parser or provider runs.
    tree=ast.parse((PACKAGE/'cs_source_bridge.py').read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='capture_2022')
    node=next(n for n in fn.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.ListComp) and any(isinstance(t,ast.Name) and t.id=='events' for t in n.targets))
    ns={'events':deepcopy(values)};exec(compile(ast.Module(body=[node],type_ignores=[]),str(PACKAGE/'cs_source_bridge.py'),'exec'),ns)
    return ns['events']

def fixture2023():
    return [dict(symbol=s,event_us=1672531200000000+i*60000000,raw_rate=.0001,reported_interval_hours=8.0) for i in range(1095) for s in sorted(SYMBOLS)]

class FundingReview(unittest.TestCase):
    def test_01_literal2022_source_projection_preserves_raw_rates_intervals_and_unit(self):
        original=literal2022();values=exact_bridge_projection(original)
        for raw,row in zip(original,values,strict=True):
            self.assertEqual(row,dict(symbol=raw['symbol'],event_us=raw['calc_time_ms']*1000,raw_rate=raw['raw_rate'],reported_interval_hours=raw['reported_interval_hours'],raw_rate_unit='UNCONFIRMED'))
        wire=c.canonical(values);result=source.funding_events(2022,wire,CONTRACTS['years']['2022'],normalized_2022=True)
        self.assertEqual(c.canonical(result),wire)
        self.assertEqual({str(hour):sum(v['reported_interval_hours']==hour for v in result) for hour in (2.,4.,8.)},{'2.0':99,'4.0':2,'8.0':5449})
        with self.assertRaises(TypeError):result[0]['raw_rate']=1
    def test_02_exact_old2022_rule_is_finite_positive_without_new_whitelist(self):
        original=exact_bridge_projection(literal2022())
        for value in (.5,1.,1.5,3.,6.,12.,24.):
            values=deepcopy(original);values[0]['reported_interval_hours']=value
            self.assertEqual(source.funding_events(2022,c.canonical(values),CONTRACTS['years']['2022'])[0]['reported_interval_hours'],value)
    def test_03_zero_negative_nonfinite_boolean_type_and_wrong_fields_rejected(self):
        original=exact_bridge_projection(literal2022())
        for key,value in [('reported_interval_hours',0),('reported_interval_hours',-1),('reported_interval_hours',True),('reported_interval_hours','2.0'),('raw_rate',False),('raw_rate','0.0001'),('raw_rate_unit','CERTIFIED')]:
            values=deepcopy(original);values[0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):source.funding_events(2022,c.canonical(values),CONTRACTS['years']['2022'])
        for key in ('reported_interval_hours','raw_rate'):
            for token in ('NaN','Infinity','-Infinity'):
                wire=c.canonical(original).replace(('"'+key+'":'+str(original[0][key])).encode(),('"'+key+'":'+token).encode(),1)
                # Explicit nonfinite wire, never accepted by strict parser.
                with self.assertRaises(ValueError):source.funding_events(2022,wire,CONTRACTS['years']['2022'])
        for mode in ('extra','missing','duplicate','order','calendar'):
            values=deepcopy(original)
            if mode=='extra':values[0]['calc_time_ms']=1640995200000
            elif mode=='missing':del values[0]['raw_rate_unit']
            elif mode=='duplicate':values[-1]=deepcopy(values[0])
            elif mode=='order':values=values[1:]+values[:1]
            elif mode=='calendar':values[0]['event_us']=1672531200000000
            with self.subTest(mode=mode),self.assertRaises(ValueError):source.funding_events(2022,c.canonical(values),CONTRACTS['years']['2022'])
    def test_04_2023_exact_preserved_four_field_schema_unchanged(self):
        values=fixture2023();wire=c.canonical(values);result=source.funding_events(2023,wire,CONTRACTS['years']['2023'])
        self.assertEqual(c.canonical(result),wire);self.assertEqual(len(result),5475)
        for mode in ('interval2','extra_unit','raw_bool'):
            changed=deepcopy(values)
            if mode=='interval2':changed[0]['reported_interval_hours']=2.
            elif mode=='extra_unit':changed[0]['raw_rate_unit']='UNCONFIRMED'
            else:changed[0]['raw_rate']=True
            with self.subTest(mode=mode),self.assertRaises(ValueError):source.funding_events(2023,c.canonical(changed),CONTRACTS['years']['2023'])

if __name__=='__main__':unittest.main(verbosity=2)
