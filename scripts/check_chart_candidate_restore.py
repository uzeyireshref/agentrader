"""E2 safe extraction + restored-source API/restart/static smoke, no user stores."""
import argparse,hashlib,json,os,subprocess,sys,tempfile,zipfile
from pathlib import Path
from verify_chart_candidate import verify
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',default='releases/chart-candidate-20261110-01.zip');args=parser.parse_args()
    archive=ROOT/args.archive;manifest=verify(archive)
    result={'date':'2026-11-10','task':'E2_RESTORE','passed':False,'candidate':manifest['candidate'],'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'full_chart_acceptance':False}
    with tempfile.TemporaryDirectory(prefix='agentrader-candidate-') as folder:
        restored=Path(folder)/'restored';restored.mkdir()
        with zipfile.ZipFile(archive) as z:z.extractall(restored)
        assert all(hashlib.sha256((restored/n).read_bytes()).hexdigest()==sha for n,sha in manifest['files'].items())
        assert not any(n.startswith('data/') or '.env' in Path(n).parts or n.endswith(('.sqlite3','.db')) for n in manifest['files'])
        child="""
import hashlib,json,tempfile
from pathlib import Path
import agentrader
from scripts.check_local_api import check_local_api
from agentrader.api.app import create_app
from agentrader.application.settings import WebSettings
from fastapi.testclient import TestClient
root=Path.cwd();assert Path(agentrader.__file__).resolve().is_relative_to(root)
result=check_local_api(include_drawings=True)
assert result['result']=='PASSED'
with tempfile.TemporaryDirectory(prefix='candidate-static-') as folder:
 p=Path(folder);settings=WebSettings(p/'app.db',p/'execution.db',market_database=p/'market.db')
 with TestClient(create_app(settings),base_url='http://127.0.0.1') as client:
  index=client.get('/');expected=json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))['bundle'];assert index.status_code==200 and expected in index.text
  data=json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))
  for name,sha in data['files'].items():
   if name.startswith('agentrader/web_assets/assets/'):
    response=client.get('/assets/'+Path(name).name);assert response.status_code==200 and hashlib.sha256(response.content).hexdigest()==sha
 result['static_bundle_http_verified']=True
result['source_loaded_from_extracted_candidate']=True
print(json.dumps(result))
"""
        env=dict(os.environ);env.pop('PYTHONPATH',None);env['AGENTRADER_CHART_DATABASE']=str(Path(folder)/'isolated-market.db')
        run=subprocess.run([sys.executable,'-c',child],cwd=restored,env=env,capture_output=True,text=True,timeout=120)
        if run.returncode:raise RuntimeError(run.stderr[-3000:]+run.stdout[-1000:])
        result['restored_checks']=json.loads(run.stdout)
        # A modified file must be rejected; only mutate a temporary test ZIP.
        bad=Path(folder)/'modified.zip'
        with zipfile.ZipFile(archive) as src,zipfile.ZipFile(bad,'w') as dst:
            for name in src.namelist():dst.writestr(name,b'altered' if name=='agentrader/__init__.py' else src.read(name))
        try:verify(bad)
        except AssertionError:result['tampered_archive_rejected']=True
        else:raise AssertionError('Tampered archive accepted')
        result.update(passed=True,files_verified=len(manifest['files']),uses_temporary_stores=True,user_stores_modified=False,server_left_running=False,live_database_restore_performed=False)
    (ROOT/'reports'/('chart-candidate-restore-20261110.json' if manifest['candidate']=='chart-candidate-20261110-01' else manifest['candidate']+'-restore.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':True,'files':len(manifest['files']),'restored_checks':result['restored_checks']},ensure_ascii=True))

if __name__=='__main__':main()
