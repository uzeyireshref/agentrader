"""Validate the full published notional ladder before selecting a risk tier."""
from agentrader.bot.risk import number


def validate_brackets(rows):
    if not isinstance(rows,list) or not rows:
        raise ValueError('Kaldıraç basamakları eksik.')
    previous_cap=number(0);previous_ratio=number(0);previous_leverage=None
    for row in rows:
        if not isinstance(row,dict):raise ValueError('Geçersiz kaldıraç basamağı.')
        try:
            floor,cap,ratio,deduction=map(number,(row['notionalFloor'],row['notionalCap'],row['maintMarginRatio'],row.get('cum',0)))
            maximum=row['initialLeverage']
        except KeyError:
            raise ValueError('Kaldıraç basamağı alanları eksik.') from None
        if (floor!=previous_cap or cap<=floor or not previous_ratio<=ratio<1 or deduction<0
                or type(maximum)is not int or maximum<1 or previous_leverage is not None and maximum>previous_leverage):
            raise ValueError('Kaldıraç basamakları boşluklu, çakışan veya geçersiz.')
        previous_cap,previous_ratio,previous_leverage=cap,ratio,maximum
    return rows


def select_bracket(rows, notional, leverage):
    amount=number(notional)
    if amount<=0 or type(leverage)is not int or leverage<1:
        raise ValueError('Basamak için pozitif nominal ve geçerli kaldıraç gerekli.')
    rows=validate_brackets(rows)
    selected=next((r for r in rows if number(r['notionalFloor'])<=amount<number(r['notionalCap'])),None)
    if selected is None or leverage>selected['initialLeverage']:
        raise ValueError('Toplam nominal/kaldıraç doğrulanmış basamağı aşıyor.')
    return selected


def leverage_constraints(payload,symbol,leverage):
    if type(leverage)is not int or leverage<1:raise ValueError('Pozitif tamsayı kaldıraç gerekli.')
    payload=[payload] if isinstance(payload,dict) else payload
    if not isinstance(payload,list) or any(not isinstance(r,dict) for r in payload):raise ValueError('Hesap kaldıraç yanıtı geçersiz.')
    selected=[r for r in payload if r.get('symbol')==symbol]
    if len(selected)!=1 or number(selected[0].get('notionalCoef',1))!=1:raise ValueError('Hesap/sembol kaldıraç kapsamı doğrulanamadı.')
    rows=validate_brackets(selected[0].get('brackets'))
    maximum=rows[0]['initialLeverage']
    if leverage>maximum:raise ValueError('Kaldıraç güncel hesap/sembol sınırını aşıyor.')
    return {'maximum_leverage':maximum,'requested_leverage':leverage,
            'max_notional_for_requested':str(max(number(r['notionalCap']) for r in rows if r['initialLeverage']>=leverage)),
            'bracket_count':len(rows)}
