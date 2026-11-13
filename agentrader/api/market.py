"""Public market HTTP/WebSocket endpoints; same local boundary as the API."""
import asyncio
import contextlib
import re

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from ..chart_market import InvalidMarket, MarketUnavailable
from ..market_feed import FeedUnavailable
from ..higher_timeframe import higher_context


def market_router(market, hub):
    router = APIRouter()

    @router.get('/api/markets')
    def markets():
        return market.catalog()

    @router.get('/api/candles')
    def candles(symbol: str = 'BTCUSDT', interval: str = '15m',
                limit: int = Query(300, ge=2, le=499), end_time: int | None = Query(None, ge=0, le=32503680000000)):
        return market.history(symbol, interval, limit=limit, end_time=end_time)

    @router.get('/api/higher-context')
    def higher(symbol: str, base_interval: str, interval: str,
               reference_time: int = Query(..., ge=1, le=32503680000000)):
        return higher_context(market, symbol, base_interval, interval, reference_time)

    @router.websocket('/api/market-stream')
    async def stream(ws: WebSocket):
        host = ws.headers.get('host', '')
        origin = ws.headers.get('origin')
        if (not re.fullmatch(r'(?:127\.0\.0\.1|localhost)(?::[0-9]{1,5})?', host)
                or origin is None or origin != 'http://' + host):
            await ws.close(code=1008)
            return
        symbol, interval = ws.query_params.get('symbol', ''), ws.query_params.get('interval', '')
        await ws.accept()
        feed = None
        tasks = []
        try:
            feed = await asyncio.to_thread(hub.acquire, symbol, interval)

            async def send():
                generation, sequence, status, sent_at, epoch = -1, -1, None, 0, None
                while True:
                    packet = feed.state.packet(generation, epoch)
                    now = asyncio.get_running_loop().time()
                    if packet.get('stream_epoch') != epoch or packet['sequence'] != sequence or packet['status'] != status or now - sent_at >= 2:
                        await ws.send_json(packet)
                        generation, sequence, status = packet['generation'], packet['sequence'], packet['status']
                        epoch = packet.get('stream_epoch')
                        sent_at = now
                    await asyncio.sleep(.25)

            async def receive():
                while True:
                    message = await ws.receive_text()
                    if message != 'ping':
                        await ws.close(code=1008)
                        return

            tasks = [asyncio.create_task(send()), asyncio.create_task(receive())]
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        except (InvalidMarket, MarketUnavailable, FeedUnavailable):
            with contextlib.suppress(Exception):
                await ws.send_json({'type': 'error', 'code': 'MARKET_UNAVAILABLE', 'symbol': symbol, 'interval': interval})
                await ws.close(code=1013)
        except (WebSocketDisconnect, OSError, RuntimeError, asyncio.CancelledError):
            pass
        finally:
            try:
                for task in tasks:
                    task.cancel()
                if tasks:
                    with contextlib.suppress(asyncio.CancelledError):
                        await asyncio.gather(*tasks, return_exceptions=True)
            finally:
                if feed is not None:
                    hub.release(feed)

    return router
