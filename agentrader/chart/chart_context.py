"""Bounded, read-only chart snapshots. Readiness is never execution authority."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from agentrader.chart.chart_evidence import digest, snapshot, grid_info
from agentrader.chart.chart_market import validate_selection
from agentrader.chart.chart_profiles import ProfileService
from agentrader.chart.drawings.service import DrawingError, DrawingService, identifier
from agentrader.chart.indicator_config import defaults_v4, expand_v4
from agentrader.shared.market_data import INTERVALS
from agentrader.shared.market_environment import SOURCE, ENVIRONMENT

SCHEMA_VERSION = 'chart-context/1'
CALCULATION_VERSION = 'chart-context-readiness/1'
IDENTITY = dict(source=SOURCE, environment=ENVIRONMENT, product='USD-M', price_type='LAST_PRICE')


class ContextChanged(DrawingError):
    status = 409
    code = 'CONTEXT_CHANGED'


class ContextSourceMismatch(DrawingError):
    code = 'SOURCE_MISMATCH'


class ContextReadLimit(DrawingError):
    status = 503
    code = 'CONTEXT_READ_TIME_LIMIT'


class ChartContext:
    def __init__(self, database, owner, hub, *, clock=time.time, monotonic=time.monotonic, ui_sessions=None):
        self.database, self.owner, self.hub = Path(database), owner, hub
        self.clock, self.monotonic = clock, monotonic
        self.ui_sessions = ui_sessions
        self.drawings = DrawingService(database, owner)
        self.profiles = ProfileService(database, owner)

    def _persistent(self, workspace_id, symbol, interval, limit, offset, deadline):
        # A read-only SQLite connection cannot create a missing store or mutate user data.
        with closing(sqlite3.connect(self.database.resolve().as_uri()+'?mode=ro', uri=True, timeout=.2)) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA query_only=ON')
            db.set_progress_handler(lambda: int(self.monotonic() > deadline), 1000)
            try:
                db.execute('BEGIN')
                row = db.execute('SELECT * FROM app_workspaces WHERE owner=? AND workspace_id=?', (self.owner, workspace_id)).fetchone()
                workspace = dict(workspace_id=workspace_id, revision=row['revision'] if row else 0,
                                 preferences=json.loads(row['body']) if row else dict(symbol='BTCUSDT', interval='15m'))
                symbol = symbol or workspace['preferences']['symbol']
                interval = interval or workspace['preferences']['interval']
                validate_selection(symbol, interval)
                row = db.execute('SELECT * FROM app_indicator_configs WHERE owner=? AND workspace_id=?', (self.owner, workspace_id)).fetchone()
                indicators = dict(schema='chart-indicators/4', workspace_id=workspace_id,
                                  revision=row['revision'] if row else 0,
                                  indicators=expand_v4(json.loads(row['body'])) if row else defaults_v4())
                profile = self.profiles._profile(db, workspace_id)
                # Include tombstone heads in the stamp: deletions cannot disappear from revision checks.
                revisions = hashlib.sha256()
                count = 0
                items = []
                rows = db.execute('''SELECT r.* FROM app_drawing_revisions r JOIN app_drawing_heads h
                    ON r.owner=h.owner AND r.drawing_id=h.drawing_id AND r.revision=h.revision
                    WHERE r.owner=? AND r.workspace_id=? AND json_extract(r.geometry,'$.symbol')=? ORDER BY r.drawing_id''', (self.owner, workspace_id, symbol)).fetchall()
                metadata = self.drawings._metadata(db, rows)
                for row in rows:
                    if self.monotonic() > deadline:
                        raise ContextReadLimit()
                    geometry = json.loads(row['geometry'])
                    if geometry['symbol'] != symbol:
                        continue
                    revisions.update(json.dumps([row['drawing_id'], row['revision'], row['deleted'], metadata[row['drawing_id']]['origin'], metadata[row['drawing_id']]['linked_note']], separators=(',', ':')).encode())
                    if row['deleted']:
                        continue
                    if offset <= count < offset+limit:
                        items.append(self.drawings._view(row,db,metadata[row['drawing_id']]))
                    count += 1
                stamp = digest(dict(workspace=workspace, indicators=indicators, profile=profile,
                                    drawings=revisions.hexdigest(), symbol=symbol, interval=interval))
                return dict(workspace=workspace, indicators=indicators, profile=profile, drawings=items,
                            count=count, stamp=stamp, symbol=symbol, interval=interval)
            except sqlite3.OperationalError as exc:
                if 'interrupted' in str(exc):
                    raise ContextReadLimit() from None
                raise

    def _data(self, symbol, interval):
        # Existing hub evidence only; never acquire a subscription, fetch REST or write candles.
        return self.hub.binding_context(symbol, interval)

    def _data_stamp(self, data):
        if data is None:
            return None
        # Dynamic ages are excluded; transitions to stale and clock failure are included.
        return digest(dict(identity=data.get('identity'), epoch=data.get('stream_epoch'),
                           generation=data.get('generation'), revision=data.get('data_revision'),
                           sequence=data.get('sequence'), proof=data.get('data_proof'),
                           transport=data.get('transport_state'), timing_state=data.get('timing', {}).get('state'),
                           timing_reason=data.get('timing', {}).get('reason')))

    def _readiness(self, data, symbol, interval, required, include_open):
        summary = dict(state='WAITING_FOR_DATA', scope='DATA_SNAPSHOT_NOT_STRATEGY_OR_ORDER_ELIGIBILITY',
                       reasons=['NO_ACTIVE_FEED'], available_count=0, available_closed_count=0,
                       warmup_available_closed_bars=0, required_closed_bars=required, missing_ranges=[],
                       history_completeness='UNKNOWN_BEFORE_LOADED_RANGE', last_closed_candle=None,
                       open_candle_present=False, open_candle_used=False, stale=False,
                       source_clock=dict(state='UNAVAILABLE', reason='NO_ACTIVE_FEED'),
                       consumed_range=None, consumed_data_hash=None, proof=None,
                       indicator_calculations='QUERY_ENDPOINT_AVAILABLE_NOT_COMPUTED_IN_CONTEXT', order_authority=False)
        if data is None:
            return summary
        expected = dict(IDENTITY, symbol=symbol, interval=interval)
        if data.get('identity') != expected or (data.get('market') or {}).get('symbol') != symbol:
            summary.update(state='SOURCE_MISMATCH', reasons=['FEED_IDENTITY_MISMATCH'])
            return summary
        rows = data.get('rows', [])
        quality = data.get('quality', {})
        if not isinstance(rows, list) or len(rows) > 499:
            summary.update(state='INVALID_INPUT', reasons=['INVALID_DATA_SNAPSHOT'])
            return summary
        try:
            evidence = snapshot(rows, data.get('market'), quality, symbol=symbol, interval=interval,
                                epoch=data.get('stream_epoch'), generation=data.get('generation'), revision=data.get('data_revision'))
        except (KeyError, TypeError, ValueError, OverflowError):
            summary.update(state='INVALID_INPUT', reasons=['INVALID_DATA_SNAPSHOT'])
            return summary
        proof = evidence.view()
        if proof != data.get('data_proof'):
            summary.update(state='WAITING_FOR_DATA', reasons=['DATA_PROOF_MISMATCH'])
            return summary
        grid = grid_info(rows, interval)
        closed = [r for r in rows if r['closed']]
        used = rows if include_open else closed
        step = INTERVALS[interval]//1000
        gaps = [dict(start=left['time']+step, end=right['time']-step,
                     missing_count=(right['time']-left['time'])//step-1)
                for left, right in zip(rows, rows[1:]) if right['time']-left['time'] > step]
        timing = data.get('timing', {})
        stale = data.get('transport_state') != 'LIVE' or timing.get('state') != 'FRESH'
        summary.update(available_count=len(rows), available_closed_count=len(closed),
                       warmup_available_closed_bars=grid['warmup_available_closed_bars'], missing_ranges=gaps,
                       last_closed_candle=closed[-1]['time'] if closed else None,
                       open_candle_present=any(not r['closed'] for r in rows),
                       open_candle_used=include_open and any(not r['closed'] for r in rows),
                       stale=stale, source_clock=timing, proof=proof,
                       consumed_range=dict(first_time=used[0]['time'], last_time=used[-1]['time'], count=len(used)) if used else None,
                       consumed_data_hash=digest([r for r in evidence.payload()['rows'] if include_open or r['closed']]))
        if stale:
            summary.update(state='STALE', reasons=[timing.get('reason') or 'TRANSPORT_NOT_LIVE'])
        elif not grid['valid'] or gaps or quality.get('state') != 'OK' or proof['state'] != 'VERIFIED':
            summary.update(state='WAITING_FOR_DATA', reasons=proof['blocked_reasons'] or ['DATA_NOT_VERIFIED'])
        elif grid['warmup_available_closed_bars'] < required:
            summary.update(state='WARMUP', reasons=['INSUFFICIENT_CLOSED_HISTORY'])
        else:
            summary.update(state='READY', reasons=[])
        return summary

    def read(self, workspace_id, *, symbol=None, interval=None, source=SOURCE, environment=ENVIRONMENT,
             product='USD-M', price_type='LAST_PRICE', required_closed_bars=2, include_open=False,
             limit=100, offset=0, expected_context_id=None, ui_session_id=None, _capture=False, _deadline=None):
        identifier(workspace_id)
        if ui_session_id is not None:identifier(ui_session_id)
        if dict(source=source, environment=environment, product=product, price_type=price_type) != IDENTITY:
            raise ContextSourceMismatch()
        if (type(required_closed_bars) is not int or not 1 <= required_closed_bars <= 499
                or type(limit) is not int or not 1 <= limit <= 200 or type(offset) is not int or not 0 <= offset <= 1000000
                or type(include_open) is not bool or offset and expected_context_id is None
                or expected_context_id is not None and (not isinstance(expected_context_id, str) or len(expected_context_id) != 64)):
            raise DrawingError()
        deadline = min(self.monotonic()+2, _deadline) if _deadline is not None else self.monotonic()+2
        for attempt in range(3):
            if self.monotonic() > deadline:
                raise ContextReadLimit()
            before = self._persistent(workspace_id, symbol, interval, limit, offset, deadline)
            actual_symbol, actual_interval = before['symbol'], before['interval']
            data = self._data(actual_symbol, actual_interval)
            readiness = self._readiness(data, actual_symbol, actual_interval, required_closed_bars, include_open)
            after = self._persistent(workspace_id, symbol, interval, limit, offset, deadline)
            data_after = self._data(actual_symbol, actual_interval)
            if before['stamp'] != after['stamp'] or self._data_stamp(data) != self._data_stamp(data_after):
                continue
            if self.monotonic() > deadline:
                raise ContextReadLimit()
            context_id = digest(dict(owner=self.owner, workspace_id=workspace_id, persistent=before['stamp'],
                                     data=self._data_stamp(data), required=required_closed_bars, include_open=include_open,
                                     readiness_state=readiness['state']))
            if expected_context_id is not None and context_id != expected_context_id:
                raise ContextChanged()
            ui=(self.ui_sessions.show(workspace_id,ui_session_id) if self.ui_sessions is not None and ui_session_id is not None
                else dict(state='UI_UNAVAILABLE',reason='UI_SESSION_NOT_SELECTED' if ui_session_id is None else 'UI_BRIDGE_UNAVAILABLE'))
            ui['consistency_scope']='INDEPENDENT_TRANSIENT_SESSION_NOT_MARKET_SNAPSHOT'
            ui['market_matches_requested']=(ui['snapshot']['market']==dict(IDENTITY,symbol=actual_symbol,interval=actual_interval)) if 'snapshot' in ui else None
            result = dict(schema_version=SCHEMA_VERSION, calculation_version=CALCULATION_VERSION,
                        context_id=context_id, server_utc=datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(),
                        time_units=dict(candle_time='UTC_SECONDS', server_utc='ISO8601_UTC', source_clock_durations='MILLISECONDS'),
                        market=dict(IDENTITY, symbol=actual_symbol, interval=actual_interval),
                        workspace=before['workspace'], objects=before['drawings'], indicators=before['indicators'],
                        persistent_view=before['profile'], derived=dict(readiness=readiness),
                        data_identity=dict(stream_epoch=data.get('stream_epoch'), generation=data.get('generation'),
                                           sequence=data.get('sequence'), data_revision=data.get('data_revision'))
                                      if data and readiness['state'] not in ('SOURCE_MISMATCH', 'INVALID_INPUT') else None,
                        object_interval_binding='NOT_BOUND_TO_INTERVAL',
                        ui=ui, ui_context_id=ui.get('ui_context_id'),
                        pagination=dict(limit=limit, offset=offset, total=before['count'],
                                        next_offset=offset+limit if offset+limit < before['count'] else None,
                                        continuation_requires_context_id=True),
                        consistency=dict(state='VERIFIED_BEFORE_AFTER', attempts=attempt+1), order_authority=False)
            return (result, data) if _capture else result
        raise ContextChanged()
