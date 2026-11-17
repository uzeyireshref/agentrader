import { useEffect, useRef } from "react";

/** Read refreshes only; never retry or replay a financial submission here. */
export function useVisiblePolling(
  load: () => Promise<void>,
  fail: (error: unknown) => void,
  interval = 5000,
  enabled = true,
): void {
  const callbacks = useRef({ load, fail });
  callbacks.current = { load, fail };
  useEffect(() => {
    if (!enabled) return;
    let active = true,
      running = false;
    const poll = async () => {
      if (!active || running || document.visibilityState === "hidden") return;
      running = true;
      try {
        await callbacks.current.load();
      } catch (error) {
        if (active) callbacks.current.fail(error);
      } finally {
        running = false;
      }
    };
    const visible = () => {
      if (document.visibilityState !== "hidden") void poll();
    };
    void poll();
    const timer = setInterval(() => {
      void poll();
    }, interval);
    document.addEventListener("visibilitychange", visible);
    return () => {
      active = false;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [interval, enabled]);
}
