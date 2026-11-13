"""Foreground session monitor. Restart resumes a session; it never opens one."""
import time
from .exchange import ExchangeError


def monitor_session(runner, session_id, *, execute=False, iterations=1, interval=5,
                    sleep=time.sleep):
    if type(iterations) is not int or iterations < 0:
        raise ValueError('Tur sayısı sıfır veya pozitif tam sayı olmalı.')
    if type(interval) is not int or not 1 <= interval <= 60:
        raise ValueError('İzleme aralığı 1–60 saniye olmalı.')
    turn = 0
    while iterations == 0 or turn < iterations:
        stopped=_requested_service_stop(runner,session_id,execute)
        if stopped is not None:
            yield stopped
            return
        # Exceptions are deliberate stop conditions: do not turn an uncertain
        # mutation into an automatic retry loop. The saved session survives.
        result = runner.manage(session_id, execute=execute)
        turn += 1
        yield result | {'monitor_turn': turn, 'observed_at_ms': int(time.time()*1000)}
        if result['state'] == 'CLOSED' or (iterations and turn >= iterations):
            return
        sleep(interval)


def supervise_session(runner, session_id, *, emit, execute=False, iterations=1,
                      interval=5, drain_on_exit=False, sleep=time.sleep, user_stream=None,
                      notification_queue=None, notification_chat=None):
    """A finite/interrupting grid monitor drains entries before giving up control."""
    last=None
    original_output=emit
    def emit(report):
        runner.store.runtime_health(session_id,report,time.time())
        original_output(report)
    if notification_queue is not None:
        from .notifications import chat_id,queue_session_report
        notification_chat=chat_id(notification_chat)
        original_emit=emit
        previous=None
        def emit(report):
            nonlocal previous
            signature=tuple(str(report.get(k,'')) for k in ('state','quantity','position','positions'))
            routine=report.get('state') in ('MANAGING','GRID_RUNNING','GRID_DRAINING','NEUTRAL_RUNNING','NEUTRAL_DRAINING')
            if not routine or signature!=previous:
                queue_session_report(notification_queue,notification_chat,report)
            previous=signature
            original_emit(report)
    try:
        monitor = monitor_session if user_stream is None else stream_monitor_session
        stream_options = {} if user_stream is None else {'stream': user_stream}
        for result in monitor(runner,session_id,execute=execute,iterations=iterations,
                              interval=interval,sleep=sleep,**stream_options):
            last=result;emit(result)
    except KeyboardInterrupt:
        if execute and drain_on_exit:
            try:emit(runner.stop(session_id,close_position=False,execute=True))
            except (ValueError,ExchangeError,OSError):
                emit({'state':'GRID_STOP_INCOMPLETE','session_id':session_id,
                      'message':'Giriş iptalleri doğrulanamadı; mevcut oturumu devralın.'})
        raise
    if execute and drain_on_exit and last and last['state']!='CLOSED' and not last.get('service_stopped'):
        last=runner.stop(session_id,close_position=False,execute=True)
        emit(last)
    return last


def stream_monitor_session(runner, session_id, *, stream, execute=False,
                           iterations=1, interval=5, sleep=time.sleep):
    """Connection recovery never retries runner mutations.

    One thread owns the socket, SQLite and runner. Events are reconciliation
    hints, not fills applied to inventory. Every connection generation needs
    a successful read-only ownership check before execute=True is allowed.
    """
    from .user_stream import StreamUnavailable, StreamProtocolError
    if type(iterations) is not int or iterations < 0:
        raise ValueError('Tur sayısı sıfır veya pozitif tam sayı olmalı.')
    if type(interval) is not int or not 1 <= interval <= 60:
        raise ValueError('İzleme aralığı 1–60 saniye olmalı.')
    turn, reconnects = 0, 0
    connected = False
    pending_event = runner.store.pending_stream_observation(session_id)
    try:
        while iterations == 0 or turn < iterations:
            stopped=_requested_service_stop(runner,session_id,execute)
            if stopped is not None:
                yield stopped
                return
            if not connected:
                try:
                    info = stream.connect()
                except StreamUnavailable:
                    reconnects += 1
                    if reconnects > 3:
                        raise StreamUnavailable('Kullanıcı akışı yeniden bağlantı sınırına ulaştı.') from None
                    yield {'state': 'STREAM_RECONNECTING', 'session_id': session_id,
                           'attempt': reconnects, 'executed': False}
                    sleep(min(2**(reconnects-1), 4))
                    continue
                yield info | {'session_id': session_id, 'executed': False}
                # Deliberately outside the stream-retry exception handler.
                # Ownership mismatch or uncertain order state must stop here.
                if pending_event is not None:
                    baseline = _stream_event_barrier(runner, session_id, pending_event, sleep=sleep)
                    runner.store.clear_stream_observation(session_id, pending_event['event_id'])
                    pending_event = None
                else:
                    baseline = runner.manage(session_id, execute=False)
                if baseline['state'] == 'CLOSED':
                    yield baseline | {'stream_generation': stream.generation}
                    return
                yield {'state': 'STREAM_RECONCILED', 'session_id': session_id,
                       'account_state': baseline['state'], 'generation': stream.generation,
                       'executed': False}
                connected = True
            try:
                stream.maintain()
            except StreamUnavailable:
                stream.close()
                connected = False
                reconnects += 1
                if reconnects > 3:
                    raise StreamUnavailable('Kullanıcı akışı kesinti sınırına ulaştı.') from None
                yield {'state': 'STREAM_DISCONNECTED', 'session_id': session_id,
                       'attempt': reconnects, 'executed': False}
                sleep(min(2**(reconnects-1), 4))
                continue
            if pending_event is not None:
                # WebSocket can lead REST. Never act on an older REST view
                # while a known fill/cancellation is still missing there.
                baseline = _stream_event_barrier(runner, session_id, pending_event, sleep=sleep)
                runner.store.clear_stream_observation(session_id, pending_event['event_id'])
                pending_event = None
                if baseline['state'] == 'CLOSED':
                    yield baseline | {'stream_generation': stream.generation}
                    return
            # All runner mutations still perform their existing REST ownership,
            # risk, native protection and approval checks.
            result = runner.manage(session_id, execute=execute)
            turn += 1
            yield result | {'monitor_turn': turn, 'stream_generation': stream.generation,
                            'observed_at_ms': int(time.time()*1000)}
            if result['state'] == 'CLOSED' or (iterations and turn >= iterations):
                return
            try:
                event = stream.wait(interval)
            except StreamUnavailable:
                stream.close()
                connected = False
                reconnects += 1
                if reconnects > 3:
                    raise StreamUnavailable('Kullanıcı akışı kesinti sınırına ulaştı.') from None
                yield {'state': 'STREAM_DISCONNECTED', 'session_id': session_id,
                       'attempt': reconnects, 'executed': False}
                sleep(min(2**(reconnects-1), 4))
                continue
            if event is not None:
                runner.store.save_stream_observation(session_id, event)
                pending_event = event
                yield {'state': 'STREAM_EVENT', 'session_id': session_id,
                       'kind': event['kind'], 'event_id': event['event_id'], 'executed': False}
    except (StreamUnavailable, StreamProtocolError):
        runner.store.halt('Kullanıcı akışı doğrulanamadı; yönetim yeniden uzlaştırılmalı.')
        raise
    finally:
        stream.close()


def _stream_event_barrier(runner, session_id, event, *, sleep):
    from .risk import number
    from .user_stream import StreamProtocolError
    if event['kind'] == 'ORDER_TRADE_UPDATE':
        terminal = {'FILLED', 'CANCELED', 'EXPIRED', 'EXPIRED_IN_MATCH', 'REJECTED'}
        for attempt in range(3):
            try:
                order = runner.x.get('/fapi/v1/order',
                                     {'symbol': event['symbol'], 'origClientOrderId': event['client_id']})
            except ExchangeError as exc:
                if exc.code != -2013:
                    raise
                order = None
            if order is not None:
                if (order.get('symbol') != event['symbol'] or
                        order.get('clientOrderId') != event['client_id'] or
                        order.get('orderId') != event['order_id'] or order.get('side') != event['side']):
                    raise StreamProtocolError('WebSocket/REST emir kimliği uyuşmuyor.')
                if (number(order.get('executedQty', '-1')) >= number(event['cumulative_filled']) and
                        (event['status'] not in terminal or order.get('status') in terminal)):
                    break
            if attempt == 2:
                raise StreamProtocolError('WebSocket olayı REST üzerinde henüz doğrulanamadı; yürütme durdu.')
            sleep(1)
    elif event['kind'] == 'ALGO_UPDATE':
        ranks = {'NEW': 0, 'TRIGGERING': 1, 'TRIGGERED': 2,
                 'FINISHED': 3, 'CANCELED': 3, 'EXPIRED': 3, 'REJECTED': 3}
        for attempt in range(3):
            try:
                order = runner.x.get('/fapi/v1/algoOrder', {'clientAlgoId': event['client_algo_id']})
            except ExchangeError as exc:
                if exc.code != -2013:
                    raise
                order = None
            if order is not None:
                if (order.get('clientAlgoId') != event['client_algo_id'] or
                        order.get('symbol') != event['symbol'] or order.get('side') != event['side'] or
                        order.get('algoId') != event['algo_id']):
                    raise StreamProtocolError('WebSocket/REST koşullu emir kimliği uyuşmuyor.')
                child_matches = (event['actual_order_id'] is None or
                                 str(order.get('actualOrderId')) == str(event['actual_order_id']))
                if (ranks.get(order.get('algoStatus'), -1) >= ranks[event['algo_status']] and child_matches and
                        number(order.get('actualQty') or '0') >= number(event['actual_filled'])):
                    break
            if attempt == 2:
                raise StreamProtocolError('WebSocket koşullu emir olayı REST üzerinde doğrulanamadı.')
            sleep(1)
    # Balance/config/algo events are hints only; do not invent a complete
    # account snapshot from their partial payload. Re-run all ownership checks.
    return runner.manage(session_id, execute=False)


def _requested_service_stop(runner,session_id,execute):
    request=runner.store.service_stop_request(session_id)
    if not isinstance(request,dict) or request.get('requested') is not True:return None
    if request.get('engine') in ('grid-v2','neutral-v2'):
        report=runner.stop(session_id,close_position=False,execute=execute)
    else:
        report=runner.manage(session_id,execute=execute)
        if report['state']!='CLOSED':
            report=report|{'account_state':report['state'],'state':'MONITOR_STOPPED'}
    if execute:
        with runner.store.db:
            runner.store.db.execute('DELETE FROM control WHERE name=?',('service_stop:'+session_id,))
    return report|{'service_stopped':True}
