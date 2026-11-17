"""Launch local terminal processes with allowlisted web settings from .env.

Exchange credentials remain handled exclusively by worker Config.load().
This launcher never enables execution.
"""
import os
from pathlib import Path
import secrets
import sys

ROOT=Path(__file__).resolve().parents[2]


def prepare():
    os.chdir(ROOT)
    path=ROOT/'.env'
    lines=path.read_text(encoding='utf-8-sig').splitlines() if path.exists() else []
    values={}
    for line in lines:
        if line.strip() and not line.lstrip().startswith('#'):
            key,sep,value=line.partition('=')
            if sep:values[key.strip()]=value.strip().strip('\"\'')
    defaults={'AGENTRADER_WEB_TOKEN':secrets.token_urlsafe(36),
              'AGENTRADER_LOCAL_AUTO_LOGIN':'1',
              'AGENTRADER_BOT_ENABLED':'1',
              'AGENTRADER_EXECUTION_DATABASE':'data/execution-demo-web.sqlite3',
              'AGENTRADER_BOT_RISK_PROFILE':'risk-demo.json'}
    for key,value in defaults.items():
        if not values.get(key):
            lines=[line for line in lines if line.partition('=')[0].strip()!=key]
            lines.append(key+'='+value);values[key]=value
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    for key in ('AGENTRADER_WEB_TOKEN','AGENTRADER_LOCAL_AUTO_LOGIN','AGENTRADER_BOT_ENABLED','AGENTRADER_EXECUTION_DATABASE',
                'AGENTRADER_BOT_RISK_PROFILE','AGENTRADER_WEB_DATABASE','AGENTRADER_CHART_DATABASE'):
        if key in values:os.environ[key]=values[key]
    token_file=ROOT/'data/local-web-token.txt'
    token_file.parent.mkdir(exist_ok=True)
    token_file.write_text(os.environ['AGENTRADER_WEB_TOKEN'],encoding='utf-8')


if __name__=='__main__':
    prepare()
    from agentrader.cli.web_cli import main
    args=sys.argv[1:]
    if args not in (['serve'],['bot-worker']):raise SystemExit('Use serve or bot-worker (read-only).')
    raise SystemExit(main(args))
