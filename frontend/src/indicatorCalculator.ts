import { steps } from "./evidence";
import {
  sourceValue,
  indicatorSeries,
  indicatorGrid,
  multiIndicator,
  smoothPoints,
  histogramState,
  type IndicatorPoint,
} from "./indicators";
import type { IndicatorConfig, PriceSource } from "./indicatorConfig";
import type { Candle, Interval } from "./types";

/** Cache closed prefixes only. Any correction, prepend, trim or config change reseeds. */
export class IndicatorCalculator {
  private multiEntries = new Map<
    string,
    {
      key: string;
      prefix: Candle[];
      data: Record<string, IndicatorPoint[]>;
      fast: number;
      slow: number;
    }
  >();
  private entries = new Map<
    string,
    {
      key: string;
      prefix: Candle[];
      points: IndicatorPoint[];
      gain: number;
      loss: number;
    }
  >();
  series(
    rows: Candle[],
    config: IndicatorConfig,
    interval: Interval,
    symbol = "",
  ): IndicatorPoint[] {
    if (!["EMA", "RSI", "ATR", "SMA"].includes(config.kind))
      return indicatorSeries(rows, config, interval, symbol);
    if (!indicatorGrid(rows, interval)) return [];
    if (rows.length <= config.period + 1)
      return indicatorSeries(rows, config, interval, symbol);
    const key = JSON.stringify([config, interval, symbol]);
    const prefix = rows.slice(0, -1);
    const stamps = prefix;
    let entry = this.entries.get(config.indicator_id);
    if (
      entry &&
      entry.key === key &&
      prefix.length === entry.prefix.length + 1 &&
      samePrefix(prefix.slice(0, -1), entry.prefix)
    ) {
      // Commit the newly closed row using exactly the open-row arithmetic.
      const points = this.series(prefix, config, interval, symbol);
      if (config.kind === "RSI") {
        const change =
          sourceValue(prefix.at(-1)!, config.source as PriceSource) -
          sourceValue(prefix.at(-2)!, config.source as PriceSource);
        entry.gain =
          (entry.gain * (config.period - 1) + Math.max(0, change)) /
          config.period;
        entry.loss =
          (entry.loss * (config.period - 1) + Math.max(0, -change)) /
          config.period;
      }
      entry.points = points;
      entry.prefix = [...entry.prefix, { ...prefix.at(-1)! }];
    }
    if (
      !entry ||
      entry.key !== key ||
      entry.prefix.length !== stamps.length ||
      !samePrefix(stamps, entry.prefix)
    ) {
      const points = indicatorSeries(prefix, config, interval, symbol);
      let gain = 0,
        loss = 0;
      if (config.kind === "RSI")
        for (let i = 1; i < prefix.length; i++) {
          const change =
            sourceValue(prefix[i], config.source as PriceSource) -
            sourceValue(prefix[i - 1], config.source as PriceSource);
          const g = Math.max(0, change),
            l = Math.max(0, -change),
            p = config.period;
          if (i <= p) {
            gain += g;
            loss += l;
            if (i === p) {
              gain /= p;
              loss /= p;
            }
          } else {
            gain = (gain * (p - 1) + g) / p;
            loss = (loss * (p - 1) + l) / p;
          }
        }
      entry = {
        key,
        prefix: stamps.map((r) => ({ ...r })),
        points,
        gain,
        loss,
      };
      this.entries.set(config.indicator_id, entry);
    }
    const last = rows.at(-1)!,
      previous = rows.at(-2)!,
      period = config.period;
    const old = entry.points.at(-1)?.value;
    if (old === undefined)
      return indicatorSeries(rows, config, interval, symbol);
    let value: number;
    if (config.kind === "EMA") {
      const alpha = 2 / (period + 1);
      value =
        sourceValue(last, config.source as PriceSource) * alpha +
        old * (1 - alpha);
    } else if (config.kind === "ATR") {
      const tr = Math.max(
        last.high - last.low,
        Math.abs(last.high - previous.close),
        Math.abs(last.low - previous.close),
      );
      value = (old * (period - 1) + tr) / period;
    } else if (config.kind === "RSI") {
      const change =
        sourceValue(last, config.source as PriceSource) -
        sourceValue(previous, config.source as PriceSource);
      const gain = (entry.gain * (period - 1) + Math.max(0, change)) / period,
        loss = (entry.loss * (period - 1) + Math.max(0, -change)) / period;
      value =
        loss === 0
          ? gain === 0 && config.calculation_version === 1
            ? 50
            : 100
          : 100 - 100 / (1 + gain / loss);
    } else {
      let total = 0;
      for (let i = rows.length - period; i < rows.length; i++)
        total += sourceValue(rows[i], config.source as PriceSource);
      value = total / period;
    }
    return [...entry.points, { time: last.time, value }];
  }
  multi(
    rows: Candle[],
    config: IndicatorConfig,
    interval: Interval,
  ): Record<string, IndicatorPoint[]> {
    if (
      !indicatorGrid(rows, interval) ||
      rows.length <=
        config.period + Number(config.params?.signal_period ?? 1) + 1
    )
      return multiIndicator(rows, config, interval);
    const key = JSON.stringify([config, interval]),
      prefix = rows.slice(0, -1),
      p = config.params!;
    let entry = this.multiEntries.get(config.indicator_id);
    if (
      entry &&
      entry.key === key &&
      prefix.length === entry.prefix.length + 1 &&
      samePrefix(prefix.slice(0, -1), entry.prefix)
    ) {
      const data = this.multi(prefix, config, interval);
      if (config.kind === "MACD") {
        const advance = (period: number, old: number) => {
          if (p.oscillator_type === "EMA")
            return (
              (sourceValue(prefix.at(-1)!, config.source as PriceSource) * 2) /
                (period + 1) +
              old * (1 - 2 / (period + 1))
            );
          let total = 0;
          for (let i = prefix.length - period; i < prefix.length; i++)
            total += sourceValue(prefix[i], config.source as PriceSource);
          return total / period;
        };
        entry.fast = advance(Number(p.fast_period), entry.fast);
        entry.slow = advance(config.period, entry.slow);
      }
      entry.data = data;
      entry.prefix = [...entry.prefix, { ...prefix.at(-1)! }];
    }
    if (!entry || entry.key !== key || !samePrefix(prefix, entry.prefix)) {
      const points = prefix.map((r) => ({
        time: r.time,
        value: sourceValue(r, config.source as PriceSource),
      }));
      entry = {
        key,
        prefix: prefix.map((r) => ({ ...r })),
        data: multiIndicator(prefix, config, interval),
        fast:
          config.kind === "MACD"
            ? smoothPoints(
                points,
                Number(p.fast_period),
                String(p.oscillator_type),
              ).at(-1)!.value
            : 0,
        slow:
          config.kind === "MACD"
            ? smoothPoints(points, config.period, String(p.oscillator_type)).at(
                -1,
              )!.value
            : 0,
      };
      this.multiEntries.set(config.indicator_id, entry);
    }
    const last = rows.at(-1)!,
      price = sourceValue(last, config.source as PriceSource);
    const average = (period: number) => {
      let sum = 0;
      for (let i = rows.length - period; i < rows.length; i++)
        sum += sourceValue(rows[i], config.source as PriceSource);
      return sum / period;
    };
    if (config.kind === "BB") {
      const mean = average(config.period);
      let variance = 0;
      for (let i = rows.length - config.period; i < rows.length; i++)
        variance +=
          (sourceValue(rows[i], config.source as PriceSource) - mean) ** 2;
      const deviation =
        Math.sqrt(variance / config.period) * Number(p.deviation);
      const basis =
        p.basis_type === "EMA"
          ? (price * 2) / (config.period + 1) +
            entry.data.basis.at(-1)!.value * (1 - 2 / (config.period + 1))
          : mean;
      const time = last.time + Number(p.offset) * steps[interval];
      return {
        basis: [...entry.data.basis, { time, value: basis }],
        upper: [...entry.data.upper, { time, value: basis + deviation }],
        lower: [...entry.data.lower, { time, value: basis - deviation }],
      };
    }
    const smooth = (period: number, old: number) =>
      p.oscillator_type === "EMA"
        ? (price * 2) / (period + 1) + old * (1 - 2 / (period + 1))
        : average(period);
    const value =
        smooth(Number(p.fast_period), entry.fast) -
        smooth(config.period, entry.slow),
      period = Number(p.signal_period);
    if (!entry.data.signal.length)
      return multiIndicator(rows, config, interval);
    let signal: number;
    if (p.signal_type === "EMA")
      signal =
        (value * 2) / (period + 1) +
        entry.data.signal.at(-1)!.value * (1 - 2 / (period + 1));
    else {
      let sum = 0;
      const data = entry.data.macd;
      for (let i = data.length - period + 1; i < data.length; i++)
        sum += data[i].value;
      signal = (sum + value) / period;
    }
    const histogram = value - signal,
      previous = entry.data.histogram.at(-1)?.value ?? 0,
      time = last.time;
    return {
      macd: [...entry.data.macd, { time, value }],
      signal: [...entry.data.signal, { time, value: signal }],
      histogram: [
        ...entry.data.histogram,
        {
          time,
          value: histogram,
          color: config.style!.colors[histogramState(histogram, previous)],
        },
      ],
    };
  }
}

function samePrefix(a: Candle[], b: Candle[]): boolean {
  return (
    a.length === b.length &&
    a.every((r, i) => {
      const p = b[i];
      return (
        r.time === p.time &&
        r.open === p.open &&
        r.high === p.high &&
        r.low === p.low &&
        r.close === p.close &&
        r.volume === p.volume &&
        r.quote_volume === p.quote_volume &&
        r.closed === p.closed &&
        r.close_time === p.close_time
      );
    })
  );
}
