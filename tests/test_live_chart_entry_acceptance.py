import time
import unittest
from scripts.integration.run_live_chart_entry_acceptance import calibration_geometry,preview_inputs,start_preview_server,chart_session
from agentrader.bot.risk import RiskLimits
from agentrader.bot.v2_preflight import prepare_single
from scripts.bot.run_bounded_demo_acceptance import make_plan
from test_v2_preflight import snapshot


class LiveChartEntryAcceptanceTests(unittest.TestCase):
    def test_legacy_closed_sessions_do_not_break_chart_entry_observation(self):
        own=dict(engine='v2',active=False,plan=dict(plan_id='owned'))
        sessions=[dict(active=False,plan=dict(symbol='BTCUSDT')),dict(engine='grid-v2',plan=dict(plan_id='owned')),own]
        self.assertIs(chart_session(sessions,'owned'),own)
        with self.assertRaises(ValueError):chart_session(sessions,'missing')
        with self.assertRaises(ValueError):chart_session(sessions+[own],'owned')

    def test_calibration_uses_only_latest_closed_price_and_native_tick(self):
        c=dict(market=dict(tick_size='.10'),rows=[dict(time=900,closed=True,exact=dict(close='100')),dict(time=960,closed=True,exact=dict(close='101')),dict(time=1020,closed=False,exact=dict(close='999'))])
        g=calibration_geometry(c,'fixture')
        self.assertEqual(g['anchors'],[dict(time=900,price='101.10')]);self.assertIn('fixture',g['label'])
        self.assertEqual(g['price_source'],'LAST_PRICE')

    def test_no_closed_reference_cannot_create_a_calibration_drawing(self):
        with self.assertRaises(ValueError):calibration_geometry(dict(rows=[]),'fixture')

    def test_explicit_small_preview_inputs_still_pass_real_plan_risk_checks(self):
        s=snapshot();s['observed_at']=time.time()
        inputs=preview_inputs(s,'fixture');plan=make_plan(s,'LONG','LIMIT','fixture')
        self.assertEqual(inputs['entry_price'],plan['entry']['trigger_price'])
        self.assertEqual(inputs['ttl_seconds'],300)
        self.assertEqual(prepare_single(plan,s,RiskLimits())['state'],'READY')

    def test_temporary_preview_server_has_no_mutation_route_and_checks_host(self):
        import socket
        import httpx
        from unittest.mock import Mock
        p=Mock();p.show.return_value=dict(state='PREVIEW_ONLY')
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server,thread=start_preview_server(p,port)
        try:
            until=time.time()+5
            while not server.started and time.time()<until:time.sleep(.01)
            url=f'http://127.0.0.1:{port}/api/workspaces/main/shadow-events/event/preview?version=1'
            with httpx.Client(trust_env=False) as client:
                self.assertEqual(client.get(url).status_code,200)
                self.assertEqual(client.post(url).status_code,405)
                self.assertEqual(client.get(url,headers={'Host':'evil.invalid'}).status_code,403)
                self.assertEqual(client.get(url,headers={'Origin':'https://evil.invalid'}).status_code,403)
            p.show.assert_called_once_with('main','event',1)
        finally:server.should_exit=True;thread.join(timeout=5)
