"""Family-bound October archive selection; reuse the public source reader."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core5-continuous-risk600-20261011'))
from prepare import SourceReader as BaseReader,git,digest


class MarkSourceReader(BaseReader):
    def read(self,row):
        if row.get('kind')=='NEW_PUBLIC_PARTS' or row.get('wrapper_id')!='OCT2022_PUBLISHED':
            return super().read(row)
        if row['family']!='markPriceKlines':
            raise ValueError('October mark reader requires independent markPriceKlines')
        index=self.inventory['source_wrappers']['OCT2022_PUBLISHED']
        raw=git('show',index['commit']+':'+index['index_path'])
        assert digest(raw)==index['index_SHA256']
        matches=[r for r in json.loads(raw)['monthly_sources']
                 if r['family']==row['family'] and r['symbol']==row['symbol'] and r['official_URL']==row['official_URL']]
        assert len(matches)==1,'Exactly one matching family/symbol/period source'
        record=matches[0];assert record['SHA256']==row['ZIP_SHA256'] and record['bytes']==row['ZIP_bytes']
        prefix=str(Path(index['index_path']).parent)+'/'
        b=b''.join(self.part(index['commit'],{**p,'path':prefix+p['path']}) for p in record['parts'])
        check=git('show',index['commit']+':'+prefix+record['checksum_path'])
        assert len(b)==row['ZIP_bytes'] and digest(b)==row['ZIP_SHA256']
        assert digest(check)==row['CHECKSUM_member_SHA256'] and check.decode()==row['official_checksum_text']
        return b,check
