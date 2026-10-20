"""Recover immutable public research inputs, never accounts or provider data.
Default is offline verification. --download fetches each missing GitHub object once;
errors stop without retry, alternate hosts, authentication, or overwriting files.
"""
import argparse,hashlib,json,os,pathlib,urllib.request,urllib.parse

def digest(b):return hashlib.sha256(b).hexdigest()
def recover(manifest,destination,download=False):
 root=destination.resolve();root.mkdir(parents=True,exist_ok=True);new=0
 for f in manifest['files']:
  rel=pathlib.PurePosixPath(f['local'])
  if rel.is_absolute() or '..' in rel.parts:raise ValueError('unsafe path')
  p=root/rel
  if any(x.is_symlink() for x in [p,*p.parents]):raise ValueError('symlink forbidden')
  if p.exists():b=p.read_bytes()
  elif download:
   ref=f['commit'];path=f['path']
   if len(ref)!=40 or any(c not in '0123456789abcdef' for c in ref):raise ValueError('immutable commit required')
   url='https://raw.githubusercontent.com/'+manifest['repository']+'/'+ref+'/'+urllib.parse.quote(path,safe='/')
   with urllib.request.urlopen(url,timeout=60) as response:
    if response.geturl()!=url:raise ValueError('unexpected redirect')
    b=response.read(f['bytes']+1)
   if len(b)!=f['bytes'] or digest(b)!=f['sha256']:raise ValueError('download hash mismatch: '+str(rel))
   p.parent.mkdir(parents=True,exist_ok=True)
   with p.open('xb') as out:out.write(b);out.flush();os.fsync(out.fileno())
   new+=1
  else:raise FileNotFoundError('Missing bound input: '+str(rel))
  if len(b)!=f['bytes'] or digest(b)!=f['sha256']:raise ValueError('existing hash mismatch: '+str(rel))
 return {'status':'PASS','verified_files':len(manifest['files']),'downloaded_missing_files':new,'account_advances':0,'provider_downloads':0}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--manifest',type=pathlib.Path,default=pathlib.Path(__file__).with_name('RECOVERY_MANIFEST.json'));a.add_argument('--destination',type=pathlib.Path,required=True);a.add_argument('--download',action='store_true');p=a.parse_args();print(json.dumps(recover(json.loads(p.manifest.read_text()),p.destination,p.download),indent=2))
