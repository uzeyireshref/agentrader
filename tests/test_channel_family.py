import copy
from pathlib import Path
import tempfile
import unittest

from agentrader.drawings.service import DrawingService, DrawingError, geometry, management
from agentrader.drawings.channel_family import KINDS
from agentrader.drawings.calculations import canonical_hash, query, CalculationBlocked
from agentrader.drawings.contracts import legacy_contract, capability
from agentrader.migrations import migrate


def family(kind='pitchfork'):
    anchors=[dict(time=1800000000,price='100'),dict(time=1800009000,price='140'),dict(time=1800009000,price='120')]
    return dict(schema='chart-channel-family/1',kind=kind,symbol='BTCUSDT',price_source='LAST_PRICE',label=kind,
                anchors=anchors[:2] if kind=='regression_channel' else anchors,text='Birinci satır\nİkinci satır',
                options=dict(extend='right' if 'pitchfork' in kind else 'none',median=True,background=True,fill_opacity=.2,
                             prices=False,levels=['0.5','1'],source='close',upper_deviation='2',lower_deviation='2',
                             upper_enabled=True,lower_enabled=True,pearson=False))


class ChannelFamilyTests(unittest.TestCase):
    def test_all_kinds_persist_options_text_and_inverse_revision_after_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'app.db';migrate(path);service=DrawingService(path,'owner')
            for index,kind in enumerate(KINDS):
                original=family(kind);made=service.create('main','new-'+str(index),original)
                changed=copy.deepcopy(made['geometry']);changed['options']['extend']='both';changed['text']='Yeni not'
                updated=service.update(made['drawing_id'],'change-'+str(index),1,changed)
                self.assertEqual(DrawingService(path,'owner').show(made['drawing_id'])['geometry'],changed)
                restored=service.operations('main','undo-'+str(index),[dict(drawing_id=made['drawing_id'],expected_revision=updated['revision'],geometry=original,management=management(),deleted=False)])['drawings'][0]
                self.assertEqual(restored['geometry'],original)

    def test_family_geometry_does_not_inherit_legacy_parallel_calculation_authority(self):
        for kind in KINDS:
            value=family(kind)
            with self.assertRaises(CalculationBlocked) as error:canonical_hash(value)
            self.assertEqual(error.exception.code,'DISPLAY_ONLY_CHANNEL_FAMILY')
            with self.assertRaises(CalculationBlocked):query(value,'boundsAt',time=1800000000)
            contract=legacy_contract(dict(geometry=value,drawing_id='test',revision=1,workspace_id='main',deleted=False,management=management()))
            self.assertFalse(contract['capabilities']['computable']);self.assertEqual(contract['capabilities']['canonical_queries'],[])
            self.assertIsNone(contract['capabilities']['binding_model'])
            if kind!='parallel_channel':self.assertTrue(capability('drawing',kind)['readable'])

    def test_strict_schema_types_nonfinite_levels_and_text(self):
        for change in [dict(schema='wrong'),dict(text='x\n'*8),dict(text='<b>literal</b>\x00'),dict(extra=True)]:
            with self.assertRaises(DrawingError):geometry({**family(),**change})
        for patch in [dict(fill_opacity=float('nan')),dict(fill_opacity=True),dict(levels=['1','1.0']),dict(levels=['0']),dict(upper_deviation='-2'),dict(median=1),dict(source='typo')]:
            value=family();value['options'].update(patch)
            with self.assertRaises(DrawingError):geometry(value)

    def test_degenerate_anchors_fail_but_flat_regression_and_vertical_pitchfork_are_valid(self):
        value=family();value['anchors'][1]['time']=value['anchors'][0]['time']
        with self.assertRaises(DrawingError):geometry(value)
        value=family();value['anchors'][2]=copy.deepcopy(value['anchors'][1])
        with self.assertRaises(DrawingError):geometry(value)
        value=family('regression_channel');value['anchors'][0]['price']=value['anchors'][1]['price']='100';geometry(value)
        value=family();value['anchors'][0]['time']=1800009000;value['anchors'][1]['time']=1800000000;value['anchors'][2]['time']=1800018000;geometry(value)
        for kind in ('flat_channel','disjoint_channel'):
            value=family(kind);value['anchors'][2]=copy.deepcopy(value['anchors'][1]);geometry(value)

    def test_family_binding_is_rejected_before_traceability_or_activation(self):
        from agentrader.chart_bindings import BindingService, BindingBlocked
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'app.db';migrate(path);made=DrawingService(path,'owner').create('main','new',family())
            with self.assertRaises(BindingBlocked) as error:
                BindingService(path,'owner').save_binding('main','b','request',0,dict(type='drawing',object_id=made['drawing_id'],revision=1),'BTCUSDT','15m','LINEAR',[1800000000+i*900 for i in range(30)],None,dict(operation='boundsAt',output='middle',ratio=None),dict(schema='chart-rule-definition/1',kind='touch',direction='ANY',tolerance='0',closed_candle=True,rearm_policy='EXPLICIT'))
            self.assertEqual(error.exception.code,'DISPLAY_ONLY_CHANNEL_FAMILY')

    def test_v9_isolates_all_old_read_write_delete_and_operation_paths(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)
            with TestClient(create_app(WebSettings(f/'app.db',f/'exec.db',market_database=f/'market.db')),base_url='http://127.0.0.1') as client:
                payload=dict(request_id='new',geometry=family())
                self.assertEqual(client.post('/api/workspaces/main/drawings?format_version=8',json=payload).status_code,422)
                response=client.post('/api/workspaces/main/drawings?format_version=9',json=payload);self.assertEqual(response.status_code,201,response.text)
                made=response.json();path='/api/drawings/'+made['drawing_id']
                self.assertEqual(len(client.get('/api/workspaces/main/drawings?format_version=9').json()['drawings']),1)
                for version in range(1,9):
                    suffix='?format_version='+str(version)
                    self.assertEqual(client.get('/api/workspaces/main/drawings'+suffix).json()['drawings'],[])
                    self.assertEqual(client.get(path+suffix).status_code,422)
                self.assertEqual(client.patch(path+'?format_version=8',json=dict(request_id='old',expected_revision=1,geometry=family())).status_code,422)
                self.assertEqual(client.request('DELETE',path+'?format_version=8',json=dict(request_id='old',expected_revision=1)).status_code,422)
                op=dict(drawing_id=made['drawing_id'],expected_revision=1,geometry=made['geometry'],management=made['management'],deleted=False)
                self.assertEqual(client.post('/api/workspaces/main/drawing-operations?format_version=8',json=dict(request_id='old-op',operations=[op])).status_code,422)
                legacy=dict(kind='horizontal',symbol='BTCUSDT',price_source='LAST_PRICE',label='old writer',anchors=[dict(time=1800000000,price='100')])
                downgrade={**op,'geometry':legacy}
                self.assertEqual(client.post('/api/workspaces/main/drawing-operations?format_version=8',json=dict(request_id='downgrade',operations=[downgrade])).status_code,422)
                result=client.post('/api/workspaces/main/drawing-operations?format_version=9',json=dict(request_id='new-op',operations=[op]));self.assertEqual(result.status_code,200,result.text)


class FamilyLineStyleTests(unittest.TestCase):
    def test_individual_line_styles_persist_and_invalid_styles_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'app.db';migrate(path);service=DrawingService(path,'owner')
            g=family();g['options']['line_styles']={'level:0.5':dict(color='#aabbcc',width=4,style='dashed'),'level:-0.5':dict(color='#bbccdd',width=2,style='dotted')}
            made=service.create('main','styles',g)
            self.assertEqual(DrawingService(path,'owner').show(made['drawing_id'])['geometry']['options']['line_styles'],g['options']['line_styles'])
            for bad in ({'x':dict(color='#aabbcc',width=1,style='solid')},{'median':dict(color='url(x)',width=1,style='solid')},{'median':dict(color='#aabbcc',width=True,style='solid')},{'median':dict(color='#aabbcc',width=1,style='other')}):
                g['options']['line_styles']=bad
                with self.assertRaises(DrawingError):geometry(g)
