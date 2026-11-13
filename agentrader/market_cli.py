"""Canlı piyasa okuma → SQLite → tekrar üretilebilir JSON/Markdown analiz raporu."""
import argparse
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .analysis import daily_volume, timeframe_report, iso
from .exchange import ExchangeError
from .market_data import PublicMarket, CandleStore, LIVE_URL, SOURCE, INTERVALS, fetch_candles


def build_report(client, store, symbols, bars=300, as_of_ms=None, offline=False):
    if offline:
        if as_of_ms is None:
            latest = store.db.execute('SELECT MAX(as_of_ms) FROM analysis_runs').fetchone()[0]
            if latest is None:
                raise ValueError('Önbellekte rapor yok; önce canlı veri okuyun veya --as-of belirtin.')
            as_of_ms = latest
        info = None
    else:
        server_time = client.get('/fapi/v1/time')['serverTime']
        as_of_ms = server_time if as_of_ms is None else as_of_ms
        if as_of_ms > server_time:
            raise ValueError('Gelecekteki veri zamanı istenemez.')
        info = {s['symbol']: s for s in client.get('/fapi/v1/exchangeInfo')['symbols']}
    if type(as_of_ms) is not int or as_of_ms <= 0:
        raise ValueError('Analiz zamanı pozitif milisaniye olmalı.')
    report = {'schema_version': 1, 'analysis_version': 'basic-mtf-v1', 'source': SOURCE,
              'market': 'Binance USD-M USDT perpetual / işlem fiyatı', 'base_url': LIVE_URL,
              'as_of_ms': as_of_ms, 'as_of_utc': iso(as_of_ms),
              'display_time_baku': datetime.fromtimestamp(as_of_ms / 1000, timezone.utc).astimezone(
                  timezone(timedelta(hours=4))).isoformat(),
              'mode': 'cached' if offline else 'live_public_read_only',
              'trade_execution_enabled': False, 'requested_bars': bars, 'symbols': {},
              'limitations': ['Bu rapor emir veya onaylanmış işlem planı oluşturmaz.',
                              'Hacim para girişi değildir; zincir üstü akış verisi bu sürümde yok.',
                              'Haber/AI, dominans, TOTAL3, destek/direnç ve formasyon analizi henüz eklenmedi.',
                              'REST anlık görüntüsüdür; sürekli WebSocket izleyici değildir.',
                              'EMA SMA ile, RSI/ATR Wilder yöntemiyle başlatılır; geçmiş penceresi sonuçları etkiler.']}
    inputs = {}
    for symbol in symbols:
        valid = (info is None or (symbol in info and info[symbol].get('status') == 'TRADING'
                 and info[symbol].get('contractType') == 'PERPETUAL' and info[symbol].get('quoteAsset') == 'USDT'))
        item = {'timeframes': {}, 'assessment': 'BEKLE', 'supporting': [], 'opposing': [], 'missing': []}
        inputs[symbol] = {}
        daily_rows = []
        for interval in INTERVALS:
            try:
                if not valid:
                    raise ValueError('İşleme açık USDT perpetual sözleşmesi doğrulanamadı.')
                if offline:
                    rows = store.load(symbol, interval, as_of_ms, bars)
                    extra = {'source_mode': 'cached'}
                else:
                    rows, quality = fetch_candles(client, symbol, interval, as_of_ms, bars)
                    revisions = store.save(symbol, interval, rows, server_time)
                    extra = quality | {'closed_revisions_observed': revisions, 'source_mode': 'live'}
                result = timeframe_report(rows, interval, as_of_ms, bars)
                result['ingestion'] = extra
                item['timeframes'][interval] = result
                inputs[symbol][interval] = [r for r in rows if r[6] < as_of_ms][-bars:]
                if interval == '1d':
                    daily_rows = rows
                if result['status'] != 'OK':
                    item['missing'].append(interval + ': ' + '; '.join(result['issues']))
                    continue
                f = result['features']
                text = f"{interval}: trend {f['trend']}, RSI14 {f['rsi14_wilder']:.1f}."
                (item['supporting'] if f['trend'] == 'UP' else item['opposing']).append(text)
                ratio = f['quote_volume_ratio']
                if ratio is not None and ratio < 1:
                    item['opposing'].append(f'{interval}: hacim önceki 20 mum ortalamasının altında ({ratio:.2f}x).')
                if f['rsi14_wilder'] > 70 or f['rsi14_wilder'] < 30:
                    item['opposing'].append(f'{interval}: RSI uç bölgede; tek başına giriş/çıkış sebebi sayılmaz.')
            except (ValueError, ExchangeError) as exc:
                if isinstance(exc, ExchangeError) and exc.http_status in (418, 429, 451):
                    raise
                item['timeframes'][interval] = {'status': 'ERROR', 'issues': [str(exc)], 'features': None}
                item['missing'].append(interval + ': ' + str(exc))
                inputs[symbol][interval] = []
        item['daily_volume'] = daily_volume(daily_rows, as_of_ms)
        item['summary'] = 'Temel göstergeler hesaplandı; giriş stratejisi ve onay akışı bu rapora bağlı değil.'
        if item['missing']:
            item['summary'] = 'Eksik/eski veri var; değerlendirme tamamlanamadı. Emir üretilmedi.'
        item['status'] = 'INCOMPLETE' if item['missing'] else 'OK'
        report['symbols'][symbol] = item
    report['status'] = 'OK' if all(s['status'] == 'OK' for s in report['symbols'].values()) else 'INCOMPLETE'
    run_id = store.record_run(as_of_ms, inputs, report)
    report['run_id'] = run_id
    return report


def markdown_report(report):
    lines = ['# Temel çoklu zaman dilimi analizi', '',
             f"Veri zamanı: {report['as_of_utc']} (UTC); Bakü: {report['display_time_baku']}", '',
             f"Kaynak: {report['market']} — {report['mode']}", '',
             '**Salt okunur rapor. Emir gönderimi kapalı.**', '']
    for symbol, item in report['symbols'].items():
        lines.extend([f'## {symbol}', '', f"Durum: {item['status']} — {item['assessment']}", '', item['summary'], '',
                      '| Zaman | Son kapanış | EMA20 | EMA50 | RSI14 | ATR14 | Hacim oranı | Trend / durum |',
                      '|---|---:|---:|---:|---:|---:|---:|---|'])
        for interval, data in item['timeframes'].items():
            f = data.get('features')
            if f:
                ratio = f"{f['quote_volume_ratio']:.2f}x" if f['quote_volume_ratio'] is not None else '—'
                lines.append(f"| {interval} | {f['close']:.4f} | {f['ema20']:.4f} | {f['ema50']:.4f} | {f['rsi14_wilder']:.2f} | {f['atr14_wilder']:.4f} | {ratio} | {f['trend']} |")
            else:
                lines.append(f"| {interval} | — | — | — | — | — | — | {data['status']} |")
        for title, key in [('Yükselişi destekleyen bulgular', 'supporting'), ('Karşı bulgular ve belirsizlikler', 'opposing'), ('Eksik veya eski mum verileri', 'missing')]:
            lines.extend(['', f'### {title}', ''])
            lines.extend(['- ' + text for text in item[key]] or ['- Yok / bu sürümde ek bulgu üretilmedi.'])
        volume = item['daily_volume']
        lines.extend(['', '### Son 7 tamamlanmış UTC gününün hacmi', '',
                      '| Gün | Toplam hacim (USDT) | Taker alış (USDT) | Taker satış (USDT) |', '|---|---:|---:|---:|'])
        for day in volume['days']:
            lines.append(f"| {day['date_utc']} | {day['quote_volume_usdt'] or 'Eksik'} | {day['taker_buy_quote_usdt'] or 'Eksik'} | {day['taker_sell_quote_usdt'] or 'Eksik'} |")
        change = f"%{volume['change_pct']:.2f}" if volume['change_pct'] is not None else 'hesaplanamadı'
        lines.extend(['', f"Önceki 7 güne göre hacim değişimi: {change}.", '', volume['note'], ''])
    lines.extend(['## Sınırlar', ''] + ['- ' + text for text in report['limitations']])
    lines.extend(['', f"Girdi özeti: `{report['input_hash']}`", ''])
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='agentrader market', description='Anahtarsız canlı veri ve temel analiz; emir göndermez')
    parser.add_argument('command', choices=['report'])
    parser.add_argument('--symbols', nargs='+', default=['BTCUSDT', 'ETHUSDT'])
    parser.add_argument('--bars', type=int, default=300)
    parser.add_argument('--as-of', help='Saat dilimli ISO-8601 veri kesim zamanı; UTC veya +04:00')
    parser.add_argument('--offline', action='store_true', help='Yalnızca ayrı piyasa önbelleğini oku')
    parser.add_argument('--database', default='data/market.sqlite3')
    parser.add_argument('--output-dir', default='reports')
    args = parser.parse_args(argv)
    symbols = list(dict.fromkeys(s.upper() for s in args.symbols))
    if not 60 <= args.bars <= 5000 or not 1 <= len(symbols) <= 10 or any(not re.fullmatch(r'[A-Z0-9]{2,20}USDT', s) for s in symbols):
        parser.error('60–5000 mum ve 1–10 geçerli USDT sembolü gerekli.')
    try:
        cutoff = None
        if args.as_of:
            date = datetime.fromisoformat(args.as_of.replace('Z', '+00:00'))
            if date.tzinfo is None:
                raise ValueError('--as-of saat dilimi içermeli.')
            cutoff = int(date.timestamp() * 1000)
        store = CandleStore(Path(args.database))
        try:
            report = build_report(None if args.offline else PublicMarket(), store, symbols, args.bars, cutoff, args.offline)
        finally:
            store.close()
        output = Path(args.output_dir)
        output.mkdir(parents=True, exist_ok=True)
        stem = f"market-{report['as_of_ms']}-{report['run_id']}"
        text = markdown_report(report)
        for name in (stem, 'market-latest'):
            (output / (name + '.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
            (output / (name + '.md')).write_text(text, encoding='utf-8')
        print(json.dumps({'status': report['status'], 'as_of_utc': report['as_of_utc'], 'symbols': symbols,
                          'report': str(output / (stem + '.md')), 'json': str(output / (stem + '.json')),
                          'input_hash': report['input_hash'], 'trade_execution_enabled': False}, ensure_ascii=False, indent=2))
        return 0 if report['status'] == 'OK' else 1
    except (ValueError, OSError, ExchangeError) as exc:
        logging.error('%s', exc)
        return 1
