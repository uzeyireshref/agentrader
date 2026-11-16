"""G4 independent shared vectors, real-bar selection and archived REA parity."""
import copy
from fractions import Fraction
import json
import math
from pathlib import Path
import unittest

from agentrader.chart.drawings.calculations import query, canonical_hash, CalculationBlocked
from scripts.integration.chart_tool_matrix_cases import candles

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT/'frontend/tests/fixtures/channel-family-g4.json').read_text())


def geometry(kind):
    return dict(schema='chart-channel-family/1',kind=kind,symbol='BTCUSDT',price_source='LAST_PRICE',
                label='Synthetic G4',text='Ham çapa korunur',anchors=copy.deepcopy(FIXTURE['anchors'][:2] if kind=='regression_channel' else FIXTURE['anchors']),
                options=copy.deepcopy(FIXTURE['options']))


def numeric(value):
    return Fraction(int(value['numerator']),int(value['denominator'])) if 'numerator' in value else float(value['decimal'])


class FamilyMathTests(unittest.TestCase):
    def setUp(self):
        self.rows=candles(40)
        self.times=[r['time'] for r in self.rows]

    def call(self,g,op='boundsAt',**kw):
        return query(g,op,times=self.times,rows=self.rows,interval='15m',**kw)

    def test_seven_independent_linear_bounds_midlines_levels_distances_and_slopes(self):
        for case in FIXTURE['cases']:
            with self.subTest(kind=case['kind']):
                g=geometry(case['kind']);stamp=self.times[25]
                original=copy.deepcopy(g)
                result=self.call(g,time=stamp)['value']
                for key in ('lower','upper','middle'):
                    self.assertEqual(numeric(result[key]),Fraction(case['expected'][key]))
                self.assertEqual(numeric(result['width']),Fraction(case['expected']['upper'])-Fraction(case['expected']['lower']))
                self.assertEqual(numeric(self.call(g,'priceAt',time=stamp)['value']),Fraction(case['expected']['middle']))
                self.assertTrue(self.call(g,'contains',time=stamp,query_price=case['expected']['middle'] if '/' not in case['expected']['middle'] else str(float(Fraction(case['expected']['middle']))))['value'])
                self.assertEqual(numeric(self.call(g,'distance',time=stamp,query_price='300')['value']),300-Fraction(case['expected']['upper']))
                self.assertTrue(self.call(g,'slope')['value']['lines'])
                self.assertEqual(g,original)
                if 'pitchfork' in g['kind']:
                    self.assertEqual(numeric(self.call(g,'level',time=stamp,ratio='0')['value']),Fraction(case['expected']['middle']))
                    self.call(g,'level',time=stamp,ratio='-1')

    def test_log_models_match_archived_native_pixel_vectors(self):
        micro=geometry('disjoint_channel')
        for anchor in micro['anchors']:
            anchor['price']=str(float(anchor['price'])*1e-8)
        model=self.call(micro,'geometry',scale='LOG')['value']
        self.assertTrue(math.isclose(float(numeric(model['handles'][3]['price'])),1.68e-6,rel_tol=1e-10,abs_tol=1e-18))
        for filename in ('pitchfork-render-rea-20261113.json','channel-render-rea-20261113.json'):
            for c in json.loads((ROOT/'frontend/tests/fixtures'/filename).read_text()):
                times=c['times'];delta=times[1]-times[0]
                # Archived display times can be nonuniform. Preserve observed logical positions
                # on an explicit synthetic 15m grid; no market rows are fabricated at runtime.
                g=geometry(c['kind']);g['anchors']=[dict(time=self.times[0]+p['index']*900,price=str(p['price'])) for p in c['points']]
                g['options']['extend']='right' if 'pitchfork' in c['kind'] else 'none'
                g['options']['median']=c['kind'] not in ('flat_channel','disjoint_channel')
                result=self.call(g,'geometry',scale='LOG' if c['log'] else 'LINEAR')['value']
                a,b=c['points'][:2];sa,sb=c['screenAnchors'][:2];transform=math.log if c['log'] else lambda p:p
                pa,pb=transform(a['price']),transform(b['price'])
                def project(point):
                    x=float(numeric(point['logical']));price=float(numeric(point['price']))
                    return dict(x=sa['x']+(x-a['index'])*(sb['x']-sa['x'])/(b['index']-a['index']),
                                y=sa['y']+(transform(price)-pa)*(sb['y']-sa['y'])/(pb-pa))
                near=lambda p,q:math.hypot(p['x']-q['x'],p['y']-q['y'])<.001
                for line in result['lines']:
                    if not line['visible']: continue
                    p,q=project(line['a']),project(line['b'])
                    self.assertTrue(any(near(p,v['points'][0]) and near(q,v['points'][1]) or near(q,v['points'][0]) and near(p,v['points'][1]) for v in c['lines']), (c['kind'],c['log'],line['role']))

    def regression(self):
        rows=self.rows[:3]
        for i,r in enumerate(rows):
            r.update(open=100+i,high=105+i,low=95+i,close=FIXTURE['regression']['close'][i])
        self.rows=rows;self.times=[r['time'] for r in rows]
        g=geometry('regression_channel')
        g['anchors']=[dict(time=t,price='999') for t in FIXTURE['regression']['raw_times']]
        return g

    def test_regression_intermediate_utc_uses_real_containing_bars_and_preserves_raw_anchors(self):
        g=self.regression();before=copy.deepcopy(g)
        result=self.call(g,time=g['anchors'][1]['time'])
        self.assertAlmostEqual(numeric(result['value']['middle']),float(Fraction('308/3')))
        info=result['regression']
        self.assertEqual(info['effective_anchor_times'],FIXTURE['regression']['effective_times'])
        self.assertEqual(info['sample_count'],3)
        self.assertAlmostEqual(numeric(info['deviation'])**2,4/3)
        self.assertAlmostEqual(numeric(info['pearson']),FIXTURE['regression']['pearson'])
        self.assertEqual(g,before)
        self.assertEqual(self.call(g,scale='LOG',time=self.times[1])['value'],self.call(g,time=self.times[1])['value'])
        reverse={**g,'anchors':list(reversed(g['anchors']))}
        self.assertEqual(self.call(reverse,time=self.times[1])['value'],self.call(g,time=self.times[1])['value'])

    def test_same_bar_gap_future_missing_and_boundary_have_explicit_results(self):
        g=self.regression()
        same={**g,'anchors':[g['anchors'][0],dict(time=self.times[0]+450,price='5')]}
        with self.assertRaisesRegex(CalculationBlocked,'INSUFFICIENT_REGRESSION_SAMPLES'):self.call(same,time=self.times[0])
        same['anchors'][1]['time']=same['anchors'][0]['time']
        with self.assertRaisesRegex(CalculationBlocked,'INSUFFICIENT_REGRESSION_SAMPLES'):self.call(same,time=self.times[0])
        future={**g,'anchors':[g['anchors'][0],dict(time=self.times[-1]+900,price='5')]}
        with self.assertRaisesRegex(CalculationBlocked,'REGRESSION_HISTORY_REQUIRED'):self.call(future,time=self.times[0])
        self.rows.pop(1);self.times.pop(1)
        with self.assertRaisesRegex(CalculationBlocked,'GRID_GAP'):self.call(g,time=self.times[0])
        self.setUp();g=self.regression();g['anchors'][1]['time']=self.times[1]
        self.assertEqual(self.call(g,time=self.times[1])['regression']['effective_anchor_times'][1],self.times[1])
        self.assertEqual(self.call(g,time=self.times[1])['regression']['sample_count'],2)

    def test_disabled_deviation_uses_extrema_and_vertical_pitchfork_is_not_a_fake_price(self):
        g=self.regression();g['options'].update(upper_enabled=False,lower_enabled=False)
        bounds=self.call(g,time=self.times[0])['value']
        self.assertAlmostEqual(numeric(bounds['upper']),105)
        self.assertAlmostEqual(numeric(bounds['lower']),95)
        g=geometry('pitchfork');g['anchors'][0]['time']=self.times[1];g['anchors'][1]['time']=self.times[0];g['anchors'][2]['time']=self.times[2]
        self.call(g,'geometry')
        with self.assertRaisesRegex(CalculationBlocked,'VERTICAL_GEOMETRY'):self.call(g,time=self.times[1])

    def test_family_semantic_hash_binds_scale_and_selected_regression_data_not_text(self):
        g=geometry('disjoint_channel')
        fingerprint=canonical_hash(g,times=self.times,interval='15m')
        self.assertEqual(fingerprint,canonical_hash({**g,'label':'renamed','text':'new note'},times=self.times,interval='15m'))
        self.assertNotEqual(fingerprint,canonical_hash(g,times=self.times,interval='15m',scale='LOG'))
        g=self.regression()
        before=canonical_hash(g,times=self.times,rows=self.rows,interval='15m')
        self.rows[1]['close']+=.25
        self.assertNotEqual(before,canonical_hash(g,times=self.times,rows=self.rows,interval='15m'))
