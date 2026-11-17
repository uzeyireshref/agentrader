import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { act } from "react";
import { createRoot } from "react-dom/client";
import WorkspaceTemplates from "../src/WorkspaceTemplates";
import {
  defaultChartView,
  templateIndicators,
  type ChartProfile,
  type ChartTemplate,
} from "../src/chartProfiles";
import { defaultVwapIndicators } from "../src/indicatorConfig";
import type { useChartProfiles } from "../src/useChartProfiles";
import type { Drawing } from "../src/drawings";

test("workspace writes wait for a loaded profile while reload and close remain available", async () => {
  const dom = new JSDOM("<html><body><div id='root'></div></body></html>");
  Object.assign(globalThis, {
    window: dom.window,
    document: dom.window.document,
    HTMLElement: dom.window.HTMLElement,
    IS_REACT_ACT_ENVIRONMENT: true,
  });
  Object.assign(dom.window.HTMLDialogElement.prototype, {
    showModal() {},
    close() {},
  });
  const originalFetch = globalThis.fetch;
  const template: ChartTemplate = {
    template_id: "sample",
    revision: 1,
    name: "Sample",
    body: {
      schema: "chart-template/1",
      view: defaultChartView(),
      indicators: templateIndicators(defaultVwapIndicators()),
      drawing_defaults: {},
    },
  };
  globalThis.fetch = async (url) =>
    new Response(
      JSON.stringify(
        String(url).includes("/templates/")
          ? template
          : {
              templates: [
                { template_id: "sample", revision: 1, name: "Sample" },
              ],
            },
      ),
    );
  const root = createRoot(document.getElementById("root")!);
  let writes = 0,
    reloads = 0,
    closes = 0;
  const profile: ChartProfile = {
    workspace_id: "main",
    revision: 0,
    body: {
      schema: "chart-profile/1",
      view: defaultChartView(),
      drawing_defaults: {},
    },
  };
  const profiles: ReturnType<typeof useChartProfiles> = {
    profile: null,
    ready: false,
    busy: false,
    error: "Profil yüklenemedi",
    reload: async () => true,
    saveProfile: async () => {
      writes++;
      return true;
    },
    saveTemplate: async () => {
      writes++;
      return null;
    },
    restore: async () => null,
    accept: () => {},
  };
  const selected: Drawing = {
    drawing_id: "line",
    workspace_id: "main",
    revision: 1,
    deleted: false,
    updated_at: 1,
    geometry: {
      kind: "horizontal",
      symbol: "BTCUSDT",
      price_source: "LAST_PRICE",
      label: "",
      anchors: [{ time: 1800000000, price: "100" }],
    },
  };
  let indicatorsReady = true;
  const render = () =>
    root.render(
      <WorkspaceTemplates
        profiles={{ ...profiles }}
        indicators={defaultVwapIndicators()}
        indicatorsReady={indicatorsReady}
        captureView={defaultChartView}
        selected={selected}
        canRestore={true}
        externalError=""
        onRestore={async () => true}
        onReload={async () => {
          reloads++;
          return true;
        }}
        onClose={() => {
          closes++;
        }}
      />,
    );
  const button = (label: string) => {
    const found = [...document.querySelectorAll("button")].find(
      (b) => b.textContent === label,
    );
    assert.ok(found, label);
    return found;
  };
  try {
    await act(async () => render());
    await act(async () => {
      const select = document.querySelector<HTMLSelectElement>(
        '[aria-label="Kayıtlı şablon"]',
      )!;
      select.value = "sample";
      select.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
    });
    assert.equal(button("Yeni şablon kaydet").disabled, true);
    assert.equal(button("Yeni sürüm kaydet").disabled, true);
    assert.equal(button("Seçili sürümü uygula").disabled, true);
    for (const label of [
      "Çalışma alanını kaydet",
      "Seçili aracı varsayılan yap",
    ])
      assert.equal(button(label).disabled, true, label);
    await act(async () => button("Son kayıtları yükle").click());
    await act(async () => button("Kapat").click());
    assert.equal(reloads, 1);
    assert.equal(closes, 1);
    assert.equal(writes, 0);
    // A retained older profile is not sufficient after a failed reload.
    profiles.profile = profile;
    await act(async () => render());
    assert.equal(button("Çalışma alanını kaydet").disabled, true);
    profiles.ready = true;
    await act(async () => render());
    assert.equal(button("Çalışma alanını kaydet").disabled, false);
    await act(async () => button("Çalışma alanını kaydet").click());
    await act(async () => button("Seçili aracı varsayılan yap").click());
    assert.equal(writes, 2);
    assert.equal(button("Yeni şablon kaydet").disabled, false);
    assert.equal(button("Yeni sürüm kaydet").disabled, false);
    indicatorsReady = false;
    await act(async () => render());
    assert.equal(button("Yeni şablon kaydet").disabled, true);
    assert.equal(button("Yeni sürüm kaydet").disabled, true);
    assert.equal(button("Çalışma alanını kaydet").disabled, false);
    await act(async () => button("Yeni şablon kaydet").click());
    assert.equal(writes, 2);
  } finally {
    await act(async () => root.unmount());
    globalThis.fetch = originalFetch;
    dom.window.close();
  }
});
