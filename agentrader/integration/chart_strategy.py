"""Closed-bar EMA20 drawing strategy over ChartBot only; no order/account capability."""
from decimal import Decimal
from fractions import Fraction
import json,os
from pathlib import Path
from agentrader.integration.chart_bot import BotError,canonical
from agentrader.shared.locking import execution_lock

VERSION='closed-ema20-horizontal/1'

class DrawingStrategy:
    def __init__(self,bot,state,*,symbol='BTCUSDT',interval='1m'):
        self.bot,self.path,self.symbol,self.interval=bot,Path(state).resolve(),symbol,interval
        if self.path==bot.journal.path:raise BotError('STRATEGY_STATE_MUST_BE_SEPARATE')
        self.identity=dict(version=VERSION,adapter_scope=bot.scope,symbol=symbol,interval=interval)

    def _load(self):
        if not self.path.exists():return dict(identity=self.identity,pending=None,latest=None)
        if self.path.stat().st_size>4*1024*1024:raise BotError('INVALID_STRATEGY_STATE')
        try:value=json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError,ValueError):raise BotError('INVALID_STRATEGY_STATE') from None
        if not isinstance(value,dict) or value.get('identity')!=self.identity or set(value)!={'identity','pending','latest'}:raise BotError('STRATEGY_STATE_SCOPE_MISMATCH')
        return value

    def _save(self,value):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.path.with_suffix(self.path.suffix+'.tmp')
        with temporary.open('w',encoding='utf-8') as stream:
            stream.write(canonical(value)+'\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,self.path)

    def _fresh(self):
        value=self.bot.snapshot(self.symbol,self.interval)
        ready=value['derived']['readiness']
        if (ready['state']!='READY' or ready.get('stale') or ready.get('open_candle_used')
                or ready.get('proof',{}).get('state')!='VERIFIED' or ready.get('source_clock',{}).get('state')!='FRESH'):
            return value,dict(state='PAUSED',reason=ready['state'],readiness=ready,order_authority=False)
        return value,None

    def step(self):
        # Separate strategy lock serializes durable intent and HTTP retries across processes.
        with execution_lock(self.path.with_suffix(self.path.suffix+'.lock')):
            state=self._load();context,paused=self._fresh()
            if paused:return paused
            ready=context['derived']['readiness'];bar=ready['last_closed_candle']
            if state['pending'] is None:
                if state['latest'] is not None and bar<=state['latest']['bar_time']:
                    return dict(state='NO_CHANGE',reason='CLOSED_BAR_ALREADY_PROCESSED',bar_time=bar,drawing_id=state['latest']['drawing_id'],order_authority=False)
                config=next(c for c in context['indicators']['indicators'] if c['indicator_id']=='ema-fast')
                if any(config.get(k)!=v for k,v in dict(kind='EMA',period=20,source='close',smoothing='EMA_SMA_SEED',calculation_version=1).items()):
                    raise BotError('STRATEGY_CONFIGURATION_CHANGED')
                response=self.bot.indicator_queries(self.symbol,self.interval,[dict(query_id='strategy-ema',indicator_id='ema-fast',expected_revision=config['revision'],operation='at',inputs=dict(time=bar))],context_id=context['context_id'])
                result=response['results'][0]
                if result['state']!='READY' or result['open_candle_used'] or result['effective_time']!=bar or result['consumed_data_hash']!=ready['consumed_data_hash']:
                    return dict(state='PAUSED',reason='INDICATOR_SOURCE_NOT_READY',order_authority=False)
                point=result['outputs']['value']['points'][0];price=point['value']['decimal']
                if point['time']!=bar or not Decimal(price).is_finite() or Decimal(price)<=0:raise BotError('INVALID_STRATEGY_PRICE')
                own=self.bot.get(state['latest']['drawing_id']) if state['latest'] else None
                if own and not self.bot._owned(own):raise BotError('BOT_OBJECT_PROTECTED')
                plan=dict(bar_time=bar,context_id=context['context_id'],source_readiness=ready,indicator=result,
                          geometry=dict(kind='horizontal',symbol=self.symbol,price_source='LAST_PRICE',label='Closed EMA20',anchors=[dict(time=bar,price=price)]),
                          target=own['drawing_id'] if own else None,expected_revision=own['revision'] if own else 0,note_revision=own['linked_note']['revision'] if own else 0)
                state['pending']=plan;self._save(state)
            plan=state['pending'];key=VERSION.replace('/','-')+'-'+self.symbol+'-'+self.interval+'-'+str(plan['bar_time'])
            _,paused=self._fresh()
            if paused:return paused
            if plan['target'] is None:item=self.bot.create(key+'-create',plan['geometry'])
            else:item=self.bot.update(key+'-update',plan['target'],plan['expected_revision'],plan['geometry'])
            _,paused=self._fresh()
            if paused:return paused
            note=canonical(dict(strategy=VERSION,reason='New closed candle: move horizontal level to closed-only EMA20; no trading decision',bar_time=plan['bar_time'],context_id=plan['context_id'],consumed_data_hash=plan['indicator']['consumed_data_hash'],calculation_input_hash=plan['indicator']['calculation_input_hash'],price=plan['geometry']['anchors'][0]['price']))
            self.bot.save_note(key+'-note',item['drawing_id'],plan['note_revision'],item['revision'],note)
            fresh,paused=self._fresh()
            if paused:return paused
            query=self.bot.calculate(item['drawing_id'],item['revision'],'priceAt',dict(time=plan['bar_time']),symbol=self.symbol,interval=self.interval,context_id=fresh['context_id'])['results'][0]
            if query['state']!='READY':return dict(state='PAUSED',reason=query['state'],order_authority=False)
            value=query['result']['value']
            if Fraction(int(value['numerator']),int(value['denominator']))!=Fraction(plan['geometry']['anchors'][0]['price']):raise BotError('STRATEGY_READBACK_MISMATCH')
            completed=dict(**plan,drawing_id=item['drawing_id'],revision=item['revision'],note=note,query=query,state='APPLIED',order_authority=False)
            state.update(pending=None,latest=completed);self._save(state)
            return completed
