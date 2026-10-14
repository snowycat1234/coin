"""Verify/reconstruct only frozen generated journal bytes; no simulator or source inputs."""
from __future__ import annotations
import argparse,hashlib,io,json,pathlib,tarfile
HERE=pathlib.Path(__file__).resolve().parent
MAX_ARCHIVE_BYTES=2_000_000
MAX_NATIVE_BYTES=12_000_000
MAX_MEMBERS=33

def digest(data):return hashlib.sha256(data).hexdigest()
def require(ok,reason):
    if not ok:raise ValueError(reason)
def strict_json(raw):
    return json.loads(raw,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('NONFINITE_JSON_'+value)))

def verify():
    manifest=strict_json((HERE/'JOURNAL_BODY_MANIFEST.json').read_bytes())
    require(manifest['schema']=='LOSSLESS_FROZEN_GENERATED_JOURNAL_ARCHIVE_V1','MANIFEST_SCHEMA')
    require(manifest['generated_only'] is True and manifest['historical_GO'] is False,'SCOPE')
    require(manifest['archive']=='GENERATED_JOURNALS.tar.gz','ARCHIVE_NAME')
    members=manifest['members'];require(len(members)==MAX_MEMBERS,'MEMBER_COUNT')
    require(sum(x['bytes'] for x in members.values())==manifest['native_total_bytes']<=MAX_NATIVE_BYTES,'NATIVE_SIZE')
    archive=(HERE/manifest['archive']).read_bytes()
    require(len(archive)==manifest['archive_bytes']<=MAX_ARCHIVE_BYTES,'ARCHIVE_SIZE')
    require(digest(archive)==manifest['archive_SHA256'],'ARCHIVE_SHA256')
    restored={};total=0
    with tarfile.open(fileobj=io.BytesIO(archive),mode='r|gz') as tf:
        for entry in tf:
            name=entry.name;path=pathlib.PurePosixPath(name)
            require(entry.isfile() and not entry.issym() and not entry.islnk(),'REGULAR_FILES_ONLY')
            require(not path.is_absolute() and '..' not in path.parts and str(path)==name,'UNSAFE_PATH')
            require(name in members and name not in restored and len(restored)<MAX_MEMBERS,'UNEXPECTED_OR_DUPLICATE_MEMBER')
            require(path.parts[0]=='generated_journals' and len(path.parts)==2 and path.suffix=='.json','MEMBER_LAYOUT')
            meta=members[name];require(entry.size==meta['bytes'] and 0<entry.size<=MAX_NATIVE_BYTES,'MEMBER_SIZE')
            stream=tf.extractfile(entry);require(stream is not None,'MISSING_MEMBER_BODY')
            raw=stream.read(entry.size+1);require(len(raw)==entry.size,'SHORT_OR_OVERSIZED_BODY')
            require(digest(raw)==meta['SHA256'],'MEMBER_SHA256_'+name)
            require(isinstance(strict_json(raw),dict),'JOURNAL_JSON_OBJECT')
            total+=len(raw);require(total<=MAX_NATIVE_BYTES,'TOTAL_SIZE_LIMIT')
            restored[name]=raw
    require(set(restored)==set(members) and total==manifest['native_total_bytes'],'INCOMPLETE_ARCHIVE')
    return manifest,restored

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=pathlib.Path,help='New non-existing directory; omitted means verification only.')
    args=parser.parse_args();manifest,restored=verify()
    if args.output is not None:
        require(not args.output.exists() and not args.output.is_symlink(),'OUTPUT_MUST_BE_NEW')
        args.output.mkdir(parents=True,exist_ok=False)
        for name,raw in restored.items():
            p=args.output/name;p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as stream:stream.write(raw)
    print(json.dumps({'status':'PASS_EXACT_GENERATED_JOURNAL_BYTES','members':len(restored),'native_bytes':manifest['native_total_bytes'],'archive_SHA256':manifest['archive_SHA256'],'output_written':args.output is not None,'historical_GO':False,'account_resume_fork_certified':False},sort_keys=True))
if __name__=='__main__':main()
