"""Read-only candidate archive integrity verification."""
import hashlib,json,sys,zipfile
from pathlib import PurePosixPath

def verify(path):
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist();assert len(names)==len(set(names)),'Duplicate archive entries'
        for name in names:
            p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts and ':' not in name and '\\' not in name,'Unsafe archive path'
        manifest=json.loads(archive.read('MANIFEST.json'));expected=manifest['files']
        assert set(names)==set(expected)|{'MANIFEST.json'},'Unexpected/missing archive entry'
        for name,sha in expected.items():assert hashlib.sha256(archive.read(name)).hexdigest()==sha,'Checksum mismatch: '+name
        assert manifest['full_chart_acceptance'] is False and manifest['b5_completed'] is False,'Acceptance scope changed'
        return manifest

if __name__=='__main__':
    try:
        result=verify(sys.argv[1]);print(json.dumps({'passed':True,'candidate':result['candidate'],'files':len(result['files']),'full_chart_acceptance':False}));raise SystemExit(0)
    except Exception as e:print(json.dumps({'passed':False,'error':str(e)}));raise SystemExit(1)
