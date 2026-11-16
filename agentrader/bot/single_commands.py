"""Generic command adapter for an already authorized, bounded SINGLE plan."""
import hashlib
from agentrader.bot.entry_options import validate_options
from agentrader.bot.plans import PlanService,digest,exact_fields
from agentrader.bot.risk import RiskLimits
from agentrader.shared.exchange import ExchangeError


def validate_reference(params):
    import re
    exact_fields(params,'plan_id version plan_digest entry_options','SINGLE komut bağlantısı')
    if (not isinstance(params['plan_id'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',params['plan_id']) or
            type(params['version']) is not int or params['version']<1 or
            not isinstance(params['plan_digest'],str) or not re.fullmatch('[a-f0-9]{64}',params['plan_digest'])):
        raise ValueError('SINGLE plan kimliği geçersiz.')
    validate_options(params['entry_options'])


def bound_plan(commands,request):
    p=request['parameters'];service=PlanService(commands.store,commands.owner)
    row=service.show(p['plan_id'],p['version']);plan=row['plan']
    if (row['digest']!=p['plan_digest'] or plan['symbol']!=request['scope']['symbol'] or
            plan['schema_version']!=2 or plan['execution']['strategy']!='SINGLE' or
            plan['entry'].get('order_options',{})!=p['entry_options']):
        raise ValueError('SINGLE komutu yetkili plan ve seçenekleriyle uyuşmuyor.')
    return service,row


def run(commands,body):
    from agentrader.bot.v2_runner import V2Runner
    p=body['request']['parameters']
    try:
        service,row=bound_plan(commands,body['request'])
        if row['state']!='AUTHORIZED':raise ValueError('SINGLE plan yetkili değil veya giriş hakkı kullanıldı.')
        V2Runner(service,commands.x,RiskLimits()).open(p['plan_id'],p['version'],execute=True)
    except (ValueError,ExchangeError):
        # The existing plan claim and order journal establish delivery evidence.
        # This adapter never retries the entry, cancels protection or frees risk.
        pass
    return reconcile(commands,body)


def reconcile(commands,body):
    _,row=bound_plan(commands,body['request']);p=body['request']['parameters']
    result={'plan_id':p['plan_id'],'version':p['version'],'plan_state':row['state'],
            'action_id':row['action_id'],'session_id':row['session_id'],'automatic_resend':False,
            'risk_profile':'DEFAULT_RISK_LIMITS','meaning':'DELEGATED_SINGLE; NOT_POSITION_CLOSED'}
    if row['action_id'] is None:
        state='NOT_SENT'
    else:
        expected_action='agt-'+hashlib.sha256(f"{p['plan_id']}:{p['version']}:entry".encode()).hexdigest()[:28]
        expected_session='v2-'+digest([p['plan_id'],p['version'],p['plan_digest']])[:28]
        if row['action_id']!=expected_action or row['session_id']!=expected_session:
            raise ValueError('SINGLE eylem/oturum kimliği uyuşmuyor.')
        intent=commands.store.intent(row['action_id'])
        result['entry_state']=intent['state'] if intent else 'NO_RECORDED_INTENT'
        projection=commands.store.db.execute('SELECT * FROM order_projection WHERE client_id=?',(row['action_id'],)).fetchone()
        if projection:
            from agentrader.bot.risk import number
            result.update(filled_quantity=projection['filled'],unfilled_quantity=str(number(projection['quantity'])-number(projection['filled'])))
            result['entry_outcome']=('NO_FILL' if number(projection['filled'])==0 and projection['status'] in ('EXPIRED','CANCELED','REJECTED') else
                                     'FILLED' if projection['status']=='FILLED' else 'PARTIAL_FILL' if number(projection['filled'])>0 else 'PENDING')
        reservation=commands.store.db.execute('SELECT * FROM risk_reservations WHERE reservation_id=?',(row['session_id'],)).fetchone()
        if reservation:
            import json
            from agentrader.bot.reservations import ReservationBook
            book=ReservationBook(commands.store,commands.account_ref)
            result['reservation_state']=book.state(row['session_id'])
            result['reserved_entry_quantity']=('0' if reservation['state']=='RELEASED' else
                str(book._effective_exposures(commands.store.db,reservation,json.loads(reservation['body']))[0].quantity))
        state='APPLIED' if row['state'] in ('MANAGING','CLOSED') else 'UNKNOWN'
    return commands._finish(body['command_id'],state,result)
