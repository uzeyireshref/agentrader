import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { useIndicatorConfig } from "../src/useIndicatorConfig";
import { defaultVwapIndicators } from "../src/indicatorConfig";

for (const reloadFirst of [false, true])
  test(`indicator save retires overlapping reload (reload first: ${reloadFirst})`, async () => {
    const dom = new JSDOM("<html><body><div id='root'></div></body></html>");
    Object.assign(globalThis, {
      window: dom.window,
      document: dom.window.document,
      IS_REACT_ACT_ENVIRONMENT: true,
    });
    const originalFetch = globalThis.fetch;
    const requests: {
      method: string;
      resolve: (response: Response) => void;
    }[] = [];
    globalThis.fetch = async (_url, init) =>
      new Promise<Response>((resolve) =>
        requests.push({ method: init?.method ?? "GET", resolve }),
      );
    const root = createRoot(document.getElementById("root")!);
    let config!: ReturnType<typeof useIndicatorConfig>;
    function Component() {
      config = useIndicatorConfig();
      return null;
    }
    const before = {
      schema: "chart-indicators/4",
      workspace_id: "main",
      revision: 0,
      indicators: defaultVwapIndicators(),
    };
    const respond = (index: number, value: unknown) =>
      requests[index].resolve(new Response(JSON.stringify(value)));
    try {
      await act(async () => root.render(<Component />));
      await act(async () => respond(0, before));
      assert.equal(config.ready, true);
      const draft = structuredClone(before.indicators);
      draft[0].period++;
      const saved = {
        ...before,
        revision: 1,
        indicators: structuredClone(draft),
      };
      saved.indicators[0].revision++;
      let reload!: Promise<boolean | undefined>, save!: Promise<boolean>;
      // Both actions can use the same committed render before React updates ready.
      await act(async () => {
        reload = config.reload();
        save = config.save(draft);
      });
      assert.deepEqual(
        requests.map((r) => r.method),
        ["GET", "GET", "PUT"],
      );
      if (reloadFirst)
        await act(async () => {
          respond(1, before);
          assert.equal(await reload, false);
        });
      await act(async () => {
        respond(2, saved);
        assert.equal(await save, true);
      });
      assert.equal(config.ready, true);
      assert.equal(config.revision, 1);
      if (!reloadFirst)
        await act(async () => {
          respond(1, before);
          assert.equal(await reload, false);
        });
      assert.equal(config.revision, 1);
      assert.equal(config.items[0].period, draft[0].period);
      assert.equal(config.ready, true);
      assert.equal(config.busy, false);
    } finally {
      await act(async () => root.unmount());
      globalThis.fetch = originalFetch;
      dom.window.close();
    }
  });
