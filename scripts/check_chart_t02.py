"""T02 current production App/native numeric parity; isolated synthetic market."""
import hashlib
import json
from fractions import Fraction
from measure_chart_interactions import main, INSPECT, ROOT
from agentrader.drawings.calculations import query


def checks(page, sockets, rows, result):
    result.update(date='2026-11-10', task='T02', checks=[])
    def read(expr):
        return page.evaluate(INSPECT[:INSPECT.index('return view?')] + 'return (' + expr + ');' + '}')
    drawings = []
    for kind, prices, times in [
        ('trend', ['170', '180'], [rows[235]['time'] + 450, rows[270]['time']]),
        ('fibonacci', ['210', '190'], [rows[270]['time'], rows[210]['time']]),
    ]:
        drawings.append({'drawing_id': 't02-' + kind, 'workspace_id': 'main', 'revision': 1,
                         'deleted': False, 'updated_at': 0,
                         'geometry': {'kind': kind, 'symbol': 'BTCUSDT', 'price_source': 'LAST_PRICE',
                                      'label': kind, 'anchors': [dict(time=t, price=p) for t, p in zip(times, prices)]}})
    page.route('**/api/workspaces/main/drawings?**', lambda route: route.fulfill(json={'drawings': drawings}))
    page.get_by_role('button', name='Sunucudan yenile', exact=True).click()
    page.wait_for_timeout(150)
    read('chart.timeScale().setVisibleLogicalRange({from:200,to:280})')
    read('series.priceScale().setVisibleRange({from:140,to:220})')
    page.wait_for_timeout(200)
    fib = drawings[1]['geometry']
    for ratio in ['0', '0.236', '0.382', '0.5', '0.618', '0.786', '1']:
        value = query(fib, 'level', time=rows[250]['time'], ratio=ratio)['value']
        exact = Fraction(int(value['numerator']), int(value['denominator']))
        expected = read('series.priceToCoordinate(' + repr(float(exact)) + ')')
        actual = float(page.locator('[data-drawing="t02-fibonacci"] .shape-line[data-fib="' + ratio + '"]').get_attribute('y1'))
        hit = page.locator('[data-drawing="t02-fibonacci"] .hit-line[data-fib="' + ratio + '"]')
        assert float(hit.get_attribute('y1')) == actual
        assert float(hit.get_attribute('y2')) == actual
        error = abs(actual - expected)
        assert error <= 1e-7, (ratio, actual, expected)
        result['checks'].append({'name': 'reverse_fib_' + ratio, 'error_css_px': error, 'passed': True})
    trend = drawings[0]['geometry']
    at = rows[250]['time']
    value = query(trend, 'priceAt', time=at, times=[r['time'] for r in rows], interval='15m')['value']
    exact = Fraction(int(value['numerator']), int(value['denominator']))
    point = read('({x:chart.timeScale().timeToCoordinate(' + str(at) + '),y:series.priceToCoordinate(' + repr(float(exact)) + ')})')
    line = page.locator('[data-drawing="t02-trend"] .shape-trend')
    x1, x2, y1, y2 = [float(line.get_attribute(a)) for a in ('x1', 'x2', 'y1', 'y2')]
    actual = y1 + (y2 - y1) * (point['x'] - x1) / (x2 - x1)
    assert abs(actual - point['y']) <= 1e-7
    result['checks'].append({'name': 'fractional_anchor_trend_native_parity', 'error_css_px': abs(actual - point['y']), 'passed': True})
    page.screenshot(path=str(ROOT/'reports/chart-t02-native-20261110.png'), full_page=True)
    result['assets'] = {str(p.relative_to(ROOT/'agentrader/web_assets')): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted((ROOT/'agentrader/web_assets').rglob('*')) if p.is_file()}
    result['scope'] = 'Current production App; native numeric parity, not physical device/raster acceptance'


if __name__ == '__main__':
    raise SystemExit(main(checks, 'chart-t02-browser-20261110.json', production=True))
