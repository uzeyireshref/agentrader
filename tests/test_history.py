import unittest

from agentrader.history import account_trades, income_history, IncompleteHistory


def income(i, timestamp, kind='COMMISSION'):
    return dict(tranId=i, time=timestamp, incomeType=kind, asset='USDT', income='-0.1')


class HistoryExchange:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def get(self, path, params):
        self.calls.append((path, params))
        return [r for r in self.rows if params['startTime'] <= r['time'] <= params['endTime']][:params['limit']]


class IncomeHistoryTests(unittest.TestCase):
    def test_dense_history_preserves_inclusive_boundaries_and_all_amounts(self):
        rows = [income(i, i//3) for i in range(2501)]
        x = HistoryExchange(rows)
        result = income_history(x, 0, 900)
        self.assertEqual(len(result), len(rows))
        self.assertEqual({r['tranId'] for r in result}, set(range(2501)))
        self.assertGreater(len(x.calls), 1)
        self.assertTrue(all(p['endTime'] <= 900 for _, p in x.calls))

    def test_saturated_millisecond_fails_instead_of_skipping_records(self):
        x = HistoryExchange([income(i, 10) for i in range(1001)])
        with self.assertRaises(IncompleteHistory):
            income_history(x, 0, 20)

    def test_request_budget_never_returns_partial_history(self):
        x = HistoryExchange([income(i, i) for i in range(1200)])
        with self.assertRaises(IncompleteHistory):
            income_history(x, 0, 2000, max_requests=2)
        self.assertEqual(len(x.calls), 2)

    def test_ids_are_scoped_by_income_type_and_duplicates_not_double_counted(self):
        a = income(1, 1)
        x = HistoryExchange([a, dict(a), income(1, 1, 'REALIZED_PNL')])
        self.assertEqual(len(income_history(x, 0, 2)), 2)
        x.rows.append(dict(a, income='-9'))
        with self.assertRaises(IncompleteHistory):
            income_history(x, 0, 2)

    def test_invalid_and_out_of_window_data_reject(self):
        for change in ({'time': 99}, {'income': 'NaN'}, {'tranId': None}, {'asset': ''}):
            class Broken:
                def get(self, *args):
                    return [dict(income(1, 1), **change)]
            with self.subTest(change=change), self.assertRaises(IncompleteHistory):
                income_history(Broken(), 0, 2)

    def test_exchange_failure_propagates_without_partial_result(self):
        class Broken(HistoryExchange):
            def get(self, path, params):
                if self.calls:
                    raise ConnectionError('offline')
                return super().get(path, params)
        with self.assertRaises(ConnectionError):
            income_history(Broken([income(i, i) for i in range(1001)]), 0, 2000)


def trade(i, timestamp=10):
    return dict(id=i, orderId=7, symbol='BTCUSDT', time=timestamp, qty='0.001', side='BUY')


class TradeExchange:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def get(self, path, params):
        self.calls.append((path, params))
        if 'fromId' in params:
            if 'startTime' in params or 'endTime' in params:
                raise AssertionError('fromId cannot be combined with dates')
            rows = [r for r in self.rows if r['id'] >= params['fromId']]
        else:
            rows = [r for r in self.rows if params['startTime'] <= r['time'] <= params['endTime']]
        return rows[:params['limit']]


class AccountTradeHistoryTests(unittest.TestCase):
    def test_more_than_1000_fills_at_same_millisecond_are_all_read(self):
        x = TradeExchange([trade(i*2) for i in range(2501)])
        result = account_trades(x, 'BTCUSDT', 0, 20)
        self.assertEqual(len(result), 2501)
        self.assertEqual(len(x.calls), 3)
        self.assertEqual(x.calls[1][1], dict(symbol='BTCUSDT', fromId=1999, limit=1000))

    def test_frozen_end_excludes_new_trades_on_id_continuation(self):
        x = TradeExchange([trade(i) for i in range(1000)]+[trade(1000, 21)])
        self.assertEqual(len(account_trades(x, 'BTCUSDT', 0, 20)), 1000)
        self.assertEqual(len(x.calls), 2)

    def test_repeated_cursor_and_conflicting_duplicate_fail_closed(self):
        class Broken(TradeExchange):
            def get(self, path, params):
                return self.rows[:params['limit']]
        with self.assertRaises(IncompleteHistory):
            account_trades(Broken([trade(i) for i in range(1000)]), 'BTCUSDT', 0, 20)
        with self.assertRaises(IncompleteHistory):
            account_trades(TradeExchange([trade(1), dict(trade(1), qty='1')]), 'BTCUSDT', 0, 20)

    def test_budget_exhaustion_never_returns_partial_inventory(self):
        with self.assertRaises(IncompleteHistory):
            account_trades(TradeExchange([trade(i) for i in range(1001)]),
                           'BTCUSDT', 0, 20, max_requests=1)

    def test_invalid_fills_and_time_order_are_rejected(self):
        for change in ({'qty': 'NaN'}, {'qty': '-1'}, {'side': 'OTHER'},
                       {'symbol': 'ETHUSDT'}, {'id': True}, {'orderId': None}):
            with self.subTest(change=change), self.assertRaises(IncompleteHistory):
                account_trades(TradeExchange([dict(trade(1), **change)]), 'BTCUSDT', 0, 20)
        with self.assertRaises(IncompleteHistory):
            account_trades(TradeExchange([trade(1, 12), trade(2, 11)]), 'BTCUSDT', 0, 20)

    def test_unsupported_window_and_invalid_budgets_do_not_send(self):
        for options in ({'end_ms': 8*86400000}, {'end_ms': -1},
                        {'page_size': 1001}, {'max_requests': 0}):
            x = TradeExchange([])
            with self.subTest(options=options), self.assertRaises(ValueError):
                account_trades(x, 'BTCUSDT', 0, **options)
            self.assertEqual(x.calls, [])

    def test_exact_full_last_page_requires_empty_confirmation(self):
        x = TradeExchange([trade(i) for i in range(1000)])
        self.assertEqual(len(account_trades(x, 'BTCUSDT', 0, 20)), 1000)
        self.assertEqual(len(x.calls), 2)


if __name__ == '__main__':
    unittest.main()
