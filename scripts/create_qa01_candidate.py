"""QA01 immutable source candidate with current runtime evidence and no local stores."""
import argparse,hashlib,json,os,platform,re,subprocess,sys,tomllib,zipfile
from pathlib import Path
from create_chart_candidate import locked
from verify_chart_candidate import verify
ROOT=Path(__file__).resolve().parents[1]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--candidate',default='chart-candidate-20261113-01');args=ap.parse_args();name=args.candidate
 assert re.fullmatch(r'chart-candidate-[0-9]{8}-[0-9]{2}',name);target=ROOT/'releases'/(name+'.zip');assert not target.exists(),'Immutable candidate already exists'
 payload={}
 def add(path):
  assert not path.is_symlink();path=path.resolve();assert path.is_relative_to(ROOT) and path.is_file() and not path.is_symlink();rel=path.relative_to(ROOT)
  assert not any(x in ('.env','.git','.aws','.codex','.agents','node_modules','__pycache__','.venv','data') for x in rel.parts[:-1] if x!='data' or rel.parts[0]!='agentrader')
  assert path.suffix not in ('.db','.sqlite','.sqlite3','.bak','.log','.zip') and not path.name.startswith('.env')
  payload[rel.as_posix()]=path.read_bytes()
 for folder,extensions in [('agentrader',{'.py','.json','.html','.js','.css','.txt'}),('frontend/src',{'.ts','.tsx','.css','.json','.txt','.md'}),('frontend/tests',{'.ts','.tsx','.json'}),('tests',{'.py'}),('docs/chart',{'.md','.json'})]:
  for path in sorted((ROOT/folder).rglob('*')):
   if path.is_file() and (path.suffix in extensions or path.name in ('LICENSE','NOTICE')) and '__pycache__' not in path.parts:add(path)
 for path in sorted((ROOT/'scripts').glob('*.py')):add(path)
 for name_ in ('pyproject.toml','frontend/package.json','frontend/package-lock.json','frontend/tsconfig.json','frontend/vite.config.ts','frontend/index.html'):add(ROOT/name_)
 reports=['chart-qa01-functional-20261113.json','chart-qa01-raster-20261113.json','chart-qa01-cleanup-20261113.json','chart-qa01-performance-20261113.json','chart-qa01-feed-20261113.json','chart-p7-scenarios-20261113.json','chart-p7-tool-coverage-20261113.json']
 for r in reports:
  value=json.loads((ROOT/'reports'/r).read_text(encoding='utf-8'));assert value.get('passed',value.get('status')=='COMPLETED'),r
  add(ROOT/'reports'/r)
 raster=json.loads((ROOT/'reports/chart-qa01-raster-20261113.json').read_text(encoding='utf-8'))
 for item in raster['matrix']:
  p=ROOT/item['path'];add(p);add(p.with_stem(p.stem+'-native'))
 add(ROOT/'reports/chart-qa01-feed-20261113.png')
 perf=json.loads((ROOT/'reports/chart-qa01-performance-20261113.json').read_text(encoding='utf-8'));add(ROOT/perf['feedback']['trace'])
 diagnostics=['reports/chart-qa01-feedback-capture-baseline-20261113.json','reports/chart-qa01-observer-effect-20261113.json']
 for diagnostic in diagnostics:add(ROOT/diagnostic)
 config=tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'));deps=config['project']['optional-dependencies']['web-test'];payload['requirements-web-test.lock.txt']=locked(deps).encode();payload['requirements-qa.lock.txt']=locked(deps+['playwright','websockets','pillow','packaging']).encode()
 payload['README.md']=b'# QA01 controlled desktop candidate\n\nSource archive; start from this extracted root with isolated stores. See docs/chart/QA01-ACCEPTANCE.md and docs/chart/RELEASE.md. Physical B5 acceptance and live integration remain open. No user databases, credentials, installed environments or external delivery adapters are included.\n'
 files={p:hashlib.sha256(v).hexdigest() for p,v in sorted(payload.items())};manifest=dict(candidate=name,date='2026-11-13',status='CONTROLLED_DESKTOP_CANDIDATE_PHYSICAL_ACCEPTANCE_OPEN',full_chart_acceptance=False,b5_completed=False,bot_integration_authorized=False,order_authority=False,migration=8,bundle=re.search(r'index-[^"/]+\.js',payload['agentrader/web_assets/index.html'].decode()).group(),python=platform.python_version(),node=subprocess.check_output(['node','--version'],text=True).strip(),npm=subprocess.check_output(['npm.cmd' if os.name=='nt' else 'npm','--version'],text=True).strip(),files=files,excluded=['User/local databases and backups','Secrets and credentials','node_modules and installed environments','Uncurated historical screenshots/logs'],archive_scope='Source-root restoration with installed locked runtime versions, not a fresh-network dependency install or universal wheel-proof claim',evidence=reports,diagnostics_not_acceptance_gates=diagnostics)
 target.parent.mkdir(exist_ok=True)
 with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as z:
  for p,v in sorted(payload.items()):z.writestr(p,v)
  z.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 checked=verify(target);assert checked['candidate']==name
 receipt=dict(candidate=name,archive=str(target.relative_to(ROOT)).replace('\\','/'),archive_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),files=len(files),manifest=manifest)
 (ROOT/'reports'/(name+'-manifest.json')).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(candidate=name,files=len(files),sha256=receipt['archive_sha256'])))

if __name__=='__main__':main()
