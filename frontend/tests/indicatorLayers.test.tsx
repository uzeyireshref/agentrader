import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { act } from "react";
import { createRoot } from "react-dom/client";
import type { IChartApi } from "lightweight-charts";
import { useIndicatorLayers } from "../src/useIndicatorLayers";
import {
  defaultVwapIndicators,
  type IndicatorConfig,
} from "../src/indicatorConfig";
import { initialState, type Candle } from "../src/types";

const dom = new JSDOM("<html><body></body></html>");
Object.assign(globalThis, {
  window: dom.window,
  document: dom.window.document,
  IS_REACT_ACT_ENVIRONMENT: true,
});
function chartFixture() {
  const active = new Set<object>(),
    removed: object[] = [],
    writes: unknown[] = [];
  let paneCount = 2;
  const api = {
    panes: () => Array.from({ length: paneCount }, () => ({})),
    addSeries: (_type: unknown, _options: unknown, pane = 0) => {
      paneCount = Math.max(paneCount, pane + 1);
      const line = {
        priceScale: () => ({ applyOptions: () => {} }),
        getPane: () => ({ paneIndex: () => pane, setStretchFactor: () => {} }),
        createPriceLine: () => {},
        setData: (data: unknown) => writes.push(data),
        update: (data: unknown) => writes.push(data),
      };
      active.add(line);
      return line;
    },
    removeSeries: (line: object) => {
      assert.equal(active.delete(line), true, "series removed exactly once");
      removed.push(line);
    },
  };
  return { api: api as unknown as IChartApi, active, removed, writes };
}

test("indicator layers create only enabled series, replace changed groups and release ownership on unmount", async () => {
  const fake = chartFixture(),
    chart = { current: fake.api },
    host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  let layers: ReturnType<typeof useIndicatorLayers> | undefined;
  function Component({ items }: { items: IndicatorConfig[] }) {
    layers = useIndicatorLayers(chart, items, () => {});
    return null;
  }
  const configs = defaultVwapIndicators().map((c) => ({ ...c, enabled: true }));
  try {
    await act(async () => root.render(<Component items={configs} />));
    assert.equal(fake.active.size, 13);
    const rsi = layers!.rsiSeries.current,
      atr = layers!.atrSeries.current;
    await act(async () =>
      root.render(
        <Component
          items={configs.map((c) =>
            c.kind === "EMA" ? { ...c, period: c.period + 1 } : c,
          )}
        />,
      ),
    );
    assert.equal(fake.removed.length, 2);
    assert.equal(layers!.rsiSeries.current, rsi);
    assert.equal(layers!.atrSeries.current, atr);
    await act(async () =>
      root.render(
        <Component items={configs.map((c) => ({ ...c, enabled: false }))} />,
      ),
    );
    assert.equal(fake.active.size, 0);
    assert.equal(layers!.rsiSeries.current, null);
    assert.equal(layers!.atrSeries.current, null);
    assert.equal(layers!.macdLine.current, null);
    await act(async () => root.unmount());
    assert.equal(fake.removed.length, 15);
  } finally {
    host.remove();
  }
});

test("enabled writers preserve incremental output and full recovery mode without network access", async () => {
  const fake = chartFixture(),
    chart = { current: fake.api },
    host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  let layers: ReturnType<typeof useIndicatorLayers> | undefined;
  const configs = defaultVwapIndicators().map((c) => ({
    ...c,
    enabled: c.kind === "EMA",
  }));
  function Component() {
    layers = useIndicatorLayers(chart, configs, () => {});
    return null;
  }
  try {
    await act(async () => root.render(<Component />));
    const candles = Array.from({ length: 70 }, (_, i) => ({
      time: 1800000000 + i * 60,
      close_time: (1800000000 + i * 60) * 1000 + 59999,
      open: 100,
      high: 110,
      low: 90,
      close: 100 + (i % 3),
      volume: 10,
      quote_volume: 1000,
      closed: i < 69,
    })) as Candle[];
    const view = { ...initialState("BTCUSDT", "1m"), candles };
    layers!.write(view, true);
    assert.equal(fake.writes.length, 2);
    const count = fake.writes.length;
    layers!.write(view, false);
    assert.equal(fake.writes.length, count);
    layers!.write(view, true);
    assert.equal(fake.writes.length, count + 2);
  } finally {
    await act(async () => root.unmount());
    host.remove();
  }
});
