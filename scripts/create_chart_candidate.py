"""Create an immutable allowlisted chart candidate archive, never include local stores."""
import argparse,hashlib,importlib.metadata as md,json,os,platform,re,subprocess,sys,tomllib,zipfile
from pathlib import Path
from packaging.requirements import Requirement
ROOT=Path(__file__).resolve().parents[1]

def locked(requirements):
    found={};pending=list(requirements)
    while pending:
        req=Requirement(pending.pop())
        if req.marker and not req.marker.evaluate({'extra':''}):continue
        key=re.sub('[-_.]+','-',req.name).lower()
        if key in found:continue
        distribution=md.distribution(req.name);version=distribution.version
        assert not req.specifier or version in req.specifier,'Installed dependency violates requirement: '+req.name
        found[key]=version;pending.extend(distribution.requires or [])
    return '\n'.join(k+'=='+v for k,v in sorted(found.items()))+'\n'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--candidate',default='chart-candidate-20261110-01');args=parser.parse_args();candidate=args.candidate
    assert re.fullmatch(r'chart-candidate-[0-9]{8}-[0-9]{2}',candidate),'Invalid candidate ID'
    target=ROOT/'releases'/(candidate+'.zip')
    assert not target.exists(),'Candidate already exists; verify it, never overwrite it.'
    payload={}
    def add(path):
        rel=path.relative_to(ROOT).as_posix();assert not path.is_symlink(),'Symlink not allowed'
        assert not any(p in {'node_modules','__pycache__','.venv','.git'} or p.startswith('.env') for p in path.relative_to(ROOT).parts)
        payload[rel]=path.read_bytes()
    for folder,extensions in [('agentrader',{'.py','.json','.html','.js','.css','.txt'}),('frontend/src',{'.ts','.tsx','.css','.json','.txt'}),('frontend/tests',{'.ts','.tsx','.json'}),('tests',{'.py'})]:
        for p in sorted((ROOT/folder).rglob('*')):
            if p.is_file() and p.suffix in extensions and '__pycache__' not in p.parts:add(p)
    for name in ['pyproject.toml','frontend/package.json','frontend/package-lock.json','frontend/tsconfig.json','frontend/vite.config.ts','frontend/index.html','docs/chart/RELEASE.md','docs/chart/ACCEPTANCE.md','docs/chart/INTERACTION.md','docs/chart/PERFORMANCE.md']:add(ROOT/name)
    # Runtime probes and browser audits require their helper scripts; no logs/private stores are swept.
    for p in sorted((ROOT/'scripts').glob('*.py')):add(p)
    review=json.loads((ROOT/'reports/chart-acceptance-review-20261110.json').read_text(encoding='utf-8'))
    evidence={e['path'] for e in review['evidence'].values()}|{'reports/chart-acceptance-review-20261110.json','reports/chart-performance-gate-20261110.json','reports/chart-acceptance-review-validation-20261110.json','reports/chart-performance-10s-20261110.json','reports/chart-performance-60s-20261110.json','reports/chart-resource-lifecycle-browser-20261110.json','reports/chart-soak-browser-20261110.json','reports/indicator-reference-20261109.json','reports/chart-two-tab-browser-20261110.json','reports/chart-app-fault-recovery-browser-20261110.json','reports/chart-app-fault-recovery-validation-20261110.json','reports/chart-cl02-lifecycle-20261110.json','reports/chart-cl02-navigation-20261110.json','reports/chart-cl02-creation-20261110.json','reports/chart-visual-raster-browser-20261110.json','reports/chart-visual-raster-validation-20261110.json','reports/chart-closure-performance-60s-20261110.json','reports/chart-closure-progress-20261110.json'}
    for name in sorted(evidence):add(ROOT/name)
    config=tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'));web=config['project']['optional-dependencies']['web-test']
    payload['requirements-web-test.lock.txt']=locked(web).encode();payload['requirements-qa.lock.txt']=locked(web+['playwright','websockets','packaging']).encode()
    payload['README.md']=b'# Agentrader chart candidate\n\nDevelopment candidate only; full release/B5 acceptance remains open. See [startup and rollback](docs/chart/RELEASE.md) and [acceptance review](docs/chart/ACCEPTANCE.md).\n'
    files={n:hashlib.sha256(v).hexdigest() for n,v in sorted(payload.items())}
    manifest={'candidate':candidate,'date':'2026-11-10','status':'DEVELOPMENT_CANDIDATE_NOT_RELEASE','full_chart_acceptance':False,'b5_completed':False,'bot_integration_authorized':False,'bundle':re.search(r'index-[^"/]+\.js',payload['agentrader/web_assets/index.html'].decode()).group(),'python':platform.python_version(),'node':subprocess.check_output(['node','--version'],text=True).strip(),'npm':subprocess.check_output(['npm.cmd' if os.name=='nt' else 'npm','--version'],text=True).strip(),'python_project_version':config['project']['version'],'frontend_project_version':json.loads(payload['frontend/package.json'])['version'],'files':files,'excluded':['.env and credentials','local data/stores','node_modules/.venv/caches','full historical screenshot corpus'],'evidence':'E1/E2 candidate, no live deployment or schema rollback performed'}
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,value in sorted(payload.items()):z.writestr(name,value)
        z.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    sha=hashlib.sha256(target.read_bytes()).hexdigest()
    receipt={'candidate':candidate,'archive':str(target.relative_to(ROOT)).replace('\\','/'),'archive_sha256':sha,'files':len(files),'manifest':manifest}
    (ROOT/'reports'/('chart-candidate-manifest-20261110.json' if candidate=='chart-candidate-20261110-01' else candidate+'-manifest.json')).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'candidate':candidate,'archive_sha256':sha,'files':len(files)},ensure_ascii=True))

if __name__=='__main__':main()
