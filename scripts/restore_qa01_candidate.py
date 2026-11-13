"""Restore the candidate into a fresh root and exercise actual loopback/restart."""
import argparse,hashlib,json,os,socket,subprocess,sys,tempfile,time,zipfile
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from verify_chart_candidate import verify
ROOT=Path(__file__).resolve().parents[1]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('archive');args=ap.parse_args();archive=(ROOT/args.archive).resolve();manifest=verify(archive);result=dict(task='QA01_RESTORE',passed=False,candidate=manifest['candidate'],archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),checks=[])
 def record(name):result['checks'].append(dict(name=name,passed=True))
 with tempfile.TemporaryDirectory(prefix='qa01-restored-') as folder:
  folder=Path(folder);restored=folder/'source';restored.mkdir()
  with zipfile.ZipFile(archive) as z:z.extractall(restored)
  assert all(hashlib.sha256((restored/p).read_bytes()).hexdigest()==sha for p,sha in manifest['files'].items());record('all_extracted_file_hashes_match')
  assert not any(p.startswith(('data/','.env','.aws/','.codex/')) or p.endswith(('.db','.sqlite3','.bak')) for p in manifest['files']);record('no_user_stores_credentials_or_backup_files')
  env=dict(os.environ);env.pop('PYTHONPATH',None);state=folder/'state';state.mkdir();env.update(AGENTRADER_WEB_DATABASE=str(state/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(state/'execution.db'),AGENTRADER_CHART_DATABASE=str(state/'market.db'),AGENTRADER_WEB_TOKEN='')
  imported=subprocess.run([sys.executable,'-c','import agentrader,sys;from pathlib import Path;assert Path(agentrader.__file__).resolve().is_relative_to(Path.cwd());print("restored source")'],cwd=restored,env=env,capture_output=True,text=True,timeout=10);assert imported.returncode==0,imported.stderr;record('python_imports_extracted_source_not_workspace')
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  base=f'http://127.0.0.1:{port}';opener=build_opener(ProxyHandler({}));process=None
  def request(path,body=None,method=None,raw=False):
   req=Request(base+path,data=json.dumps(body).encode() if body is not None else None,method=method or ('PUT' if body is not None else 'GET'),headers={'Content-Type':'application/json'})
   with opener.open(req,timeout=5) as r:return r.read() if raw else json.load(r)
  def start():
   nonlocal process
   process=subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=restored,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
   for _ in range(100):
    try:request('/api/health');return
    except Exception:time.sleep(.1)
   raise AssertionError('Restored server unavailable')
  def stop():
   if process and process.poll() is None:process.terminate();process.wait(timeout=10)
  try:
   start();health=request('/api/health');assert health['mode']=='LOCAL_READ_ONLY' and not health['private_api_enabled'] and not health['trading_commands_enabled'];record('keyless_loopback_health_no_order_authority')
   assert manifest['bundle'].encode() in request('/',raw=True)
   for p,sha in manifest['files'].items():
    if p.startswith('agentrader/web_assets/assets/'):assert hashlib.sha256(request('/assets/'+Path(p).name,raw=True)).hexdigest()==sha
   record('all_http_assets_match_archive')
   assert request('/api/binding-catalog')['state']=='VERIFIED_TRACEABILITY';summary=request('/api/replay-validation');assert summary['state']=='VERIFIED_ISOLATED' and summary['passed_count']==36;record('restored_binding_and36_scenario_evidence_verified')
   drawing=request('/api/workspaces/main/drawings',dict(request_id='restore',geometry=dict(kind='horizontal',symbol='BTCUSDT',price_source='LAST_PRICE',label='Restored',anchors=[dict(time=1800000000,price='100')])),'POST');d_id=drawing['drawing_id'];request('/api/drawings/'+d_id,dict(request_id='edit',expected_revision=1,geometry={**drawing['geometry'],'label':'Restored edit'}),'PATCH');saved=request('/api/drawings/'+d_id);stop();start();assert request('/api/drawings/'+d_id)==saved;assert request('/api/replay-validation')['report_sha256']==summary['report_sha256'];record('drawing_revision_and_evidence_survive_real_restart')
   assert request('/api/workspaces/main/local-events')['events']==[];assert not (state/'execution.db').exists();record('no_execution_database_or_event_worker_created')
  finally:stop()
  # Exercise old schema upgrade + its actual SQLite backup in isolated state.
  migration_script="""
from pathlib import Path
from contextlib import closing
import agentrader.migrations as m,sys
p=Path(sys.argv[1]);original=m.MIGRATIONS;m.MIGRATIONS=original[:7];m.migrate(p);m.MIGRATIONS=original
with closing(m.connect(p)) as db,db:db.execute("INSERT INTO app_chart_local_intents VALUES ('legacy','owner','main','replay:restore','PENDING_FAKE',0,'{}')")
m.migrate(p)
with closing(m.connect(p)) as db:assert db.execute("SELECT state FROM app_chart_local_intents WHERE event_id='legacy'").fetchone()[0]=='PENDING_FAKE';assert db.execute('SELECT MAX(version) FROM app_schema_migrations').fetchone()[0]==8
backups=list(p.parent.glob(p.name+'.before-v8-*.bak'));assert len(backups)==1
with closing(m.connect(backups[0])) as db:assert db.execute('SELECT MAX(version) FROM app_schema_migrations').fetchone()[0]==7;assert db.execute("SELECT COUNT(*) FROM app_chart_local_intents WHERE event_id='legacy'").fetchone()[0]==1
"""
  migrated=subprocess.run([sys.executable,'-c',migration_script,str(state/'legacy.db')],cwd=restored,env=env,capture_output=True,text=True,timeout=20);assert migrated.returncode==0,migrated.stderr;record('schema7_upgrade8_preserves_intent_and_restorable_schema7_backup')
  tampered=folder/'tampered.zip'
  with zipfile.ZipFile(archive) as original,zipfile.ZipFile(tampered,'w') as bad:
   for name in original.namelist():bad.writestr(name,b'changed' if name=='agentrader/__init__.py' else original.read(name))
  try:verify(tampered)
  except AssertionError:record('tampered_archive_rejected')
  else:raise AssertionError('Tampered candidate accepted')
 result.update(passed=True,user_stores_modified=False,live_database_restored=False,server_left_running=False,full_chart_acceptance=False,b5_completed=False)
 (ROOT/'reports'/(manifest['candidate']+'-restore.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=True,checks=len(result['checks']),candidate=manifest['candidate'])))

if __name__=='__main__':main()
