import { test } from "node:test";
import assert from "node:assert/strict";
import { IndicatorCalculator } from "../src/indicatorCalculator";
import { indicatorSeries, multiIndicator } from "../src/indicators";
import {
  defaultVwapIndicators,
  type IndicatorConfig,
} from "../src/indicatorConfig";
import type { Candle } from "../src/types";
const candles = (n: number): Candle[] =>
  Array.from({ length: n }, (_, i) => ({
    time: 1800000000 + i * 60,
    close_time: (1800000000 + (i + 1) * 60) * 1000 - 1,
    open: 90000 + (i % 13),
    high: 90020 + (i % 13),
    low: 89980 + (i % 13),
    close: 90000 + ((i * 7) % 13),
    volume: 10,
    quote_volume: 900000,
    closed: true,
  }));
test("closed prefix cache preserves exact reference results through ticks, corrections, prepend, trim and config changes", () => {
  const cache = new IndicatorCalculator();
  let rows = candles(150);
  const configs = defaultVwapIndicators().filter(
    (c) => !c.kind.includes("VWAP"),
  );
  const check = (c: IndicatorConfig) =>
    assert.deepEqual(
      ["MACD", "BB"].includes(c.kind)
        ? cache.multi(rows, c, "1m")
        : cache.series(rows, c, "1m", "BTCUSDT"),
      ["MACD", "BB"].includes(c.kind)
        ? multiIndicator(rows, c, "1m")
        : indicatorSeries(rows, c, "1m", "BTCUSDT"),
    );
  for (let tick = 0; tick < 20; tick++) {
    rows = rows.map((r, i) =>
      i === rows.length - 1 ? { ...r, close: 90000 + (tick % 10) } : r,
    );
    for (const c of configs) {
      check(c);
      if (c.kind === "MACD")
        check({
          ...c,
          params: { ...c.params, signal_type: "SMA", oscillator_type: "SMA" },
        });
      if (c.kind === "BB")
        check({ ...c, params: { ...c.params, basis_type: "EMA" } });
    }
  }
  rows[3].close = 90004;
  configs.forEach(check);
  rows = candles(160);
  configs.forEach(check);
  rows = rows.slice(10);
  configs.forEach(check);
  for (const c of configs) check({ ...c, period: c.period + 2 });
});
test("warmup and invalid grids retain full-reference behavior", () => {
  const cache = new IndicatorCalculator();
  for (const n of [0, 1, 14, 20, 27])
    for (const c of defaultVwapIndicators().slice(0, 7)) {
      const rows = candles(n);
      assert.deepEqual(
        cache.series(rows, c, "1m"),
        indicatorSeries(rows, c, "1m"),
      );
    }
  const rows = candles(100);
  rows[4].time++;
  assert.deepEqual(cache.series(rows, defaultVwapIndicators()[0], "1m"), []);
});

test("successive closed candles preserve every reference value including SMA MACD and Bollinger", () => {
  const all = candles(180);
  const configs = defaultVwapIndicators()
    .slice(0, 7)
    .flatMap<IndicatorConfig>((c) =>
      c.kind === "MACD"
        ? [
            c,
            {
              ...c,
              params: {
                ...c.params,
                signal_type: "SMA",
                oscillator_type: "SMA",
              },
            },
          ]
        : c.kind === "BB"
          ? [
              c,
              {
                ...c,
                params: { ...c.params, basis_type: "EMA" },
              },
            ]
          : [c],
    );
  const caches = configs.map(() => new IndicatorCalculator());
  for (let n = 70; n <= all.length; n++) {
    const rows = structuredClone(all.slice(0, n));
    rows.at(-1)!.closed = false;
    for (let tick = 0; tick < 3; tick++) {
      rows.at(-1)!.close = 90000 + tick;
      for (const [index, c] of configs.entries())
        assert.deepEqual(
          c.kind === "MACD" || c.kind === "BB"
            ? caches[index].multi(rows, c, "1m")
            : caches[index].series(rows, c, "1m"),
          c.kind === "MACD" || c.kind === "BB"
            ? multiIndicator(rows, c, "1m")
            : indicatorSeries(rows, c, "1m"),
        );
    }
  }
});

test("subtract/add rolling sums cannot replace the existing numerical contract", () => {
  const values = [1e16, 1, 1, 1];
  const initial = values.slice(0, 3).reduce((sum, value) => sum + value, 0);
  const rolling = (initial - values[0] + values[3]) / 3;
  const reference = values.slice(1).reduce((sum, value) => sum + value, 0) / 3;
  assert.notEqual(rolling, reference);
  const cache = new IndicatorCalculator();
  const config = { ...defaultVwapIndicators()[3], period: 3 };
  for (let n = 70; n < 90; n++) {
    const rows = candles(n).map((row, i) => ({
      ...row,
      open: values[i % 4],
      close: values[i % 4],
      high: 1e16,
      low: 1,
    }));
    assert.deepEqual(
      cache.series(rows, config, "1m"),
      indicatorSeries(rows, config, "1m"),
    );
  }
});
