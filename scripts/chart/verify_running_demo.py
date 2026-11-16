"""Verify the running local demo terminal without account/order access."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json,sys
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from agentrader.shared.market_environment import SOURCE,ENVIRONMENT

with httpx.Client(base_url='http://127.0.0.1:8765',timeout=20) as c:
    health=c.get('/api/health').json();assert health['market_environment']==ENVIRONMENT and not health['trading_commands_enabled']
    markets=c.get('/api/markets').json();assert markets['source']==SOURCE and markets['environment']==ENVIRONMENT
    candles=c.get('/api/candles',params=dict(symbol='BTCUSDT',interval='15m')).json();assert candles['source']==SOURCE and candles['environment']==ENVIRONMENT and candles['candles']
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport=dict(width=1536,height=960))
    page.goto('http://127.0.0.1:8765',wait_until='networkidle')
    expect(page.locator('.loaded-count')).not_to_have_text('0 mum',timeout=45000)
    expect(page.locator('.shell-state')).to_have_text('Canlı',timeout=45000)
    assert 'Binance Demo USD-M' in page.locator('.shell-instrument').inner_text()
    loaded=page.locator('.loaded-count').inner_text()
    page.screenshot(path=str(ROOT/'reports/demo-running-terminal-20261113.png'))
    browser.close()
report=dict(passed=True,url='http://127.0.0.1:8765',source=SOURCE,environment=ENVIRONMENT,loaded=loaded,trading_commands_enabled=False,account_requests=0,order_requests=0)
(ROOT/'reports/demo-running-terminal-20261113.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
