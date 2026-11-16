"""Bounded REST history collection; never return a truncated risk view."""
import time
from decimal import Decimal, InvalidOperation


class IncompleteHistory(ValueError):
    pass


def account_trades(exchange, symbol, start_ms, end_ms=None, *, page_size=1000, max_requests=100):
    """Freeze the time boundary, then continue by trade ID (never timestamp+1)."""
    end_ms = (int(time.time()*1000) + getattr(exchange, 'offset_ms', 0)
              if end_ms is None else end_ms)
    if (type(start_ms) is not int or type(end_ms) is not int or
            not 0 <= start_ms <= end_ms or end_ms-start_ms > 7*86400000 or
            type(page_size) is not int or not 1 <= page_size <= 1000 or
            type(max_requests) is not int or max_requests < 1):
        raise ValueError('Geçersiz gerçekleşme geçmişi aralığı veya bütçesi.')
    params = dict(symbol=symbol, startTime=start_ms, endTime=end_ms, limit=page_size)
    seen = {}
    cursor = None
    previous_time = start_ms
    for _ in range(max_requests):
        rows = exchange.get('/fapi/v1/userTrades', params)
        if not isinstance(rows, list) or len(rows) > page_size:
            raise IncompleteHistory('Geçersiz gerçekleşme geçmişi yanıtı.')
        ids = []
        passed_end = False
        for row in rows:
            if (not isinstance(row, dict) or row.get('symbol') != symbol or
                    type(row.get('id')) is not int or row['id'] < 0 or
                    type(row.get('orderId')) is not int or row['orderId'] < 0 or
                    type(row.get('time')) is not int or row['time'] < start_ms or
                    row.get('side') not in ('BUY', 'SELL')):
                raise IncompleteHistory('Geçersiz gerçekleşme kaydı.')
            try:
                qty = Decimal(str(row['qty']))
                if not qty.is_finite() or qty <= 0:
                    raise ValueError()
            except (KeyError, InvalidOperation, ValueError):
                raise IncompleteHistory('Geçersiz gerçekleşme miktarı.') from None
            ident = row['id']
            if (cursor is not None and ident < cursor) or (ids and ident <= ids[-1]):
                raise IncompleteHistory('Gerçekleşme geçmişi ilerlemiyor.')
            if row['time'] < previous_time:
                raise IncompleteHistory('Gerçekleşme zaman sırası uyuşmuyor.')
            previous_time = row['time']
            ids.append(ident)
            if row['time'] > end_ms:
                if cursor is None:
                    raise IncompleteHistory('Gerçekleşme istenen aralık dışında.')
                passed_end = True
                continue
            if passed_end:
                raise IncompleteHistory('Gerçekleşme zaman sırası uyuşmuyor.')
            if ident in seen:
                raise IncompleteHistory('Tekrarlanan gerçekleşme kimliği.')
            seen[ident] = row
        if passed_end or len(rows) < page_size:
            return list(seen.values())
        cursor = ids[-1]+1
        params = dict(symbol=symbol, fromId=cursor, limit=page_size)
    raise IncompleteHistory('Gerçekleşme geçmişi istek bütçesini aştı.')


def income_history(exchange, start_ms, end_ms=None, *, page_size=1000, max_requests=127):
    """Split saturated inclusive windows, including their millisecond boundaries.

    A full single-millisecond window cannot prove completeness without a cursor.
    Fail closed in that case, and on exhausted request budgets.
    """
    end_ms = (int(time.time()*1000) + getattr(exchange, 'offset_ms', 0)
              if end_ms is None else end_ms)
    if (type(start_ms) is not int or type(end_ms) is not int or
            not 0 <= start_ms <= end_ms or type(page_size) is not int or
            not 1 <= page_size <= 1000 or type(max_requests) is not int or max_requests < 1):
        raise ValueError('Geçersiz geçmiş aralığı veya istek bütçesi.')
    pending = [(start_ms, end_ms)]
    result = []
    calls = 0
    while pending:
        if calls >= max_requests:
            raise IncompleteHistory('Gelir geçmişi istek bütçesini aştı; eksik veri kullanılamaz.')
        low, high = pending.pop()
        rows = exchange.get('/fapi/v1/income',
                            {'startTime': low, 'endTime': high, 'limit': page_size})
        calls += 1
        if not isinstance(rows, list) or len(rows) > page_size:
            raise IncompleteHistory('Geçersiz gelir geçmişi yanıtı.')
        for row in rows:
            if not isinstance(row, dict):
                raise IncompleteHistory('Geçersiz gelir kaydı.')
            if (type(row.get('time')) is not int or not low <= row['time'] <= high or
                    type(row.get('tranId')) is not int or row['tranId'] < 0 or
                    not isinstance(row.get('incomeType'), str) or not row['incomeType'] or
                    not isinstance(row.get('asset'), str) or not row['asset']):
                raise IncompleteHistory('Gelir kaydı istenen zaman aralığı dışında.')
            try:
                if not Decimal(str(row['income'])).is_finite():
                    raise ValueError()
            except (KeyError, InvalidOperation, ValueError):
                raise IncompleteHistory('Geçersiz gelir tutarı.') from None
        if len(rows) == page_size:
            if low == high:
                raise IncompleteHistory('Tek milisaniyedeki gelir kayıtları eksiksiz doğrulanamadı.')
            middle = (low + high)//2
            pending.extend(((middle+1, high), (low, middle)))
        else:
            result.extend(rows)
    # Transaction identifiers are scoped by income type, not globally unique.
    seen = {}
    unique = []
    for row in result:
        key = (row.get('incomeType'), str(row['tranId']))
        if key in seen:
            if seen[key] != row:
                raise IncompleteHistory('Çelişkili gelir işlem kimliği.')
            continue
        seen[key] = row
        unique.append(row)
    return unique
