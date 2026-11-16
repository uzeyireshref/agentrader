"""Sequential current browser checks; archive results without replacing old evidence."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from scripts import script_path
import argparse,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/all-chart-tools-20261114'
PACKAGES={
 'P3':[
  ('indicator-five','check_chart_t10.py','chart-t10-validation-20261112.json','chart-t10-'),
  ('indicator-macd-bb','check_chart_g05.py','chart-g05-validation-20261112.json','chart-g05-'),
  ('indicator-vwap','check_chart_t11.py','chart-t11-validation-20261112.json','chart-t11-')],
 'P4':[
  ('channel-current','check_chart_t06.py','chart-t06-validation-20261115.json','chart-t06-validation-'),
  ('channel-legacy-compatibility','check_chart_t06_legacy.py','chart-t06-legacy-validation-20261115.json','chart-t06-legacy-'),
  ('wire-compatibility','check_chart_bot_contract.py','chart-bot-contract-validation-20261115.json','chart-bot-contract-validation-'),
  ('basic-edit','check_chart_t02.py','chart-t02-browser-20261110.json','chart-t02-'),
  ('ruler','check_chart_t03.py','chart-t03-browser-20261110.json','chart-t03-'),
  ('position-plan','check_chart_t04.py','chart-t04-validation-20261112.json','chart-t04-'),
  ('line-extensions','check_chart_t05.py','chart-t05-validation-20261112.json','chart-t05-'),
  ('management','check_chart_t07.py','chart-t07-validation-20261112.json','chart-t07-'),
  ('higher-timeframe','check_chart_t08.py','chart-t08-validation-20261112.json','chart-t08-'),
  ('fib-settings','check_chart_t12.py','chart-t12-validation-20261112.json','chart-t12-'),
  ('log-view','check_chart_t13.py','chart-t13-validation-20261112.json','chart-t13-'),
  ('profiles-templates','check_chart_t14.py','chart-t14-validation-20261112.json','chart-t14-'),
  ('controls-bot-boundary','check_all_tool_browser_projection.py','chart-control-bot-readability-20261114.json','chart-control-bot-readability-',['--controls']),
  ('channel-family','check_channel_family.mts','channel-family-20261113/result.json','channel-family-20261113',['http://127.0.0.1:8765']),
  ('channel-family-log','check_channel_family.mts','channel-family-log-20261113/result.json','channel-family-log-20261113',['http://127.0.0.1:8765','--log']),
  ('channel-family-dpr2','check_channel_family.mts','channel-family-dpr2-20261113/result.json','channel-family-dpr2-20261113',['http://127.0.0.1:8765','--dpr2']),
  ('two-tabs','check_chart_two_tabs.py','chart-two-tab-browser-20261110.json','chart-two-tab-'),
  ('functional','check_chart_qa01.py','chart-qa01-functional-20261113.json','chart-qa01-functional-', ['--section','functional']),
  ('cleanup','check_chart_qa01.py','chart-qa01-cleanup-20261113.json','chart-qa01-cleanup-', ['--section','cleanup']),
  ('feed-recovery','check_chart_qa01_feed.py','chart-qa01-feed-20261113.json','chart-qa01-feed-'),
  ('shadow-ui','check_shadow_tracking.py','shadow-tracking-validation-20261113.json','shadow-tracking-'),
  ('preview-ui','check_signal_previews.py','signal-preview-validation-20261113.json','signal-preview-'),
  ('approval-ui','check_chart_approval_ui.py','chart-approval-ui-validation-20261114.json','chart-approval-ui-'),
  ('alert-conditions','check_alert_conditions.mts','alerts-conditions-ui-20261113/result.json','alerts-conditions-ui-'),
  ('alert-schedule','check_alert_schedule.mts','alert-schedule-ui-20261113/result.json','alert-schedule-ui-'),
  ('alert-frequencies','check_alert_frequencies.mts','alert-frequencies-ui-20261113/result.json','alert-frequencies-ui-'),
  ('alert-channels','check_alert_channels.mts','alert-channels-ui-20261113/result.json','alert-channels-ui-'),
  ('alert-notifications','check_alert_notifications.mts','alert-notifications-20261113/result.json','alert-notifications-'),
 ]}


PACKAGES['G10_UI']=[entry for entry in PACKAGES['P4'] if not entry[0].startswith('channel-family')]

def main():
    global OUT
    p=argparse.ArgumentParser();p.add_argument('package',choices=PACKAGES);p.add_argument('--only');p.add_argument('--resume',action='store_true');p.add_argument('--output-dir',type=Path,default=OUT);args=p.parse_args();OUT=args.output_dir.resolve()
    OUT.mkdir(parents=True,exist_ok=True);path=OUT/(args.package.lower()+'-browser-suite.json')
    if path.exists() and (args.only or args.resume):r=json.loads(path.read_text(encoding='utf-8'))
    else:r=dict(package=args.package,passed=False,started_at=time.time(),checks=[],scope='Current isolated production browser checks; no user workspace or exchange writes')
    jobs=[j for j in PACKAGES[args.package] if not args.only or j[0]==args.only]
    if args.resume:jobs=[j for j in jobs if not any(c['name']==j[0] and c['state']=='PASS' for c in r['checks'])]
    if not jobs:raise ValueError('Unknown acceptance check')
    for entry in jobs:
        name,script,target_name,prefix,*optional=entry
        arguments=optional[0] if optional else []
        if args.package=='G10_UI' and name=='approval-ui':arguments=['--synthetic-demo-acceptance']
        local_controls=args.package=='G10_UI' and name=='controls-bot-boundary'
        if local_controls:arguments=['--controls','--with-ui','--controls-report-local','--output-dir',str(OUT/'controls-browser')]
        row=dict(name=name,script=script,state='RUNNING',started_at=time.time(),script_sha256=hashlib.sha256((script_path(script)).read_bytes()).hexdigest())
        r['checks']=[c for c in r['checks'] if c['name']!=name]+[row];r['passed']=False
        path.write_text(json.dumps(r,indent=2),encoding='utf-8')
        target=OUT/'controls-browser/controls.json' if local_controls else ROOT/'reports'/target_name
        def outputs():
            for item in (ROOT/'reports').glob(prefix+'*'):
                if item.is_file():yield item
                elif item.is_dir():yield from (f for f in item.rglob('*') if f.is_file())
        before={f:(f.read_bytes(),f.stat().st_mtime_ns) for f in outputs()}
        old_stamp=target.stat().st_mtime_ns if target.exists() else None
        with (OUT/(name+'.stdout.log')).open('w',encoding='utf-8') as log:
            try:
                command=([str(ROOT/'frontend/node_modules/.bin/tsx.cmd'),str(script_path(script))] if script.endswith('.mts') else [sys.executable,str(script_path(script))])+arguments
                # Invoke Node directly so cmd.exe is not part of test execution.
                if script.endswith('.mts'):command=['node',str(ROOT/'frontend/node_modules/tsx/dist/cli.mjs'),str(script_path(script))]+arguments
                if args.package=='G10_UI' and script.endswith('.mts'):command=[sys.executable,str(ROOT/'scripts/chart/run_isolated_browser.py'),script]+arguments
                completed=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                    timeout=420,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                row['exit_code']=completed.returncode
                fresh=target.exists() and target.stat().st_mtime_ns!=old_stamp
                if fresh:
                    body=json.loads(target.read_text(encoding='utf-8'));shutil.copy2(target,OUT/(name+'.json'))
                    row.update(result_file=name+'.json',passed=body.get('passed') is True,error=body.get('error'),checks=len(body.get('checks',[])))
                else:row.update(passed=False,error='Current result was not produced at the expected path; inspect stdout')
                row['state']='PASS' if row.get('passed') and completed.returncode==0 else 'FAIL'
                for f in outputs():
                    if f.is_file() and (f not in before or f.stat().st_mtime_ns!=before[f][1]):
                        shutil.copy2(f,OUT/(name+'-'+f.relative_to(ROOT/'reports').as_posix().replace('/','__')))
            except Exception as exc:row.update(state='FAIL',passed=False,error_type=type(exc).__name__)
            finally:
                for f,(data,stamp) in before.items():
                    if f.read_bytes()!=data:f.write_bytes(data)
                row['finished_at']=time.time();path.write_text(json.dumps(r,indent=2),encoding='utf-8')
        print(json.dumps(dict(check=name,state=row['state'],error=row.get('error')),ensure_ascii=True),flush=True)
        if row['state']=='FAIL':return 1
    required={j[0] for j in PACKAGES[args.package]}
    r['passed']={c['name'] for c in r['checks'] if c['state']=='PASS'}==required
    r['finished_at']=time.time();path.write_text(json.dumps(r,indent=2),encoding='utf-8')
    return 0 if (r['passed'] or args.only and all(c['state']=='PASS' for c in r['checks'] if c['name']==args.only)) else 1


if __name__=='__main__':raise SystemExit(main())
