import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { act, lazy, useState } from "react";
import { createRoot } from "react-dom/client";
import DeferredPanel from "../src/DeferredPanel";
const dom = new JSDOM("<html><body></body></html>");
Object.assign(globalThis, {
  window: dom.window,
  document: dom.window.document,
  IS_REACT_ACT_ENVIRONMENT: true,
});

test("optional chunk loads only when opened; cancel keeps the surrounding chart mounted", async () => {
  let loads = 0,
    resolve: (value: { default: () => React.JSX.Element }) => void = () => {};
  const Panel = lazy(() => {
    loads++;
    return new Promise<{default:()=>React.JSX.Element}>((resolvePromise) => {
      resolve = resolvePromise;
    });
  });
  const host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  function App() {
    const [open, setOpen] = useState(false);
    return (
      <>
        <input aria-label="chart draft" defaultValue="saved" />
        <button onClick={() => setOpen(true)}>Open</button>
        {open && (
          <DeferredPanel onClose={() => setOpen(false)}>
            <Panel />
          </DeferredPanel>
        )}
      </>
    );
  }
  try {
    await act(async () => root.render(<App />));
    assert.equal(loads, 0);
    const input = host.querySelector("input");
    await act(async () => host.querySelector("button")!.click());
    assert.equal(loads, 1);
    assert.match(host.textContent!, /Panel yükleniyor/);
    await act(async () =>
      host
        .querySelector("[role=status] button")!
        .dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true })),
    );
    await act(async () => resolve({ default: () => <div>Loaded panel</div> }));
    assert.equal(host.querySelector("input"), input);
    assert.equal(host.textContent!.includes("Loaded panel"), false);
    await act(async () => host.querySelector("button")!.click());
    assert.match(host.textContent!, /Loaded panel/);
    assert.equal(loads, 1);
  } finally {
    await act(async () => root.unmount());
    host.remove();
  }
});

test("failed optional module is contained and can be closed without losing chart state", async () => {
  const host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  const errors: unknown[] = [];
  const prior = console.error;
  console.error = (...args) => errors.push(args);
  function Broken(): React.JSX.Element {
    throw Error("synthetic chunk failure");
  }
  let closed = false;
  try {
    await act(async () =>
      root.render(
        <>
          <input defaultValue="saved" />
          <DeferredPanel
            onClose={() => {
              closed = true;
            }}
          >
            <Broken />
          </DeferredPanel>
        </>,
      ),
    );
    assert.match(
      host.querySelector("[role=alert]")!.textContent!,
      /Panel yüklenemedi/,
    );
    assert.equal(host.querySelector("input")?.value, "saved");
    await act(async () => host.querySelector("button")!.click());
    assert.equal(closed, true);
  } finally {
    console.error = prior;
    await act(async () => root.unmount());
    host.remove();
  }
});
