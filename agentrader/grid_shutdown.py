"""Durable stop barrier for a grid; proposes cleanup, never sends requests."""
from .risk import number


class GridShutdown:
    def __init__(self, store, journal, owner, symbol):
        self.store, self.journal = store, journal
        self.owner, self.symbol = owner, symbol
        store.db.execute('''CREATE TABLE IF NOT EXISTS grid_shutdown (
            owner TEXT NOT NULL, symbol TEXT NOT NULL, phase TEXT NOT NULL,
            reason TEXT NOT NULL, PRIMARY KEY(owner,symbol))''')

    def phase(self):
        row = self.store.db.execute('SELECT phase FROM grid_shutdown WHERE owner=? AND symbol=?',
                                    (self.owner, self.symbol)).fetchone()
        return row['phase'] if row else 'ACTIVE'

    def stop(self, reason):
        if not isinstance(reason, str) or not reason:
            raise ValueError('Stop reason required.')
        with self.store.db:
            self.store.db.execute('INSERT OR IGNORE INTO grid_shutdown VALUES (?,?,?,?)',
                                  (self.owner, self.symbol, 'STOPPING', reason))
        return self.phase()

    def assert_entry_allowed(self):
        if self.phase() != 'ACTIVE':
            raise ValueError('Stopped grid cannot open or replenish inventory.')

    def cleanup(self, *, account_position, open_client_ids, snapshot_fresh,
                ownership_verified):
        """Require independently read REST state; empty streams are not flat proof.

        Cancel every owned active order before closing residual inventory. Even
        reducing limit orders must reach terminal state to avoid a close race.
        """
        if self.phase() == 'ACTIVE':
            raise ValueError('Persist the stop barrier before requesting cleanup.')
        result = {'phase': self.phase(), 'execution_authorized': False, 'actions': []}
        if not snapshot_fresh or not ownership_verified:
            return result | {'blocked': 'FRESH_OWNED_SNAPSHOT_REQUIRED'}
        if not isinstance(open_client_ids, (set, list, tuple)) or any(
                not isinstance(cid, str) for cid in open_client_ids):
            raise ValueError('Open-order client identities required.')
        rows = [dict(row) for row in self.store.db.execute(
            'SELECT * FROM order_projection WHERE owner=? AND symbol=?',
            (self.owner, self.symbol))]
        owned_ids = {row['client_id'] for row in rows}
        if set(open_client_ids) - owned_ids:
            return result | {'blocked': 'FOREIGN_OPEN_ORDER'}
        unresolved = [row for row in self.journal.unresolved(self.owner)
                      if row['symbol'] == self.symbol]
        pending = set(open_client_ids) | {row['client_id'] for row in unresolved}
        if pending:
            return result | {'actions': [{'kind': 'QUERY_THEN_CANCEL', 'client_id': cid}
                                         for cid in sorted(pending)],
                             'blocked': 'WAIT_FOR_TERMINAL_ORDERS'}
        inventory = self.journal.inventory(self.owner, self.symbol)
        position = number(account_position)
        if inventory != position:
            return result | {'blocked': 'INVENTORY_POSITION_MISMATCH'}
        if position != 0:
            return result | {'actions': [{'kind': 'REDUCE_ONLY_CLOSE',
                                          'side': 'SELL' if position > 0 else 'BUY',
                                          'quantity': str(abs(position))}],
                             'blocked': 'WAIT_FOR_FLAT_POSITION'}
        with self.store.db:
            self.store.db.execute("UPDATE grid_shutdown SET phase='CLOSED' WHERE owner=? AND symbol=?",
                                  (self.owner, self.symbol))
        return result | {'phase': 'CLOSED', 'blocked': None}
