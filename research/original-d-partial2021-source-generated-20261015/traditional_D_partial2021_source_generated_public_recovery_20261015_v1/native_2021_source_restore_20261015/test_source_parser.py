"""Synthetic parser/clock/overlap tests only, never synthetic market inputs."""
import io,zipfile
import numpy as np
from source_parser import parse_zip,complete_grid,union_exact,strict_prior,MINUTE,START
HEADER='open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n'
def body(rows,header=HEADER):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('synthetic_parser_test.csv',header+'\n'.join(','.join(map(str,x)) for x in rows)+'\n')
    return buf.getvalue()
def rows(n=3):return [[START//1000+i*60000,100,102,99,101,1,START//1000+i*60000+59999,101,1,0.5,50.5,0] for i in range(n)]
def reject(fn):
    try:fn()
    except (AssertionError,ValueError):return
    raise AssertionError('Invalid input was accepted')
def main():
    r=rows();f,_=parse_zip(body(r),'klines',START,START+3*MINUTE);t=complete_grid(f,START,START+3*MINUTE);assert len(t)==3
    f2,rec=union_exact(f.iloc[[0,2]],f);assert rec['actual_daily_new_rows_added']==1 and rec['actual_daily_common_rows_verified']==2;complete_grid(f2,START,START+3*MINUTE)
    bad=rows();bad[1][4]=999;reject(lambda:parse_zip(body(bad),'klines',START,START+3*MINUTE))
    bad=rows();bad[1][6]+=1;reject(lambda:parse_zip(body(bad),'klines',START,START+3*MINUTE))
    bad=rows();bad[1][0]*=1000;reject(lambda:parse_zip(body(bad),'klines',START,START+3*MINUTE))
    reject(lambda:complete_grid(f.iloc[[0,2]],START,START+3*MINUTE))
    bad=rows();bad.append([*r[0]]);bad[-1][4]=100.5;reject(lambda:parse_zip(body(bad),'klines',START,START+3*MINUTE))
    g=f.copy();g['close']=g['close'].astype(float);g.loc[0,'close']=100.5;reject(lambda:union_exact(f,g))
    reject(lambda:parse_zip(body(r,HEADER.replace('high,low','low,high')),'klines',START,START+3*MINUTE))
    p=np.array([101.,102.,103.]);assert strict_prior(START+MINUTE,t,p) is None;assert strict_prior(START+MINUTE+1,t,p)['mark_close']==101.;assert strict_prior(START+2*MINUTE,t,p)['mark_close']==101.;assert strict_prior(START+3*MINUTE+MINUTE+1,t,p) is None
    print('PASS 13 source-only synthetic checks: exact grid, real daily union, bad OHLC/clock/unit/duplicates/header/gap, strict-prior equality/jitter/stale/start boundaries')
if __name__=='__main__':main()
