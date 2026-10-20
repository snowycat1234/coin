import hashlib,json,pathlib,zipfile,io
B=pathlib.Path(__file__).resolve().parent
D=lambda b:hashlib.sha256(b).hexdigest()
def check(b,size,sha):
 if len(b)!=size or D(b)!=sha:raise ValueError('bound size/hash mismatch')
 return b
report={'account_advances':0,'provider_downloads':0,'archives':[]}
for q in ['Q1','Q2']:
 j=json.loads((B/q/'INDEX.json').read_text())
 for a in j['all_archives']:
  raw=b''.join(check((B/q/p['path'].split('/'+q+'/')[1]).read_bytes(),p['bytes'],p['SHA256']) for p in a['parts'])
  check(raw,a['ZIP_bytes'],a['ZIP_SHA256'])
  if zipfile.ZipFile(io.BytesIO(raw)).testzip() is not None:raise ValueError('CRC')
  c=a['official_checksum_text'].encode();check(c,len(c),a['CHECKSUM_SHA256'])
  report['archives'].append({'path':a['raw_path'],'bytes':len(raw),'sha256':D(raw),'CRC':True})
for q in ['JULY2023','OCTOBER2023']:
 j=json.loads((B/q/'INDEX.json').read_text());raw=b''.join(check((B/q/p['name']).read_bytes(),p['bytes'],p['SHA256']) for p in j['parts']);check(raw,j['package_bytes'],j['package_SHA256'])
 z=zipfile.ZipFile(io.BytesIO(raw))
 if z.testzip() is not None:raise ValueError('wrapperCRC')
 for a in j['members']:
  b=check(z.read(a['name']),a['bytes'],a['SHA256'])
  if a['name'].endswith('.zip'):
   if zipfile.ZipFile(io.BytesIO(b)).testzip() is not None:raise ValueError('innerCRC')
   report['archives'].append({'path':a['name'],'bytes':len(b),'sha256':D(b),'CRC':True})
report.update(status='PASS_125_PUBLISHED_ORIGINAL_ARCHIVES',archive_count=len(report['archives']),original_compressed_bytes=sum(a['bytes'] for a in report['archives']))
if report['archive_count']!=125:raise ValueError('count')
(B/'ARCHIVE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='archives'})
