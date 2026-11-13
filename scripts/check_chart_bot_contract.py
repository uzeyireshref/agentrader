"""E3 contract/wire compatibility examples; not a bot adapter or decision engine."""
import hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from agentrader.chart_market import ChartMarket
from agentrader.market_feed import FeedState
from agentrader.application.service import ApplicationService
from agentrader.application.settings import WebSettings
from agentrader.drawings.service import DrawingService


def main(report_name='chart-bot-contract-validation-20261110.json'):
    spec_path=ROOT/'docs/chart/contracts/chart-bot-input-v1.json';spec=json.loads(spec_path.read_text(encoding='utf-8'))
    result={'date':'2026-11-10','task':'E3','passed':False,'checks':[],'contract':'docs/chart/contracts/chart-bot-input-v1.json','contract_sha256':hashlib.sha256(spec_path.read_bytes()).hexdigest(),'production_changed':False,'bot_connected':False,'full_chart_acceptance':False,'example_scope':'Production models with local fake public market; no network/user stores. This validates wire descriptions, not proposed runtime rules.'}
    def check(name,value):
        result['checks'].append({'name':name,'passed':bool(value)})
        if not value:raise AssertionError(name)
    try:
        start=1800000000000;step=900000;clock=[start/1000+2]
        def row(t):return [t,'100','110','90','105','10',t+step-1,'1050',5,'5','525','0']
        class Client:
            def get(self,path,params=None):
                if path.endswith('exchangeInfo'):return {'symbols':[{'symbol':'BTCUSDT','status':'TRADING','contractType':'PERPETUAL','baseAsset':'BTC','quoteAsset':'USDT','filters':[{'filterType':'PRICE_FILTER','tickSize':'0.1'}]}]}
                if path.endswith('/time'):return {'serverTime':start+2000}
                return [row(start-step),row(start)]
        with tempfile.TemporaryDirectory(prefix='agentrader-e3-') as folder:
            folder=Path(folder);settings=WebSettings(folder/'app.db',folder/'execution.db',market_database=folder/'market.db');ApplicationService(settings).initialize()
            market=ChartMarket(settings.market_database,client_factory=Client,clock=lambda:clock[0]);history=market.history('BTCUSDT','15m',limit=2)
            feed=FeedState('BTCUSDT','15m',clock=lambda:clock[0]);feed.seed(history);snapshot=feed.packet(-1)
            def event(t,stamp,closed,volume):return {'e':'kline','E':stamp,'s':'BTCUSDT','k':{'s':'BTCUSDT','i':'15m','t':t,'T':t+step-1,'x':closed,'o':'100','h':'110','l':'90','c':'105','v':volume,'q':str(float(volume)*105),'n':6,'V':str(float(volume)/2),'Q':str(float(volume)*52.5)}}
            clock[0]=(start+3000)/1000;feed.apply(event(start,start+3000,False,'11'));update=feed.packet(snapshot['generation'])
            check('actual_packet_common_fields',all(set(spec['current_wire']['packet_common_required'])<=set(p) for p in [snapshot,update]))
            check('actual_snapshot_and_update_shapes',snapshot['type']=='snapshot' and 'candles' in snapshot and update['type']=='update' and all(k in update for k in spec['current_wire']['update_payload']))
            check('actual_market_identity',all(snapshot[k]==spec['market_identity'][k] for k in ['source','environment','product','price_type']))
            check('actual_candle_fields_and_time_units',all(set(spec['current_wire']['candle_required'])<=set(c) and set(c)<=set(spec['current_wire']['candle_required']+spec['current_wire'].get('candle_optional',[])) and c['close_time']==c['time']*1000+step-1 for c in snapshot['candles']))
            check('wire_price_is_number_not_exact_decimal_text',isinstance(update['candle']['close'],float) and isinstance(update['market']['tick_size'],str))
            check('exact_sidecar_text_round_trip',update['candle']['exact']['close']=='105' and update['candle']['exact']['state']=='VERIFIED')
            check('precision_is_not_bot_authority',update['precision']['state']=='VERIFIED' and update['precision']['bot_eligible'] is False)
            check('equal_sequence_heartbeat_keeps_data_receipt_time',feed.packet(snapshot['generation'])['sequence']==update['sequence'] and feed.packet(snapshot['generation'])['received_at']==update['received_at'])
            clock[0]=(start+step)/1000;feed.apply(event(start,start+step,True,'12'));closed=feed.packet(snapshot['generation'])
            clock[0]=(start+step+2000)/1000;feed.apply(event(start+step,start+step+2000,False,'1'));after=feed.packet(snapshot['generation'])
            check('close_metadata_repeats_on_later_bar',closed['close_event']==after['close_event'] and closed['close_event']['time']==start//1000 and closed['close_event']['event_time']==start+step)
            check('closed_keys_are_bounded_not_durable',feed.closed_keys.maxlen==1000 and FeedState('BTCUSDT','15m').generation==0)
            service=DrawingService(settings.application_database,'local:contract',clock=lambda:clock[0]);views=[]
            for kind in spec['current_wire']['geometry_kinds']:
                anchors=[{'time':start//1000,'price':'100.1'}]
                if kind!='horizontal':anchors.append({'time':(start+step)//1000,'price':'105.2'})
                if kind=='fibonacci':anchors.reverse()
                value={'kind':kind,'symbol':'BTCUSDT','price_source':'LAST_PRICE','anchors':anchors,'label':'contract '+kind}
                view=service.create('main','contract_'+kind,value);views.append(view)
                check('saved_geometry_'+kind,set(spec['current_wire']['geometry_fields'])==set(view['geometry']) and view['geometry']['anchors']==anchors)
            check('actual_drawing_envelope_and_no_interval',all(set(spec['current_wire']['drawing_required'])<=set(v) and 'interval' not in v['geometry'] and v['tracking']=='NOT_IMPLEMENTED' for v in views))
            old=views[0];changed=service.update(old['drawing_id'],'change',old['revision'],dict(old['geometry'],label='renamed'))
            undone=service.update(old['drawing_id'],'undo',changed['revision'],old['geometry'])
            deleted=service.update(old['drawing_id'],'delete',undone['revision'],deleted=True)
            check('same_geometry_undo_has_new_revision',undone['geometry']==old['geometry'] and undone['revision']==3)
            check('deleted_head_visible_but_excluded_from_list',service.show(old['drawing_id'])['deleted'] and len(service.list('main','BTCUSDT'))==3)
            check('draft_has_no_activation_or_execution_authority',spec['status']=='DESIGN_ONLY_NOT_IMPLEMENTED' and not spec['production_adapter_implemented'] and not spec['runtime_activation_authorized'] and not spec['execution_authority'])
            check('planned_readiness_requires_all_proofs',spec['eligibility_constraints']['all_future_capabilities_required'] and len(spec['future_required_capabilities'])==8 and 'CLOCK_UNTRUSTED' in spec['blocked_reasons'])
            check('semantic_identity_excludes_feed_counters',all(k not in spec['event_identity_template'] for k in ['packet_sequence','packet_generation']) and 'drawing_revision' in spec['event_identity_template'])
            check('no_execution_database_created',not settings.execution_database.exists())
            result['current_wire_examples']={'snapshot':snapshot,'update':update,'closed':closed,'after_close':after,'drawing':old,'new_revision_same_geometry':undone,'deleted_head':deleted}
        result['passed']=True;result['next_task']='E4'
    except Exception as error:result['error']=str(error)
    (ROOT/'reports'/report_name).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'checks':len(result['checks']),'error':result.get('error')},ensure_ascii=True))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
