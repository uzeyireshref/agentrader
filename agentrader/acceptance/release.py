"""Local evidence consistency gate. This never authorizes financial execution."""
import hashlib
import json
from pathlib import Path

DEFERRED=tuple(f'G{i:02d}' for i in range(14,22))


def verify(root,report_path):
    root=Path(root).resolve()
    blocked=lambda code:dict(status='BLOCKED',error=code,financial_execution_authorized=False)
    try:
        target=Path(report_path).resolve();target.relative_to(root)
        if target.stat().st_size>1024*1024:return blocked('EVIDENCE_REPORT_TOO_LARGE')
        report=json.loads(target.read_text(encoding='utf-8'))
        if report.get('schema')!='reliability-priority-validation/1':return blocked('EVIDENCE_SCHEMA_INVALID')
        full=report['full_regression'];reliability=report['reliability_suite']
        if (type(full.get('tests_run')) is not int or full['tests_run']<max(1,report['baseline_regression_tests'])
                or full.get('result')!='OK' or full.get('skipped',0)!=0
                or reliability.get('status')!='PASSED' or reliability.get('skipped')!=0
                or report.get('chart_replay')!={'passed':36,'total':36}):return blocked('LOCAL_ACCEPTANCE_INCOMPLETE')
        if report.get('authenticated_exchange_acceptance')!='NOT_RUN' or report.get('financial_exchange_actions_performed') is not False:
            return blocked('EXTERNAL_ACCEPTANCE_SCOPE_CHANGED')
        hashes=report.get('source_sha256')
        if not isinstance(hashes,dict) or not 1<=len(hashes)<=1000:return blocked('SOURCE_MANIFEST_INVALID')
        required={'docs/development/exchange-operations-20261115/packages.json',
                  'docs/development/exchange-operations-20261115/G23-scope.json'}
        if not required<=set(hashes):return blocked('REQUIRED_EVIDENCE_NOT_BOUND')
        python_sources={p.relative_to(root).as_posix() for directory in ('agentrader','tests') for p in (root/directory).rglob('*.py')}
        if not python_sources<=set(hashes):return blocked('SOURCE_COVERAGE_INCOMPLETE')
        if report.get('hardening_scope'):
            frontend_sources = {p.relative_to(root).as_posix() for directory in ('frontend/src','frontend/tests','frontend/scripts','agentrader/web_assets')
                                for p in (root/directory).rglob('*') if p.is_file()}
            frontend_sources |= {str(p.relative_to(root).as_posix()) for name in ('package.json','package-lock.json','tsconfig.json','vite.config.ts','index.html')
                                 if (p := root/'frontend'/name).is_file()}
            frontend = report.get('frontend',{})
            if not frontend_sources<=set(hashes):return blocked('FRONTEND_SOURCE_COVERAGE_INCOMPLETE')
            if frontend.get('result')!='OK' or frontend.get('skipped')!=0 or frontend.get('build')!='OK':
                return blocked('FRONTEND_ACCEPTANCE_INCOMPLETE')
        for name,expected in hashes.items():
            p=(root/name).resolve();rel=p.relative_to(root).as_posix()
            if (not rel.startswith(('agentrader/','tests/','scripts/acceptance/','scripts/maintenance/','docs/development/exchange-operations-20261115/','reports/exchange-development-20261115/','reports/hardening-20261117/','docs/development/hardening-20261117/','frontend/'))
                    or (p.suffix not in ('.py','.md','.json','.txt','.ts','.tsx','.css','.html','.js') and p.name not in ('LICENSE','NOTICE')) or len(expected)!=64 or p.stat().st_size>20*1024*1024):
                return blocked('SOURCE_PATH_NOT_ALLOWED')
            if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:return blocked('SOURCE_EVIDENCE_STALE')
        packages=json.loads((root/'docs/development/exchange-operations-20261115/packages.json').read_text(encoding='utf-8'))['packages']
        for key in ('G13','G22'):
            if packages[key]['status']!='LOCAL_ACCEPTANCE_PASSED':return blocked('CRITICAL_PACKAGE_INCOMPLETE')
            if any(packages[d]['status']!='LOCAL_ACCEPTANCE_PASSED' for d in packages[key]['dependencies']):return blocked('CRITICAL_DEPENDENCY_INCOMPLETE')
        if packages['G23']['status']!='LOCAL_SCOPE_ACCEPTANCE_PASSED':return blocked('LOCAL_CLOSURE_INCOMPLETE')
        for key in DEFERRED:
            p=packages[key]
            if p.get('status')!='DEFERRED_BY_USER_SCOPE' or p.get('implemented') is not False or not p.get('deferred_reason'):
                return blocked('DEFERRED_PACKAGE_MISREPRESENTED')
        scope=json.loads((root/'docs/development/exchange-operations-20261115/G23-scope.json').read_text(encoding='utf-8'))
        if (scope.get('runtime_execution_scope')!='BINANCE_USDM_DEMO_EXISTING_COMMANDS'
                or set(scope.get('deferred_packages',[]))!=set(DEFERRED)
                or scope.get('full_exchange_coverage_claimed') is not False
                or scope.get('external_acceptance')!='NOT_RUN'):return blocked('CLOSURE_SCOPE_MISMATCH')
        return dict(status='LOCAL_SCOPE_VERIFIED_EXTERNAL_ACCEPTANCE_PENDING',source_files_verified=len(hashes),
                    full_tests=full['tests_run'],deferred_packages=list(DEFERRED),
                    trading_readiness='UNPROVEN',financial_execution_authorized=False)
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return blocked('EVIDENCE_UNAVAILABLE_OR_INVALID')
