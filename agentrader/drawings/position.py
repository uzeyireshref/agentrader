"""Pure hypothetical USD-M position arithmetic; no account or execution imports."""
from fractions import Fraction
from ..chart_precision import decimal_text

KINDS = ('long_plan', 'short_plan')


def metrics(value):
    if value.get('schema') != 'chart-position/1' or value.get('kind') not in KINDS:
        raise ValueError('INVALID_POSITION')
    anchors, params = value['anchors'], value['params']
    if len(anchors) != 3 or anchors[1]['time'] != anchors[2]['time'] or anchors[0]['time'] >= anchors[1]['time']:
        raise ValueError('INVALID_POSITION_TIME')
    if not isinstance(params, dict) or set(params) != {'risk_budget', 'fee_bps', 'slippage_bps'}:
        raise ValueError('INVALID_POSITION_PARAMS')
    entry, stop, target = [Fraction(decimal_text(a['price'], positive=True)) for a in anchors]
    direction = 1 if value['kind'] == 'long_plan' else -1
    risk, reward = direction*(entry-stop), direction*(target-entry)
    if risk <= 0 or reward <= 0:
        raise ValueError('INVALID_POSITION_ORDER')
    fee, slip = [Fraction(decimal_text(params[k], positive=False)) for k in ('fee_bps', 'slippage_bps')]
    if not 0 <= fee <= 1000 or not 0 <= slip <= 1000:
        raise ValueError('INVALID_POSITION_COST')
    budget = None if params['risk_budget'] is None else Fraction(decimal_text(params['risk_budget'], positive=True))
    fee, slip = fee/10000, slip/10000
    entry_fill = entry*(1+direction*slip)
    stop_fill, target_fill = stop*(1-direction*slip), target*(1-direction*slip)
    net_risk = direction*(entry_fill-stop_fill)+fee*(entry_fill+stop_fill)
    net_reward = direction*(target_fill-entry_fill)-fee*(entry_fill+target_fill)
    qty = None if budget is None else budget/net_risk
    return dict(gross_risk=risk, gross_reward=reward, gross_rr=reward/risk,
                risk_percent=risk/entry*100, reward_percent=reward/entry*100,
                net_risk=net_risk, net_reward=net_reward, net_rr=net_reward/net_risk,
                entry_fill=entry_fill, stop_fill=stop_fill, target_fill=target_fill,
                quantity=qty, notional=None if qty is None else qty*entry_fill,
                loss_budget=budget, target_pnl=None if qty is None else qty*net_reward)
