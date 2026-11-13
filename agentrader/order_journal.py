"""Persistent internal order projection; adapters must normalize exchange events.

This module never submits orders. Cumulative fills, rather than delivery count,
drive inventory so duplicate, delayed and cancel-race observations are harmless.
"""
import json
from decimal import Decimal

from .risk import number

STATUSES = {'NEW', 'PARTIALLY_FILLED', 'FILLED', 'CANCELED', 'EXPIRED', 'REJECTED'}
TERMINAL = {'FILLED', 'CANCELED', 'EXPIRED', 'REJECTED'}


class OrderJournal:
    def __init__(self, store):
        self.db = store.db
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS order_projection (
              client_id TEXT PRIMARY KEY, owner TEXT NOT NULL, symbol TEXT NOT NULL,
              side TEXT NOT NULL, quantity TEXT NOT NULL, filled TEXT NOT NULL,
              status TEXT NOT NULL, observed_ms INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS order_observations (
              client_id TEXT NOT NULL, event_id TEXT NOT NULL, body TEXT NOT NULL,
              PRIMARY KEY(client_id,event_id));
        ''')

    def register(self, client_id, owner, symbol, side, quantity):
        if not all(isinstance(v, str) and v for v in (client_id, owner, symbol)):
            raise ValueError('Order identity and owner are required.')
        q = number(quantity)
        if side not in ('BUY', 'SELL') or q <= 0:
            raise ValueError('Invalid order side or quantity.')
        with self.db:
            row = self.db.execute('SELECT * FROM order_projection WHERE client_id=?',
                                  (client_id,)).fetchone()
            if row:
                if (row['owner'], row['symbol'], row['side'], number(row['quantity'])) != (owner, symbol, side, q):
                    raise ValueError('Order identity already belongs to another intent.')
                return self.get(client_id)
            self.db.execute('INSERT INTO order_projection VALUES (?,?,?,?,?,?,?,?)',
                            (client_id, owner, symbol, side, str(q), '0', 'UNKNOWN', 0))
        return self.get(client_id)

    def get(self, client_id):
        row = self.db.execute('SELECT * FROM order_projection WHERE client_id=?',
                              (client_id,)).fetchone()
        if row is None:
            raise ValueError('Unowned order; reconciliation required.')
        result = dict(row)
        result['remaining'] = str(number(row['quantity']) - number(row['filled']))
        result['terminal'] = row['status'] in TERMINAL
        return result

    def observe(self, client_id, event_id, *, status, cumulative_filled, observed_ms):
        if status not in STATUSES or not isinstance(event_id, str) or not event_id:
            raise ValueError('Invalid normalized order event.')
        if type(observed_ms) is not int or observed_ms < 0:
            raise ValueError('Invalid event timestamp.')
        filled = number(cumulative_filled)
        body = json.dumps([status, str(filled), observed_ms], separators=(',', ':'))
        with self.db:
            # Serialize the read/merge/write across separate processes too.
            self.db.execute('BEGIN IMMEDIATE')
            current = self.get(client_id)
            existing = self.db.execute(
                'SELECT body FROM order_observations WHERE client_id=? AND event_id=?',
                (client_id, event_id)).fetchone()
            if existing:
                if existing['body'] != body:
                    raise ValueError('Conflicting replay for the same event identity.')
                return current | {'fill_delta': '0', 'duplicate': True}
            quantity = number(current['quantity'])
            if not 0 <= filled <= quantity:
                raise ValueError('Cumulative fill exceeds the owned order quantity.')
            if status == 'FILLED' and filled != quantity:
                raise ValueError('FILLED requires the complete quantity.')
            if status == 'REJECTED' and filled != 0:
                raise ValueError('Rejected order cannot contain executions.')
            old_filled = number(current['filled'])
            delta = max(Decimal(0), filled - old_filled)
            merged_fill = max(old_filled, filled)
            merged_status = current['status']
            if merged_fill == quantity:
                merged_status = 'FILLED'
            elif current['terminal']:
                # Late execution updates inventory but never reopens a canceled order.
                pass
            elif status in TERMINAL or observed_ms >= current['observed_ms']:
                merged_status = status
                if merged_fill > 0 and status == 'NEW':
                    merged_status = 'PARTIALLY_FILLED'
            self.db.execute('INSERT INTO order_observations VALUES (?,?,?)',
                            (client_id, event_id, body))
            self.db.execute('UPDATE order_projection SET filled=?,status=?,observed_ms=? WHERE client_id=?',
                            (str(merged_fill), merged_status, max(observed_ms, current['observed_ms']), client_id))
        return self.get(client_id) | {'fill_delta': str(delta), 'duplicate': False}

    def inventory(self, owner, symbol):
        rows = self.db.execute('SELECT side,filled FROM order_projection WHERE owner=? AND symbol=?',
                               (owner, symbol))
        return sum((number(row['filled']) * (1 if row['side'] == 'BUY' else -1)
                    for row in rows), Decimal(0))

    def unresolved(self, owner):
        return [dict(row) for row in self.db.execute(
            "SELECT * FROM order_projection WHERE owner=? AND status NOT IN ('FILLED','CANCELED','EXPIRED','REJECTED')",
            (owner,))]
