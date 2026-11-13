"""Version 2 contracts for leveraged SINGLE/GRID plans; no implicit execution grant."""
import re
from decimal import Decimal

from .plans import exact_fields,positive,timestamp


def validate_v2(plan):
    if (isinstance(plan,dict) and (plan.get('direction')=='NEUTRAL' or
            isinstance(plan.get('execution'),dict) and plan['execution'].get('strategy')=='NEUTRAL_GRID')):
        from .neutral_plan import validate_neutral
        return validate_neutral(plan)
    optional={'grid'}
    exact_fields({k:v for k,v in plan.items() if k not in optional},
        'schema_version plan_id version environment exchange product symbol position_mode direction mode created_at expires_at entry sizing stop targets management max_runs analysis_ref rationale execution',
        'Plan v2')
    if type(plan['schema_version']) is not int or plan['schema_version']!=2:
        raise ValueError('Plan v2 şeması gerekli.')
    if not isinstance(plan['plan_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',plan['plan_id']):
        raise ValueError('Plan kimliği geçersiz.')
    if type(plan['version']) is not int or plan['version']<1: raise ValueError('Sürüm geçersiz.')
    if (plan['environment'],plan['exchange'],plan['product'])!=('demo','binance','USD-M'):
        raise ValueError('Plan v2 yalnız demo Binance USD-M destekler.')
    if plan['position_mode'] not in ('one-way','hedge') or plan['direction'] not in ('LONG','SHORT'):
        raise ValueError('Yön veya hesap modu geçersiz.')
    if not isinstance(plan['symbol'],str) or not re.fullmatch(r'[A-Z0-9]{2,20}USDT',plan['symbol']):
        raise ValueError('Sembol geçersiz.')
    if plan['mode'] not in ('A','B'): raise ValueError('Yetki modu geçersiz.')
    created,expires=timestamp(plan['created_at']),timestamp(plan['expires_at'])
    if not 0<expires-created<=5*86400: raise ValueError('Geçerlilik en fazla beş gün olabilir.')
    execution=plan['execution']
    exact_fields(execution,'strategy leverage margin_mode','Yürütme')
    if execution['strategy'] not in ('SINGLE','GRID') or execution['margin_mode'] not in ('CROSSED','ISOLATED'):
        raise ValueError('Strateji veya teminat modu geçersiz.')
    if type(execution['leverage']) is not int or not 1<=execution['leverage']<=125:
        raise ValueError('Kaldıraç geçersiz.')
    entry=plan['entry'];exact_fields(entry,'condition reference_price trigger_price max_drift_bps','Giriş')
    if entry['condition'] not in ('IMMEDIATE','LIMIT','MARK_AT_OR_BELOW','MARK_AT_OR_ABOVE'):
        raise ValueError('Giriş koşulu desteklenmiyor.')
    ref=positive(entry['reference_price'],'Referans')
    if positive(entry['max_drift_bps'],'Tolerans')>100: raise ValueError('Tolerans en fazla 100 bps.')
    if entry['condition']=='IMMEDIATE':
        if entry['trigger_price'] is not None: raise ValueError('Anlık girişte tetik boş olmalı.')
    else: positive(entry['trigger_price'],'Tetik')
    exact_fields(plan['sizing'],'kind amount currency','Bütçe')
    if plan['sizing']['kind'] not in ('NOTIONAL','MARGIN','MAX_LOSS') or plan['sizing']['currency']!='USDT':
        raise ValueError('Bütçe türü açık ve USDT olmalı.')
    positive(plan['sizing']['amount'],'Bütçe')
    stop=positive(plan['stop'],'Stop')
    direction=1 if plan['direction']=='LONG' else -1
    if direction*(ref-stop)<=0: raise ValueError('Stop yönle uyumsuz.')
    targets=plan['targets']
    if not isinstance(targets,list) or not 1<=len(targets)<=8: raise ValueError('1–8 hedef gerekli.')
    previous=ref;total=Decimal(0)
    for target in targets:
        exact_fields(target,'price fraction','Hedef')
        price=positive(target['price'],'Hedef')
        total+=positive(target['fraction'],'Hedef payı')
        if direction*(price-previous)<=0: raise ValueError('Hedef sırası yönle uyumsuz.')
        previous=price
    if total!=1: raise ValueError('Hedef payları toplamı 1 olmalı.')
    if entry['trigger_price'] is not None:
        trigger=positive(entry['trigger_price'],'Tetik')
        if direction*(trigger-stop)<=0 or direction*(Decimal(targets[0]['price'])-trigger)<=0:
            raise ValueError('Tetik fiyatı stop ve ilk hedef aralığında olmalı.')
    management=plan['management']
    if not isinstance(management,dict):
        raise ValueError('Yönetim nesne olmalı.')
    exact_fields({k:v for k,v in management.items() if k!='trailing'},
                 'break_even_after_target allow_scale_in allow_reverse allow_reentry','Yönetim')
    trailing=management.get('trailing')
    if trailing is not None:
        if not isinstance(trailing,dict):raise ValueError('Takip eden stop nesne olmalı.')
        exact_fields({k:v for k,v in trailing.items() if k!='native_stop'},'activation_price distance_bps min_step_bps','Takip eden stop')
        if 'native_stop' in trailing and (type(trailing['native_stop']) is not bool or execution['strategy']!='GRID'):
            raise ValueError('native_stop boolean olmalı ve yalnız yönlü GRID ile kullanılabilir.')
        activation=positive(trailing['activation_price'],'Takip etkinleşme fiyatı')
        distance=positive(trailing['distance_bps'],'Takip mesafesi')
        step=positive(trailing['min_step_bps'],'Takip güncelleme aralığı')
        if not 1<=distance<=5000 or not 1<=step<=distance:
            raise ValueError('Takip mesafesi 1–5000 bps, güncelleme aralığı 1–mesafe arasında olmalı.')
        if direction*(activation-ref)<0 or direction*(Decimal(targets[-1]['price'])-activation)<=0:
            raise ValueError('Takip etkinleşmesi referans ile son hedef arasında olmalı.')
    for key in ('allow_scale_in','allow_reverse','allow_reentry'):
        if type(management[key]) is not bool: raise ValueError('Yönetim izni boolean olmalı.')
    if management['allow_reverse']: raise ValueError('Otomatik yön çevirme desteklenmiyor.')
    be=management['break_even_after_target']
    if be is not None and (type(be) is not int or not 1<=be<len(targets)):
        raise ValueError('Girişe stop hedefi geçersiz.')
    if type(plan['max_runs']) is not int or plan['max_runs']!=1:
        raise ValueError('Plan ilk etkinleştirmede tek başlangıç girişine yetkilidir.')
    if execution['strategy']=='GRID':
        if 'grid' not in plan: raise ValueError('Grid tanımı gerekli.')
        g=plan['grid'];exact_fields(g,'lower upper intervals spacing','Grid')
        lo,hi=positive(g['lower'],'Alt'),positive(g['upper'],'Üst')
        if not lo<=ref<hi or type(g['intervals']) is not int or not 2<=g['intervals']<=100:
            raise ValueError('Grid bandı veya sayısı geçersiz.')
        if g['spacing'] not in ('ARITHMETIC','GEOMETRIC'): raise ValueError('Grid aralık türü geçersiz.')
        if not management['allow_scale_in'] or not management['allow_reentry'] or be is not None:
            raise ValueError('Grid döngü yetkisi açık olmalı; otomatik girişe stop ayrı politikadır.')
    elif 'grid' in plan or management['allow_scale_in'] or management['allow_reentry']:
        raise ValueError('Tek giriş planında grid/artırma/yeniden giriş desteklenmiyor.')
    for field in ('analysis_ref','rationale'):
        if not isinstance(plan[field],str) or not 1<=len(plan[field])<=2000:
            raise ValueError('Plan gerekçesi ve analiz kaynağı gerekli.')
    return plan
