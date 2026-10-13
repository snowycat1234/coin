"""Inspect only complete SHA-bound ZIP members in the restored prefix, no padding."""
import os,resource
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import hashlib,json,struct,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def prefix_members(max_parts=None):
    yi=json.loads((ROOT/'evidence/Y2021_INDEX.json').read_text());expected={r['name']:r for r in yi['members']};chunks=[]
    for part in yi['parts'][:max_parts]:
        p=ROOT/'source/Y2021_parts'/part['name']
        if not p.is_file():break
        b=p.read_bytes();assert len(b)==part['bytes'] and sha(b)==part['SHA256'];chunks.append(b)
    raw=b''.join(chunks);at=0;result={};records=[];incomplete=None
    while at+30<=len(raw) and raw[at:at+4]==b'PK\x03\x04':
        _,version,flags,method,mtime,mdate,crc,packed,unpacked,nlen,elen=struct.unpack_from('<IHHHHHIIIHH',raw,at)
        assert not flags&9,'Encrypted/data-descriptor sources require complete ZIP, never infer lengths'
        name=raw[at+30:at+30+nlen].decode('utf-8');extra=raw[at+30+nlen:at+30+nlen+elen]
        if packed==0xffffffff or unpacked==0xffffffff:
            pos=0
            while pos+4<=len(extra):
                tag,n=struct.unpack_from('<HH',extra,pos);data=extra[pos+4:pos+4+n];pos+=4+n
                if tag==1:
                    i=0
                    if unpacked==0xffffffff:unpacked=struct.unpack_from('<Q',data,i)[0];i+=8
                    if packed==0xffffffff:packed=struct.unpack_from('<Q',data,i)[0]
        left=at+30+nlen+elen;right=left+packed
        if right>len(raw):incomplete=dict(member=name,required_compressed_bytes=packed,available_compressed_bytes=len(raw)-left);break
        b=raw[left:right]
        if method==8:b=zlib.decompress(b,-15)
        else:assert method==0
        assert len(b)==unpacked and zlib.crc32(b)==crc and len(b)==expected[name]['bytes'] and sha(b)==expected[name]['SHA256'],name
        result[name]=b;records.append(dict(member=name,bytes=len(b),SHA256=sha(b),CRC32=f'{crc:08x}'));at=right
    return result,dict(status='PARTIAL_PUBLIC2021_WRAPPER_PREFIX_ONLY',verified_contiguous_parts=len(chunks),verified_prefix_bytes=len(raw),complete_SHA_CRC_bound_members=len(records),members=records,next_incomplete_member=incomplete,complete_wrapper_verified=False,provider_downloads=0,targets=0,wallets=0)
if __name__=='__main__':
    _,r=prefix_members();(ROOT/'LOCAL_PREFIX_RECEIPT.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='members'}))
