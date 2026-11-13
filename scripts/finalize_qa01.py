"""Close controlled QA01 only after an independently restored immutable candidate."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def write(p,v):(ROOT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 sections=['functional','raster','cleanup','performance','feed']
 evidence={s:read(f'reports/chart-qa01-{s}-20261113.json') for s in sections}
 assert all(v['passed'] for v in evidence.values())
 assets=evidence['performance']['assets'];assert all(v['assets']==assets for v in evidence.values())
 restore=read('reports/chart-candidate-20261113-01-restore.json');assert restore['passed'] and len(restore['checks'])==10
 archive=ROOT/'releases/chart-candidate-20261113-01.zip';assert hashlib.sha256(archive.read_bytes()).hexdigest()==restore['archive_sha256']
 p='docs/chart/contracts/chart-core-plan-v3.json';plan=read(p)
 task=next(t for t in plan['tasks'] if t['id']=='QA01');task.update(status='COMPLETED',completion_scope='CONTROLLED_DESKTOP_PHYSICAL_ACCEPTANCE_OPEN',evidence='reports/chart-qa01-delivery-20261113.json')
 plan.update(status='CONTROLLED_IMPLEMENTATION_COMPLETE_WITH_OPEN_ACCEPTANCE',next_task='REVIEW_OPEN_ACCEPTANCE',new_tasks_completed=27)
 plan['performance_acceptance'].update(status='CONTROLLED_HEADLESS_PASSED',product_raf_p95_ms=[16.8]*5,product_wheel_frame_swap_p95_ms=78.487,evidence='reports/chart-qa01-performance-20261113.json')
 plan['performance_acceptance']['limits'].append('Physical B5, trackpad/touch, screen reader and real display remain open; frame swap is not scanout')
 plan['latest_implementation']=dict(task='QA01',date='2026-11-13',python_tests=920,frontend_tests=278,build='PASSED',functional_checks=11,raster_cases=18,feed_checks=7,cleanup_cycles=20,restore_checks=10,report='docs/chart/QA01-ACCEPTANCE.md',integration_decision='KEEP_LIVE_DISABLED_PHYSICAL_AND_GENERAL_ACCEPTANCE_OPEN')
 assert sum(t['status']=='COMPLETED' for t in plan['tasks'])==27
 write(p,plan)
 update='13 Kasım 2026 — **QA01 kontrollü masaüstü doğrulaması tamamlandı; uygulama planı 27/27.** [Kabul raporu](QA01-ACCEPTANCE.md): 920 Python/278 frontend testi, 18 raster durumu, 20 cleanup döngüsü, beş 60 saniyelik performans koşusu ve 10 temiz restore kontrolü geçti. rAF p95 her koşuda16,8 ms; wheel→frame-swap p95 78,487 ms. Genel sürüm/B5 fiziksel kabul açık; canlı entegrasyon kapalı. Sıradaki iş açık fiziksel kabul maddelerinin gözden geçirilmesi. Aşağıdaki önceki teslim kayıtları tarihseldir.\n\n'
 for path in ['docs/chart/PLAN.md','docs/chart/REA04-IMPLEMENTATION-ROADMAP.md','docs/chart/RELEASE.md','docs/chart/ACCEPTANCE.md']:
  f=ROOT/path;content=f.read_text(encoding='utf-8');head,body=content.split('\n',1);f.write_text(head+'\n\n'+update+body.lstrip(),encoding='utf-8')
 f=ROOT/'docs/chart/PLAN.md';s=f.read_text(encoding='utf-8');s=s.replace('**Güncel plan26/27**;1 paket (QA01) bekliyor.','**Güncel uygulama planı27/27**; QA01 kontrollü kapsamda kapandı, fiziksel/genel kabul açık.');f.write_text(s,encoding='utf-8')
 files=[f'reports/chart-qa01-{s}-20261113.json' for s in sections]+['reports/chart-candidate-20261113-01-restore.json','reports/chart-candidate-20261113-01-manifest.json','docs/chart/QA01-ACCEPTANCE.md','docs/chart/QA01-UI-AUDIT.md','docs/chart/contracts/qa01-acceptance-v1.json',p,'docs/chart/PLAN.md','docs/chart/REA04-IMPLEMENTATION-ROADMAP.md','docs/chart/RELEASE.md','docs/chart/ACCEPTANCE.md']
 files += ['reports/qa01-'+s for s in ['python-tests.log','frontend-tests.log','build.log','g03-regression.log','g06-regression.log','t07-regression.log','t14-regression.log','p4-regression.log','p7-regression.log']]
 files += [str(x.relative_to(ROOT)).replace('\\','/') for x in (ROOT/'scripts').glob('*qa01*.py')]
 files += ['scripts/qa_chart_fixture.py','scripts/check_chart_g06.py','frontend/src/drag.ts','frontend/src/DrawingLayer.tsx','frontend/src/App.tsx','frontend/src/terminal.css','frontend/src/LocalEventHistory.tsx','frontend/src/useModalDialog.ts','frontend/src/ReplayValidation.tsx','frontend/src/RuleBindings.tsx','frontend/src/WorkspaceTemplates.tsx','frontend/src/IndicatorSettings.tsx','frontend/src/ChartCommandDialog.tsx','frontend/tests/qaCancellation.test.ts','frontend/tests/modalLifecycle.test.tsx','pyproject.toml']
 receipt=dict(task='QA01',date='2026-11-13',status='COMPLETED',completion_scope='CONTROLLED_DESKTOP',passed=True,implementation_packages_completed=27,implementation_packages_total=27,python_tests=920,frontend_tests=278,build='PASSED',assets=assets,archive=str(archive.relative_to(ROOT)).replace('\\','/'),archive_sha256=restore['archive_sha256'],restore_checks=10,full_chart_acceptance=False,b5_completed=False,bot_adapter_connected=False,live_execution_authorized=False,physical_open=['B5 D03/D05/D06','D07 previous FAIL not retested','physical trackpad','native touch','screen reader','physical display/DPR','other browsers'],candidate_snapshot_note='Archive freezes pre-promotion plan; current external restore receipt and delivery record promote controlled scope only',files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(set(files))})
 write('reports/chart-qa01-delivery-20261113.json',receipt)
 print(json.dumps(dict(passed=True,completed=27,total=27,restore_checks=10,full_chart_acceptance=False)))
if __name__=='__main__':main()
