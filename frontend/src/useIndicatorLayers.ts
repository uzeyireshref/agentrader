import { useEffect, useRef, type RefObject } from "react";
import {
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { IndicatorCalculator } from "./indicatorCalculator";
import { LineSeriesWriter } from "./lineWriter";
import { vwapSeries, vwapRenderPlot, type VwapPlotPoint } from "./vwap";
import type { IndicatorConfig } from "./indicatorConfig";
import type { ChartState } from "./types";

/** Series ownership stays here; pane layout and data transport stay with their owners. */
export function useIndicatorLayers(
  chart: RefObject<IChartApi | null>,
  items: IndicatorConfig[],
  changed: () => void,
) {
  const [
    fast,
    slow,
    oscillator,
    simple,
    volatility,
    convergence,
    bands,
    sessionVwap,
    anchoredVwap,
  ] = items;
  const showEma = fast.enabled || slow.enabled,
    showRsi = oscillator.enabled;
  const emaKey = JSON.stringify([fast, slow]),
    rsiKey = JSON.stringify(oscillator),
    smaKey = JSON.stringify(simple),
    atrKey = JSON.stringify(volatility),
    macdKey = JSON.stringify(convergence),
    bbKey = JSON.stringify(bands),
    sessionVwapKey = JSON.stringify(sessionVwap),
    anchoredVwapKey = JSON.stringify(anchoredVwap);
  const sessionVwapWriter = useRef<LineSeriesWriter<VwapPlotPoint> | null>(
      null,
    ),
    anchoredVwapWriter = useRef<LineSeriesWriter<VwapPlotPoint> | null>(null);
  const macdLine = useRef<ISeriesApi<"Line"> | null>(null),
    macdWriters = useRef<LineSeriesWriter[]>([]),
    macdHistogram = useRef<LineSeriesWriter | null>(null),
    bbWriters = useRef<LineSeriesWriter[]>([]);
  const smaWriter = useRef<LineSeriesWriter | null>(null),
    atrWriter = useRef<LineSeriesWriter | null>(null),
    atrSeries = useRef<ISeriesApi<"Line"> | null>(null);
  const emaWriters = useRef<(LineSeriesWriter | null)[]>([]),
    rsiWriter = useRef<LineSeriesWriter | null>(null),
    rsiSeries = useRef<ISeriesApi<"Line"> | null>(null);
  const calculator = useRef(new IndicatorCalculator());
  const lineWriter = (line: ISeriesApi<"Line">) =>
    new LineSeriesWriter({
      setData: (points) =>
        line.setData(
          points.map((p) => ({ ...p, time: p.time as UTCTimestamp })),
        ),
      update: (p, historical) =>
        line.update({ ...p, time: p.time as UTCTimestamp }, historical),
    });
  useEffect(() => {
    const instance = chart.current;
    if (!instance || !showEma) return;
    const lines = [fast, slow].map((c, i) =>
      c.enabled
        ? instance.addSeries(LineSeries, {
            color: i === 0 ? "#d6a849" : "#7e9ed4",
            lineWidth: 1,
            title: "EMA " + c.period,
            priceLineVisible: false,
            lastValueVisible: false,
          })
        : null,
    );
    emaWriters.current = lines.map((line) => (line ? lineWriter(line) : null));
    return () => {
      if (chart.current === instance)
        for (const line of lines) if (line) instance.removeSeries(line);
      emaWriters.current = [];
    };
  }, [emaKey]);
  useEffect(() => {
    const instance = chart.current;
    if (!instance || !showRsi) return;
    const line = instance.addSeries(
      LineSeries,
      {
        color: "#9d7ce0",
        lineWidth: 1,
        title: "RSI " + oscillator.period,
        priceScaleId: "right",
        priceLineVisible: false,
        priceFormat: { type: "custom", formatter: (v: number) => v.toFixed(1) },
        autoscaleInfoProvider: () => ({
          priceRange: { minValue: 0, maxValue: 100 },
        }),
      },
      instance.panes().length,
    );
    line.priceScale().applyOptions({ mode: 0 });
    for (const value of [30, 70])
      line.createPriceLine({
        price: value,
        color: "#7a8494",
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: "",
      });
    rsiSeries.current = line;
    rsiWriter.current = lineWriter(line);
    changed();
    return () => {
      if (chart.current === instance) instance.removeSeries(line);
      rsiSeries.current = null;
      rsiWriter.current = null;
    };
  }, [rsiKey]);
  useEffect(() => {
    const instance = chart.current;
    if (!instance || !simple.enabled) return;
    const line = instance.addSeries(LineSeries, {
      color: "#e18e65",
      lineWidth: 1,
      title: "SMA " + simple.period,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    smaWriter.current = lineWriter(line);
    return () => {
      if (chart.current === instance) instance.removeSeries(line);
      smaWriter.current = null;
    };
  }, [smaKey]);
  useEffect(() => {
    const instance = chart.current;
    if (!instance || !volatility.enabled) return;
    const line = instance.addSeries(
      LineSeries,
      {
        color: "#58b5ca",
        lineWidth: 1,
        title: "ATR " + volatility.period,
        priceScaleId: "right",
        priceLineVisible: false,
        priceFormat: { type: "price", precision: 4, minMove: 0.0001 },
      },
      instance.panes().length,
    );
    line.priceScale().applyOptions({ mode: 0 });
    line.getPane().setStretchFactor(1.5);
    atrSeries.current = line;
    atrWriter.current = lineWriter(line);
    changed();
    return () => {
      if (chart.current === instance) instance.removeSeries(line);
      atrSeries.current = null;
      atrWriter.current = null;
    };
  }, [atrKey]);
  useEffect(() => {
    const instance = chart.current;
    if (!instance || !convergence.enabled) return;
    const style = convergence.style!,
      hist = instance.addSeries(
        HistogramSeries,
        {
          title: "MACD Histogram",
          priceScaleId: "right",
          priceLineVisible: false,
          priceFormat: { type: "price", precision: 4, minMove: 0.0001 },
        },
        instance.panes().length,
      );
    hist.priceScale().applyOptions({ mode: 0 });
    const lines = ["macd", "signal"].map((key, i) =>
      instance.addSeries(
        LineSeries,
        {
          title: i ? "MACD Sinyal" : "MACD",
          color: style.colors[key],
          lineWidth: style.line_width,
          priceScaleId: "right",
          priceLineVisible: false,
        },
        hist.getPane().paneIndex(),
      ),
    );
    lines[0].createPriceLine({
      price: 0,
      color: "#78858b",
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: false,
      title: "",
    });
    hist.getPane().setStretchFactor(1.5);
    macdLine.current = lines[0];
    macdWriters.current = lines.map(lineWriter);
    macdHistogram.current = new LineSeriesWriter({
      setData: (points) =>
        hist.setData(
          points.map((p) => ({ ...p, time: p.time as UTCTimestamp })),
        ),
      update: (p, historical) =>
        hist.update({ ...p, time: p.time as UTCTimestamp }, historical),
    });
    changed();
    return () => {
      if (chart.current === instance) {
        for (const line of lines) instance.removeSeries(line);
        instance.removeSeries(hist);
      }
      macdLine.current = null;
      macdWriters.current = [];
      macdHistogram.current = null;
    };
  }, [macdKey]);
  useEffect(() => {
    const instance = chart.current;
    if (!instance || !bands.enabled) return;
    const style = bands.style!,
      lines = ["basis", "upper", "lower"].map((key, i) =>
        instance.addSeries(LineSeries, {
          title: "BB " + ["Orta", "Üst", "Alt"][i],
          color: style.colors[key],
          lineWidth: style.line_width,
          lineStyle: i === 0 ? 2 : 0,
          priceLineVisible: false,
          lastValueVisible: false,
        }),
      );
    bbWriters.current = lines.map(lineWriter);
    return () => {
      if (chart.current === instance)
        for (const line of lines) instance.removeSeries(line);
      bbWriters.current = [];
    };
  }, [bbKey]);
  useEffect(() => {
    const instance = chart.current;
    if (!instance || !sessionVwap.enabled) return;
    const line = instance.addSeries(LineSeries, {
      title: "Seans VWAP",
      color: sessionVwap.style!.colors.value,
      lineWidth: sessionVwap.style!.line_width,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    sessionVwapWriter.current = new LineSeriesWriter<VwapPlotPoint>({
      setData: (points) =>
        line.setData(
          points.map((p) => ({ ...p, time: p.time as UTCTimestamp })),
        ),
      update: (p, historical) =>
        line.update({ ...p, time: p.time as UTCTimestamp }, historical),
    });
    return () => {
      if (chart.current === instance) instance.removeSeries(line);
      sessionVwapWriter.current = null;
    };
  }, [sessionVwapKey]);
  useEffect(() => {
    const instance = chart.current;
    if (!instance || !anchoredVwap.enabled) return;
    const line = instance.addSeries(LineSeries, {
      title: "Anchored VWAP",
      color: anchoredVwap.style!.colors.value,
      lineWidth: anchoredVwap.style!.line_width,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    anchoredVwapWriter.current = new LineSeriesWriter<VwapPlotPoint>({
      setData: (points) =>
        line.setData(
          points.map((p) => ({ ...p, time: p.time as UTCTimestamp })),
        ),
      update: (p, historical) =>
        line.update({ ...p, time: p.time as UTCTimestamp }, historical),
    });
    return () => {
      if (chart.current === instance) instance.removeSeries(line);
      anchoredVwapWriter.current = null;
    };
  }, [anchoredVwapKey]);

  function write(view: ChartState, full: boolean) {
    if (fast.enabled)
      emaWriters.current[0]?.write(
        calculator.current.series(view.candles, fast, view.interval),
        full,
      );
    if (slow.enabled)
      emaWriters.current[1]?.write(
        calculator.current.series(view.candles, slow, view.interval),
        full,
      );
    if (showRsi)
      rsiWriter.current?.write(
        calculator.current.series(view.candles, oscillator, view.interval),
        full,
      );
    if (simple.enabled)
      smaWriter.current?.write(
        calculator.current.series(view.candles, simple, view.interval),
        full,
      );
    if (volatility.enabled)
      atrWriter.current?.write(
        calculator.current.series(view.candles, volatility, view.interval),
        full,
      );
    if (convergence.enabled) {
      const data = calculator.current.multi(
        view.candles,
        convergence,
        view.interval,
      );
      macdWriters.current[0]?.write(data.macd, full);
      macdWriters.current[1]?.write(data.signal, full);
      macdHistogram.current?.write(data.histogram, full);
    }
    if (bands.enabled) {
      const data = calculator.current.multi(view.candles, bands, view.interval);
      ["basis", "upper", "lower"].forEach((key, i) =>
        bbWriters.current[i]?.write(data[key], full),
      );
    }
    if (sessionVwap.enabled)
      sessionVwapWriter.current?.write(
        vwapRenderPlot(
          vwapSeries(view.candles, sessionVwap, view.interval, view.symbol)
            .plot,
        ),
        full,
      );
    if (anchoredVwap.enabled)
      anchoredVwapWriter.current?.write(
        vwapRenderPlot(
          vwapSeries(view.candles, anchoredVwap, view.interval, view.symbol)
            .plot,
        ),
        full,
      );
  }
  return { rsiSeries, atrSeries, macdLine, write };
}
