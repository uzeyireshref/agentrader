import { performance } from "node:perf_hooks";
import { writeFileSync } from "node:fs";
import { IndicatorCalculator } from "../src/indicatorCalculator";
import { indicatorSeries, multiIndicator } from "../src/indicators";
import { defaultVwapIndicators } from "../src/indicatorConfig";
import type { Candle } from "../src/types";
const samples = [];
for (const count of [300, 1000, 4000]) {
  const rows = Array.from({ length: count }, (_, i) => ({
    time: 1800000000 + i * 60,
    close_time: (1800000000 + (i + 1) * 60) * 1000 - 1,
    open: 90000,
    high: 90020,
    low: 89980,
    close: 90000 + (i % 10),
    volume: 10,
    quote_volume: 900000,
    closed: i < count - 1,
  })) as Candle[];
  const configs = defaultVwapIndicators().slice(0, 7),
    cache = new IndicatorCalculator();
  const run = (cached: boolean) => {
    const times = [];
    for (let t = 0; t < 51; t++) {
      rows[rows.length - 1] = { ...rows.at(-1)!, close: 90000 + (t % 10) };
      const start = performance.now();
      for (const c of configs)
        if (c.kind === "MACD" || c.kind === "BB") {
          if (cached) cache.multi(rows, c, "1m");
          else multiIndicator(rows, c, "1m");
        } else {
          if (cached) cache.series(rows, c, "1m");
          else indicatorSeries(rows, c, "1m");
        }
      if (t) times.push(performance.now() - start);
    }
    times.sort((a, b) => a - b);
    return { median_ms: times[25], max_ms: times.at(-1) };
  };
  const append = (cached: boolean) => {
    const calculator = new IndicatorCalculator(),
      times = [];
    let history = rows.map((r) => ({ ...r, closed: true }));
    for (let t = 0; t < 31; t++) {
      const last = history.at(-1)!;
      history = [
        ...history,
        {
          ...last,
          time: last.time + 60,
          close_time: last.close_time + 60000,
          close: 90000 + (t % 10),
          closed: false,
        },
      ];
      const start = performance.now();
      for (const c of configs)
        if (c.kind === "MACD" || c.kind === "BB") {
          if (cached) calculator.multi(history, c, "1m");
          else multiIndicator(history, c, "1m");
        } else {
          if (cached) calculator.series(history, c, "1m");
          else indicatorSeries(history, c, "1m");
        }
      if (t) times.push(performance.now() - start);
      history[history.length - 1] = { ...history.at(-1)!, closed: true };
    }
    times.sort((a, b) => a - b);
    return { median_ms: times[15], max_ms: times.at(-1) };
  };
  samples.push({
    candles: count,
    reference: run(false),
    cached: run(true),
    closed_append: { reference: append(false), cached: append(true) },
  });
}
const text = JSON.stringify(
  {
    schema: "indicator-cpu-benchmark/1",
    scope: "Pure indicator CPU; not browser FPS",
    samples,
  },
  null,
  2,
);
if (process.argv[2]) writeFileSync(process.argv[2], text + "\n");
console.log(text);
