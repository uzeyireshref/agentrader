import copy
from pathlib import Path
import tempfile
import unittest
from agentrader.drawings.service import DrawingService, DrawingError, DrawingLocked, geometry, management
from agentrader.drawings.calculations import query, canonical_hash, CalculationBlocked
from agentrader.drawings.contracts import capability, legacy_contract
from agentrader.migrations import migrate


def annotation(kind='note',text='İlk satır\nİkinci satır'):
    return dict(schema='chart-annotation/1',kind=kind,symbol='BTCUSDT',price_source='LAST_PRICE',label=kind,text='' if kind=='price_label' else text,anchors=[dict(time=1800000000,price='100.25')])


class AnnotationTests(unittest.TestCase):
    def test_plain_unicode_multiline_normalization_and_optional_price_caption(self):
        self.assertEqual(geometry(annotation(text='İlk\r\nİkinci\rÜçüncü'))['text'],'İlk\nİkinci\nÜçüncü')
        value=annotation(text='<script>alert(1)</script>\n😀 Bakı İstanbul')
        self.assertEqual(geometry(value)['text'],value['text'])
        self.assertEqual(geometry(annotation('price_label'))['text'],'')

    def test_strict_limits_controls_schema_and_single_anchor(self):
        for text in ['', '   ', 'a\x00b','a\x1fb','a\n'*8,'x'*257]:
            with self.subTest(text=repr(text)),self.assertRaises(DrawingError):geometry(annotation(text=text))
        for value in [dict(annotation(),schema='wrong'),dict(annotation(),extra=True),dict(annotation(),anchors=[]),dict(annotation('price_label'),text='a\nb'),dict(annotation('price_label'),text='x'*81)]:
            with self.assertRaises(DrawingError):geometry(value)

    def test_annotations_are_readable_editable_but_never_computable(self):
        for kind in ['text','note','price_label']:
            tool=capability('annotation',kind)
            self.assertTrue(tool['readable']);self.assertTrue(tool['editable']);self.assertFalse(tool['computable'])
            self.assertEqual(tool['canonical_queries'],[]);self.assertEqual(tool['calculation_state'],'DISPLAY_ONLY')
            self.assertFalse(tool['tracking_activation']);self.assertFalse(tool['order_authority'])
            with self.assertRaises(CalculationBlocked) as e:query(annotation(kind),'priceAt',time=1800000000)
            self.assertEqual(e.exception.code,'DISPLAY_ONLY_ANNOTATION')
            with self.assertRaises(CalculationBlocked):canonical_hash(annotation(kind))

    def test_text_revision_restart_inverse_and_duplicate_keep_plain_body(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'app.db';migrate(db);s=DrawingService(db,'owner');old=s.create('main','create',annotation())
            changed={**old['geometry'],'text':'Yeni not\nTam metin'};edited=s.update(old['drawing_id'],'edit',1,changed)
            restored=s.operations('main','undo',[dict(drawing_id=old['drawing_id'],expected_revision=2,geometry=old['geometry'],management=management(),deleted=False)])['drawings'][0]
            self.assertEqual(restored['geometry'],old['geometry'])
            copied=s.operations('main','copy',[dict(drawing_id=None,expected_revision=0,geometry=changed,management=management(),deleted=False)])['drawings'][0]
            self.assertNotEqual(copied['drawing_id'],old['drawing_id'])
            self.assertEqual(DrawingService(db,'owner').show(copied['drawing_id'])['geometry']['text'],changed['text'])
            self.assertEqual(copied['tracking'],'NOT_IMPLEMENTED')

    def test_lock_protects_body_price_and_delete_while_hide_is_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'app.db';migrate(db);s=DrawingService(db,'owner');a=s.create('main','new',annotation())
            locked=s.operations('main','lock',[dict(drawing_id=a['drawing_id'],expected_revision=1,geometry=a['geometry'],management=management()|dict(locked=True),deleted=False)])['drawings'][0]
            with self.assertRaises(DrawingLocked):s.update(a['drawing_id'],'body',2,{**a['geometry'],'text':'changed'})
            with self.assertRaises(DrawingLocked):s.update(a['drawing_id'],'delete',2,deleted=True)
            c=legacy_contract(locked);self.assertEqual(c['market']['interval_state'],'NOT_BOUND_TO_INTERVAL');self.assertEqual(c['category'],'annotation');self.assertEqual(c['time_scope']['mode'],'ANCHOR_POINT');self.assertEqual(c['params']['bot_use'],'DISPLAY_ONLY')

    def test_text_and_note_store_full_body_even_if_renderer_must_truncate(self):
        text='\n'.join('Long Unicode Bakı İstanbul '+str(i)+' '+('a'*80) for i in range(8))
        self.assertEqual(geometry(annotation(text=text))['text'],text)

    def test_v8_read_write_delete_and_batch_isolation(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)
            with TestClient(create_app(WebSettings(f/'app.db',f/'exec.db',market_database=f/'market.db')),base_url='http://127.0.0.1') as c:
                body=dict(request_id='new',geometry=annotation());self.assertEqual(c.post('/api/workspaces/main/drawings?format_version=7',json=body).status_code,422)
                r=c.post('/api/workspaces/main/drawings?format_version=8',json=body);self.assertEqual(r.status_code,201);a=r.json();path='/api/drawings/'+a['drawing_id']
                for version in range(1,8):
                    suffix='?format_version='+str(version);self.assertEqual(c.get('/api/workspaces/main/drawings'+suffix).json()['drawings'],[]);self.assertEqual(c.get(path+suffix).status_code,422)
                self.assertEqual(c.patch(path+'?format_version=7',json=dict(request_id='old-edit',expected_revision=1,geometry=annotation())).status_code,422)
                self.assertEqual(c.request('DELETE',path+'?format_version=7',json=dict(request_id='old-delete',expected_revision=1)).status_code,422)
                op=dict(drawing_id=a['drawing_id'],expected_revision=1,geometry=a['geometry'],management=a['management'],deleted=False)
                self.assertEqual(c.post('/api/workspaces/main/drawing-operations?format_version=7',json=dict(request_id='old-batch',operations=[op])).status_code,422)
                self.assertEqual(c.post('/api/workspaces/main/drawing-operations?format_version=8',json=dict(request_id='new-batch',operations=[op])).status_code,200)
