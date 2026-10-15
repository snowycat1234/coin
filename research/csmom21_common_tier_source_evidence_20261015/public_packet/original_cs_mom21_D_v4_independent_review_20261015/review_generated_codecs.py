"""Complete generated FIRST6 source years and malformed-header tests, no source reads."""
from copy import deepcopy
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
import json
import sys
import unittest
import zipfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v4'))
import cs_codec as codec
import cs_common as c
import cs_config as config
import cs_quality as quality
import cs_signal as signal
import cs_source as source
from cs_source_bridge import ACTUAL27_OPEN_POINTS_US
CONTRACTS=json.loads((c.HERE/'SOURCE_CONTRACT_MAP.json').read_bytes())

def packed(arrays):
    stream=BytesIO();np.savez_compressed(stream,**arrays);return stream.getvalue()

def curve(at,year):
    x=(np.asarray(at,dtype=np.int64)-config.period_named(year)['warmup_start'])/config.DAY
    return np.exp(x[...,None]*np.array([.0002,.0004,.0006,.0008,.001])+.006*np.sin(x[...,None]*np.array([.13,.17,.23,.29,.31])))*np.array([50000,2000,20,.5,.05])

def fake_source(year):
    contract=deepcopy(CONTRACTS['years'][str(year)]);period=config.period_named(year)
    rows,first,last=codec.STORED_DAILY[year]
    times=np.arange(first,last+config.DAY,config.DAY,dtype=np.int64)
    a={'close_available_us':times,'close':curve(times,year)}
    if year==2022:a['symbol_order']=np.array(signal.SYMBOLS)
    warm=packed(a)
    cells=[]
    if year==2022:
        missing=set(ACTUAL27_OPEN_POINTS_US)
        cls=quality.original_quality().QualityCell
        for symbol,at in sorted(missing):
            anchor=at-codec.MINUTE
            while (symbol,anchor) in missing:anchor-=codec.MINUTE
            price=float(curve(np.int64((anchor+codec.MINUTE)//config.DAY*config.DAY),year)[signal.SYMBOLS.index(symbol)])
            cells.append(cls(symbol,at,at+codec.MINUTE,at+codec.MINUTE,str(price),anchor,anchor+codec.MINUTE,anchor+codec.MINUTE,
                anchor+codec.MINUTE,anchor+codec.MINUTE,'a'*64,'INVENTED_GENERATED_ANCHOR:'+symbol+':'+str(anchor)))
        side=dict(quality='UNKNOWN_OR_DERIVED',arrival_status='UNKNOWN_NOT_CERTIFIED',derived_mark_cells=27,
            certifies_liquidation=False,certifies_no_liquidation=False,actual_publication_arrival_installation='UNKNOWN_NOT_CERTIFIED',
            actual_event_impacts='PENDING_ACTUAL_SAVED_EVIDENCE',cells=[asdict(row) for row in cells])
        contract['normalized_quality_cells_SHA256']=c.jsha(side['cells'])
    else:side={'schema':'INVENTED_GENERATED_2023_QUALITY'}
    months=[]
    for rec in contract['months']:
        t=np.arange(rec['start'],rec['start']+rec['count']*codec.MINUTE,codec.MINUTE,dtype=np.int64)
        value=curve((t+codec.MINUTE)//config.DAY*config.DAY,year)
        arrays={'times':t}
        if year==2022:arrays['available_us']=t+codec.MINUTE
        for j,symbol in enumerate(signal.SYMBOLS):
            for field in codec.FIELDS:arrays[symbol+'_'+field]=np.full(len(t),100000.,dtype=np.float64) if field=='quote_volume' else value[:,j].copy()
            if year==2022:
                for sym,at in ACTUAL27_OPEN_POINTS_US:
                    if sym==symbol and rec['start']<=at<rec['start']+rec['count']*codec.MINUTE:arrays[symbol+'_mark'][(at-rec['start'])//codec.MINUTE]=np.nan
        raw=packed(arrays);rec['hash']=c.sha(raw);rec['size']=len(raw);months.append((rec['path'],raw))
    if year==2022:side['final_endpoint_close']={symbol:float(curve(np.int64(period['end']),year)[j]) for j,symbol in enumerate(signal.SYMBOLS)}
    count=contract['events']['selected_events']//5
    ordered=signal.SYMBOLS if year==2022 else sorted(signal.SYMBOLS)
    events=[dict(symbol=symbol,event_us=period['start']+i*codec.MINUTE,raw_rate=.0001,reported_interval_hours=8,**({'raw_rate_unit':'UNCONFIRMED'} if year==2022 else {})) for i in range(count) for symbol in ordered]
    return source.assemble_inputs(year,warm,None,c.canonical(events),c.canonical(side),months,contract)

class CodecReview(unittest.TestCase):
    def test_01_complete_generated_2023_source_and_targets(self):
        fixture=fake_source(2023);arrays,proof=source.project_targets(fixture)
        self.assertEqual(arrays['decision_us'].shape,(365,));self.assertEqual(arrays['weekly_raw_CS'].shape,(365,5))
        self.assertEqual(len(fixture['events']),5475);self.assertEqual(len(fixture['months']),12)
        self.assertEqual(fixture['sidecar']['actual_CS_event_impacts'],'PENDING_CS_SAVED_EXECUTION')
        for a in arrays.values():
            self.assertFalse(a.flags.writeable)
            with self.assertRaises(ValueError):a.setflags(write=True)
        raw=source.target_blob(arrays)
        specs={key:(a.shape,a.dtype) for key,a in arrays.items()}
        decoded=codec.npz(raw,specs)
        for key,a in arrays.items():self.assertEqual(a.tobytes(),decoded[key].tobytes())
    def test_02_complete_generated_2022_carry_and_eight_genuine_recoveries(self):
        fixture=fake_source(2022);arrays,proof=source.project_targets(fixture)
        self.assertEqual(arrays['decision_us'].shape,(365,));self.assertEqual(len(fixture['quality_cells']),27)
        self.assertEqual(len(fixture['sidecar']['genuine_recovery_witnesses']),8)
        self.assertEqual(len(fixture['events']),5550);self.assertEqual(len(fixture['months']),12)
        for witness in fixture['sidecar']['genuine_recovery_witnesses']:
            self.assertTrue(witness['is_genuine']);self.assertEqual(witness['actual_publication_arrival_installation'],'UNKNOWN_NOT_CERTIFIED')
        for cell in fixture['quality_cells']:
            self.assertLess(cell.anchor_open_us,cell.minute_open_us);self.assertEqual(cell.source_freshness_clock_us,cell.anchor_available_us)
            self.assertFalse(cell.is_genuine);self.assertFalse(cell.permits_new_increase)
        self.assertEqual(fixture['sidecar']['actual_CS_position_interval_impacts'],'PENDING_CS_SAVED_EXECUTION_NOT_INHERITED_FROM_D')
    def test_03_npz_header_namespace_dtype_length_and_object_denials(self):
        raw=packed({'clock':np.array([1,2],dtype=np.int64)})
        decoded=codec.npz(raw,{'clock':((2,),'int64')});self.assertEqual(decoded['clock'].tolist(),[1,2])
        for specs in ({'clock':((3,),'int64')},{'clock':((2,),'float64')},{'missing':((2,),'int64')}):
            with self.assertRaises(ValueError):codec.npz(raw,specs)
        with self.assertRaises(ValueError):codec.npz(packed({'clock':np.array([{},{}],dtype=object)}),{'clock':((2,),'int64')})
        stream=BytesIO()
        with zipfile.ZipFile(BytesIO(raw)) as old,zipfile.ZipFile(stream,'w') as new:
            blob=old.read('clock.npy');new.writestr('clock.npy',blob);new.writestr('clock.npy',blob)
        with self.assertRaises(ValueError):codec.npz(stream.getvalue(),{'clock':((2,),'int64')})

if __name__=='__main__':unittest.main(verbosity=2)
