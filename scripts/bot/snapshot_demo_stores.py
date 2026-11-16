"""SQLite online backups before demo cutover; never reads credentials or changes sources."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from contextlib import closing
import hashlib,json,sqlite3,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def run():
    target=ROOT/'reports/demo-transition-20261113'/('stores-'+str(int(time.time())))
    target.mkdir(parents=True,exist_ok=False)
    result=[]
    for path in sorted((ROOT/'data').glob('*.sqlite3')):
        destination=target/path.name
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=10)) as source:
            with closing(sqlite3.connect(destination)) as backup:
                source.backup(backup)
                assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        result.append(dict(name=path.name,backup=str(destination.relative_to(ROOT)),sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),integrity='ok'))
    (target/'manifest.json').write_text(json.dumps(dict(source_mutations=0,stores=result),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(manifest=str((target/'manifest.json').relative_to(ROOT)),stores=len(result),source_mutations=0)))

if __name__=='__main__':run()
