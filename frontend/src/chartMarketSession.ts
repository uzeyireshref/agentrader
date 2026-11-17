import { historyQuality } from "./historyQuality";
import type { HistoryLoadState } from "./historyLoad";
import { isDemoMarket } from "./marketEnvironment";
import { RenderRecovery, applyRenderedPacket } from "./renderRecovery";
import { checkFreshness } from "./freshness";
import {
  beginStream,
  initialState,
  mergeHistory,
  type Candle,
  type ChartState,
  type Interval,
  type Packet,
} from "./types";

export type MarketSocket = {
  onmessage: ((event: { data: string }) => void) | null;
  onclose: (() => void) | null;
  onerror: (() => void) | null;
  close: () => void;
};
export type MarketSessionEnvironment = {
  fetch: typeof fetch;
  socket: (url: string) => MarketSocket;
  origin: string;
  now: () => number;
  later: (callback: () => void, delay: number) => ReturnType<typeof setTimeout>;
  cancelLater: (timer: ReturnType<typeof setTimeout>) => void;
  every: (
    callback: () => void,
    delay: number,
  ) => ReturnType<typeof setInterval>;
  cancelEvery: (timer: ReturnType<typeof setInterval>) => void;
};
export type MarketSessionOptions = {
  symbol: string;
  interval: Interval;
  state: { current: ChartState };
  publish: (state: ChartState) => void;
  paint: (state: ChartState, full: boolean) => void;
  // A viewport snapshot becomes a commit callback only after a successful paint.
  beforeHistory: () => (added: number) => void;
  historyBusy: (busy: boolean) => void;
  historyError: (error: boolean) => void;
  hasMore: (more: boolean) => void;
  historyState?: (state: HistoryLoadState) => void;
  // Display-only cache. Never restore epoch, timing, proof or LIVE eligibility.
  preview?: Pick<ChartState,'candles'|'market'|'quality'>;
};

export function browserMarketEnvironment(): MarketSessionEnvironment {
  return {
    fetch: (...args) => fetch(...args),
    socket: (url) => {
      const native = new WebSocket(url);
      const socket: MarketSocket = {
        onmessage: null,
        onclose: null,
        onerror: null,
        close: () => native.close(),
      };
      native.onmessage = (event) => socket.onmessage?.({ data: event.data });
      native.onclose = () => socket.onclose?.();
      native.onerror = () => socket.onerror?.();
      return socket;
    },
    origin:
      (location.protocol === "https:" ? "wss://" : "ws://") + location.host,
    now: () => Date.now(),
    later: (callback, delay) => setTimeout(callback, delay),
    cancelLater: (timer) => clearTimeout(timer),
    every: (callback, delay) => setInterval(callback, delay),
    cancelEvery: (timer) => clearInterval(timer),
  };
}

/** Owns one symbol/interval subscription. Closing retires every callback and read. */
export function startChartMarketSession(
  options: MarketSessionOptions,
  environment = browserMarketEnvironment(),
) {
  const {
    symbol,
    interval,
    state,
    publish,
    paint,
    historyBusy,
    historyError,
    hasMore,
  } = options;
  const requests = new AbortController();
  const recovery = new RenderRecovery();
  let alive = true,
    loading = false,
    moreHistory = true,
    retries = 0,
    connectionSerial = 0;
  let socket: MarketSocket | undefined,
    retry: ReturnType<typeof setTimeout> | undefined;
  let transportStatus = 'CONNECTING';
  let clockResync = false;
  state.current = { ...initialState(symbol, interval), ...options.preview };
  publish(state.current);
  hasMore(true);
  historyError(false);
  let lastHistoryState: HistoryLoadState = 'READY';
  const reportHistory = (value:HistoryLoadState) => {
    lastHistoryState = value;
    if (alive) options.historyState?.(value);
    return value;
  };
  reportHistory('READY');

  let historyRequest: Promise<HistoryLoadState> | null = null;
  function loadOlder(): Promise<HistoryLoadState> {
    if (historyRequest) return historyRequest;
    historyRequest = fetchOlder().finally(() => { historyRequest = null; });
    return historyRequest;
  }
  async function fetchOlder():Promise<HistoryLoadState> {
    if (alive && state.current.candles.length >= 4000) {
      hasMore(false);
      return reportHistory('LIMIT');
    }
    if (
      !alive ||
      loading ||
      !moreHistory ||
      !state.current.stream_epoch ||
      !state.current.candles.length ||
      state.current.candles.length >= 4000
    )
      return lastHistoryState;
    loading = true;
    reportHistory('LOADING');
    historyBusy(true);
    historyError(false);
    const before = state.current.candles[0].time * 1000 - 1;
    let failure:HistoryLoadState = 'NETWORK_ERROR';
    try {
      const response = await environment.fetch(
        "/api/candles?" +
          new URLSearchParams({
            symbol,
            interval,
            limit: "300",
            end_time: String(before),
          }),
        { signal: requests.signal },
      );
      if (!response.ok) throw Error("History unavailable");
      failure = 'INVALID_DATA';
      const data = await response.json();
      if (!alive) return lastHistoryState;
      failure = 'INVALID_DATA';
      if (
        !isDemoMarket(data) ||
        data.symbol !== symbol ||
        data.interval !== interval
      )
        throw Error("Demo history context required");
      if (!Array.isArray(data.candles) || typeof data.has_more !== 'boolean' || historyQuality(data.candles, interval).invalid_bars) throw Error("Invalid history grid");
      if (data.candles.some((c:Candle) => c.time*1000 > before)) throw Error("History exceeds requested boundary");
      if (!data.candles.length && data.has_more) throw Error("History made no progress");
      const old = state.current.candles,
        commitViewport = options.beforeHistory();
      const merged = mergeHistory(old, data.candles as Candle[]);
      if (data.candles.length && merged[0].time >= old[0].time) throw Error("History made no progress");
      const candidate = checkFreshness({ ...state.current, candles: merged,
        status: state.current.status === 'RENDER_ERROR' ? transportStatus : state.current.status }, environment.now());
      failure = 'RENDER_ERROR';
      if (!recovery.run(true, (full) => paint(candidate, full))) {
        state.current = { ...state.current, status: "RENDER_ERROR" };
        publish(state.current);
        throw Error("History paint failed");
      }
      state.current = candidate;
      const added = merged.length - old.length;
      commitViewport(added);
      publish(state.current);
      // Viewport events call loadOlder directly, independently of the UI button.
      moreHistory = Boolean(data.has_more) && added > 0 && merged.length < 4000;
      hasMore(moreHistory);
      return reportHistory(merged.length >= 4000 ? 'LIMIT' : moreHistory ? 'READY' : 'EXHAUSTED');
    } catch {
      if (alive) historyError(true);
      return alive ? reportHistory(failure) : lastHistoryState;
    } finally {
      if (alive) {
        loading = false;
        historyBusy(false);
      }
    }
  }

  function connect() {
    if (!alive) return;
    retry = undefined;
    clockResync = false;
    const connection = ++connectionSerial;
    state.current = {
      ...beginStream(state.current),
      status: retries ? "RECONNECTING" : "CONNECTING",
    };
    publish(state.current);
    transportStatus = state.current.status;
    const current = environment.socket(
      environment.origin +
        "/api/market-stream?" +
        new URLSearchParams({ symbol, interval }),
    );
    socket = current;
    current.onmessage = (event) => {
      if (!alive || connection !== connectionSerial) return;
      try {
        const packet = JSON.parse(event.data) as Packet;
        if (
          packet.type !== "error" &&
          (!isDemoMarket(packet) || !packet.stream_epoch)
        )
          throw Error("Demo stream proof required");
        if (packet.type === "error") {
          transportStatus = 'ERROR';
          state.current = { ...state.current, status: "ERROR" };
          publish(state.current);
          return;
        }
        // An empty preparation packet announces server startup, not data proof.
        // Keep this cold socket; malformed/nonempty snapshots still resync below.
        if (!state.current.stream_epoch && packet.type==='snapshot' &&
            packet.symbol===symbol && packet.interval===interval &&
            ['CONNECTING','SYNCING','RECONNECTING'].includes(packet.status) &&
            Array.isArray(packet.candles) && !packet.candles.length && packet.data_proof===null) return;
        const candidate = applyRenderedPacket(
          state.current,
          packet,
          recovery,
          (next, full) => { transportStatus = next.status; paint(next, full); },
        );
        if (
          candidate === state.current &&
          packet.stream_epoch &&
          packet.symbol === symbol &&
          packet.interval === interval &&
          !state.current.retired_epochs?.includes(packet.stream_epoch) &&
          ((!state.current.stream_epoch && packet.type === "snapshot") ||
            (packet.stream_epoch === state.current.stream_epoch &&
              packet.sequence > state.current.sequence))
        ) {
          state.current = beginStream(state.current);
          publish(state.current);
          current.close();
          return;
        }
        const next = checkFreshness(candidate, environment.now());
        if (next.status !== 'RENDER_ERROR') transportStatus = next.status;
        if (next === state.current) return;
        state.current = next;
        publish(next);
        if (next.status === "LIVE") retries = 0;
        recoverClock();
      } catch {
        transportStatus = 'ERROR';
        state.current = { ...state.current, status: "ERROR" };
        publish(state.current);
      }
    };
    current.onclose = () => {
      if (!alive || connection !== connectionSerial) return;
      connectionSerial++;
      state.current = beginStream(state.current);
      transportStatus = state.current.status;
      publish(state.current);
      retry = environment.later(
        connect,
        Math.min(15000, 1000 * 2 ** Math.min(retries++, 4)),
      );
    };
    current.onerror = () => {
      if (alive && connection === connectionSerial) current.close();
    };
  }
  // A clock jump requires a proven snapshot. Reuse the single backoff reconnect
  // path; heartbeats must never clear the clock block themselves.
  function recoverClock() {
    if (alive && state.current.consumer_clock_untrusted && !state.current.snapshot_required && retry === undefined && !clockResync) {
      clockResync = true;
      socket?.close();
    }
  }
  connect();
  if (options.preview?.candles.length && !recovery.run(true, full=>paint(state.current,full))) {
    state.current={...state.current,status:'RENDER_ERROR'};
    publish(state.current);
  }
  const freshness = environment.every(() => {
    if (!alive) return;
    const next = checkFreshness(state.current, environment.now());
    if (next !== state.current) {
      state.current = next;
      publish(next);
    }
    recoverClock();
  }, 2000);
  return {
    loadOlder,
    close() {
      if (!alive) return;
      alive = false;
      requests.abort();
      environment.cancelEvery(freshness);
      if (retry !== undefined) environment.cancelLater(retry);
      socket?.close();
      loading = false;
      historyBusy(false);
    },
  };
}
