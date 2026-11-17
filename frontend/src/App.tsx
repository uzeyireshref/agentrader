import { captureTimeViewport, restoreTimeViewport, changeViewportInterval, followLatestViewport, type TimeViewport } from "./chartViewport";
import { ChartDisplayCache } from './chartDisplayCache';
import { steps } from "./evidence";
import GoToDateDialog from "./GoToDateDialog";
import CandleCountdown from "./CandleCountdown";
import { intervalOpen } from "./goToDate";
import { historyLoadLabels, type HistoryLoadState } from "./historyLoad";
import DeferredPanel from "./DeferredPanel";
import { startChartMarketSession } from "./chartMarketSession";
import { useIndicatorLayers } from "./useIndicatorLayers";
import { installChartGestures } from "./chartGestures";
const DrawingClipboard = lazy(() => import("./DrawingClipboard"));
import { candleCoordinate, candleLogicalAt } from "./chartTime";
import { drawingTimeAt } from "./drawingTime";
import { useUiSession } from "./useUiSession";
import type { UiPolicy } from "./uiSession";
import {
  isDemoMarket,
  marketSource,
  marketEnvironment,
} from "./marketEnvironment";
import { useAlertNotifications } from "./useAlertNotifications";
import AlertNotificationToasts from "./AlertNotificationToasts";
const Alerts = lazy(() => import("./Alerts"));
import {
  familyKinds,
  familyNames,
  familyGeometry,
  familyModel,
  validateFamily,
  isPitchfork,
  type FamilyKind,
} from "./channelFamily";
const ReplayValidation = lazy(() => import("./ReplayValidation"));
const LocalEventHistory = lazy(() => import("./LocalEventHistory"));
const RuleBindings = lazy(() => import("./RuleBindings"));
const WorkspaceTemplates = lazy(() => import("./WorkspaceTemplates"));
import { useChartProfiles } from "./useChartProfiles";
import {
  defaultChartView,
  type ChartView,
  type ChartTemplate,
  type ChartProfile,
} from "./chartProfiles";
import { indicatorName } from "./indicatorConfig";
const IndicatorSettings = lazy(() => import("./IndicatorSettings"));
import { useIndicatorConfig } from "./useIndicatorConfig";
import { annotationKinds } from "./annotations";
import ViewScaleControl from "./ViewScaleControl";
import {
  readViewScale,
  saveViewScale,
  applyViewScale,
  supportsView,
  scaleBlockMessage,
  type ViewScale,
} from "./viewScale";
import {
  legacyFibLevels,
  extensionFibLevels,
  validateFibonacci,
} from "./fibonacci";
import { channelBasis } from "./channel";
import { positionMetrics, defaultPositionParams } from "./position";
import { decimalRational, subtract } from "./exactGeometry";
import { lazy, Suspense, useEffect, useLayoutEffect, useRef, useState } from "react";
import Icon from "./ChartIcon";
import ShellMenu from "./ShellMenu";
import ChartCommandDialog, { type CommandMode } from "./ChartCommandDialog";
import {
  installShellShortcuts,
  readSymbolList,
  searchMarkets,
  type ToolKind,
} from "./chartCommands";
import "./terminal.css";
import "./botTerminal.css";
import "./botConnectedLayout.css";
import {createLiveBotDraft} from './botLiveDraft';
import { initialBotDraft, type BotDraft } from "./botPrototype";
const BotPrototype = lazy(() => import("./BotTerminal"));
const BotConnected = lazy(() => import("./BotConnected"));
const BotTerminal =
  new URLSearchParams(location.search).get("mode") === "preview"
    ? BotPrototype
    : BotConnected;
import { draftFromDrawing } from "./botChartBridge";
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { magnetPrice } from "./indicators";
import { ChartSeriesWriter } from "./seriesWriter";
import { RenderRecovery } from "./renderRecovery";
import { checkFreshness } from "./freshness";
import { navigationOptions, installDominantWheel } from "./chartNavigation";
import { installChartKeyboard } from "./chartKeyboard";
import { installCreationCancellation } from "./creationCancellation";
import AlignmentPanel from "./AlignmentPanel";
import PerformancePanel from "./PerformancePanel";
import DrawingLayer from "./DrawingLayer";
import DrawingInteraction from "./DrawingInteraction";
import DrawingToolbar from "./DrawingToolbar";
import { installDrawingShortcuts } from "./drawingShortcuts";
import DrawingPanel from "./DrawingPanel";
import OhlcReadout from "./OhlcReadout";
import DataWindow from "./DataWindow";
import { marketReadiness, statusLabels } from "./chartReadiness";
import PriceScaleControl from "./PriceScaleControl";
import PaneLegends from "./PaneLegends";
import { arrangeVolume, applyPaneLayout, type PanePreset } from "./paneLayout";
import { useDrawings } from "./useDrawings";
import {
  roundPrice,
  pricePrecision,
  type Anchor,
  type Geometry,
} from "./drawings";
import {
  initialState,
  intervals,
  labels,
  type ChartState,
  type Interval,
  type Market,
} from "./types";

type Catalog = { markets: Market[]; ui_session_bridge?: UiPolicy };

const number = (v: number | undefined, digits = 2) =>
  v === undefined
    ? "—"
    : new Intl.NumberFormat("tr-TR", {
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      }).format(v);
const volume = (v: number | undefined) =>
  v === undefined
    ? "—"
    : new Intl.NumberFormat("tr-TR", {
        notation: "compact",
        maximumFractionDigits: 2,
      }).format(v);
export default function App() {
  const [terminalView, setTerminalView] = useState<"chart" | "bot">(() =>
    new URLSearchParams(location.search).get("view") === "bot"
      ? "bot"
      : "chart",
  );
  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set("view", terminalView);
    window.history.replaceState(window.history.state, "", url);
  }, [terminalView]);
  const [botPanel, setBotPanel] = useState(false);
  const [botImportError, setBotImportError] = useState("");
  const [botDraft, setBotDraft] = useState<BotDraft>(() =>
    new URLSearchParams(location.search).get('mode') === 'preview' ? initialBotDraft : createLiveBotDraft());
  const indicatorConfig = useIndicatorConfig();
  const [indicatorSettingsOpen, setIndicatorSettingsOpen] = useState(false);
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
  ] = indicatorConfig.items;
  const showEma = fast.enabled || slow.enabled,
    showRsi = oscillator.enabled;
  const indicatorKey = JSON.stringify(indicatorConfig.items),
    rsiKey = JSON.stringify(oscillator),
    atrKey = JSON.stringify(volatility),
    macdKey = JSON.stringify(convergence);
  const setShowEma = (action: boolean | ((v: boolean) => boolean)) => {
    const enabled = typeof action === "function" ? action(showEma) : action;
    void indicatorConfig.save(
      indicatorConfig.items.map((c) =>
        c.kind === "EMA" ? { ...c, enabled } : c,
      ),
    );
  };
  const setShowRsi = (action: boolean | ((v: boolean) => boolean)) => {
    const enabled = typeof action === "function" ? action(showRsi) : action;
    void indicatorConfig.save(
      indicatorConfig.items.map((c) =>
        c.kind === "RSI" ? { ...c, enabled } : c,
      ),
    );
  };
  const setExtra = (
    kind: "SMA" | "ATR" | "MACD" | "BB" | "SESSION_VWAP" | "ANCHORED_VWAP",
    enabled: boolean,
  ) =>
    void indicatorConfig.save(
      indicatorConfig.items.map((c) =>
        c.kind === kind ? { ...c, enabled } : c,
      ),
    );
  const [viewScale, setViewScale] = useState<ViewScale>(readViewScale);
  const viewScaleRef = useRef(viewScale);
  viewScaleRef.current = viewScale;
  const [clipboardMode, setClipboardMode] = useState<"copy" | "paste" | null>(
    null,
  );
  const [commandMode, setCommandMode] = useState<CommandMode | null>(null);
  const [favorites, setFavorites] = useState(() =>
      readSymbolList("agentrader.favorites", 200),
    ),
    [favoritesOnly, setFavoritesOnly] = useState(false);
  const [recentSymbols, setRecentSymbols] = useState(() =>
      readSymbolList("agentrader.recentSymbols", 8),
    ),
    [marketLimit, setMarketLimit] = useState(80);
  const shellActions = useRef({
    markets: () => {},
    commands: () => {},
    intervals: () => {},
    tool: (_kind: ToolKind) => {},
  });
  const [panel, setPanel] = useState<"markets" | "drawings" | "data" | null>(
    "markets",
  );
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    try {
      return localStorage.getItem("agentrader.theme") === "light"
        ? "light"
        : "dark";
    } catch {
      return "dark";
    }
  });
  const [uiPolicy, setUiPolicy] = useState<UiPolicy | null>(null);
  const [markets, setMarkets] = useState<Market[]>([]),
    [catalogError, setCatalogError] = useState(false),
    [query, setQuery] = useState("");
  const [symbol, setSymbol] = useState("BTCUSDT"),
    [interval, setIntervalValue] = useState<Interval>("15m"),
    [revision, setRevision] = useState(0);
  const [alertsOpen, setAlertsOpen] = useState(false),
    [alertInitialView, setAlertInitialView] = useState<"editor" | "history">(
      "editor",
    );
  const alertNotifications = useAlertNotifications();
  const openAlertHistory = () => {
    setAlertInitialView("history");
    setAlertsOpen(true);
  };
  useEffect(() => {
    const open = () => {
      setAlertInitialView("history");
      setAlertsOpen(true);
    };
    window.addEventListener("agentrader:alert-history", open);
    return () => window.removeEventListener("agentrader:alert-history", open);
  }, []);
  const profiles = useChartProfiles(symbol, interval);
  const [templatesOpen, setTemplatesOpen] = useState(false),
    [bindingsOpen, setBindingsOpen] = useState(false),
    [localEventsOpen, setLocalEventsOpen] = useState(false),
    [replayValidationOpen, setReplayValidationOpen] = useState(false);
  const appliedProfile = useRef<ChartProfile | null>(null),
    pendingWeights = useRef<ChartView["pane_weights"] | null>(null);
  const [view, setView] = useState<ChartState>(() =>
    initialState("BTCUSDT", "15m"),
  );
  const context = marketReadiness(view, symbol, interval);
  const activeView: ChartState =
    view.symbol === symbol && view.interval === interval
      ? { ...view, status: context.status }
      : initialState(symbol, interval);
  const [tool, setTool] = useState<ToolKind>("cursor"),
    [creationNotice, setCreationNotice] = useState(""),
    [historyBusy, setHistoryBusy] = useState(false),
    [historyError, setHistoryError] = useState(false),
    [hasMore, setHasMore] = useState(true);
  const [fullscreenError, setFullscreenError] = useState(""),
    [fullscreenActive, setFullscreenActive] = useState(false);
  const [dragGeometry, setDragGeometry] = useState<Geometry | null>(null);
  const [magnet, setMagnet] = useState(false);
  const magnetEnabled = useRef(false);
  magnetEnabled.current = magnet;
  const indicatorRecovery = useRef(new RenderRecovery());
  const [showVolume, setShowVolume] = useState(true),
    [panePreset, setPanePreset] = useState<PanePreset>("balanced"),
    [paneVersion, setPaneVersion] = useState(0);
  const host = useRef<HTMLDivElement>(null),
    chart = useRef<IChartApi | null>(null),
    series = useRef<ISeriesApi<"Candlestick"> | null>(null),
    histogram = useRef<ISeriesApi<"Histogram"> | null>(null);
  const drawings = useDrawings(
    symbol,
    interval,
    (s, i) => {
      setSymbol(s);
      setIntervalValue(i);
    },
    profiles.ready && !profiles.error
      ? (profiles.profile?.body.drawing_defaults ?? {})
      : null,
  );
  const drawingManager = useRef(drawings);
  drawingManager.current = drawings;
  const zoneStart = useRef<Anchor | null>(null),
    positionStop = useRef<Anchor | null>(null);
  const state = useRef(view),
    activeTool = useRef(tool),
    loadOlder = useRef<() => void>(() => {}),
    fit = useRef(false);
  const cancelViewportRestore = useRef<() => void>(() => {});
  const goToDate = useRef<(time:number)=>void>(()=>{});
  const [dateDialogOpen,setDateDialogOpen] = useState(false);
  const [historyLoadState,setHistoryLoadState] = useState<HistoryLoadState>('READY');
  const [dateLocating,setDateLocating] = useState(false);
  const latestAction = useRef<() => void>(() => {});
  activeTool.current = tool;
  const cancelCreation = () => {
    activeTool.current = "cursor";
    zoneStart.current = null;
    positionStop.current = null;
    setTool("cursor");
    setCreationNotice("");
  };
  const publish = (next: ChartState) =>
    setView(
      indicatorRecovery.current.pending && next.status === "LIVE"
        ? { ...next, status: "RENDER_ERROR" }
        : next,
    );
  const selected = markets.find((m) => m.symbol === symbol),
    last = context.inspectable ? context.rows.at(-1) : undefined,
    decimals = pricePrecision(Number(selected?.tick_size ?? "0.01"));
  const refreshCatalog = () => {
    setCatalogError(false);
    fetch("/api/markets")
      .then((r) => {
        if (!r.ok) throw Error();
        return r.json() as Promise<Catalog>;
      })
      .then((data) => {
        if (
          !isDemoMarket(data) ||
          !Array.isArray(data.markets) ||
          !data.markets.length
        )
          throw Error("Demo market context required");
        setMarkets(data.markets);
        setUiPolicy(
          data.ui_session_bridge?.schema_version === "chart-ui-policy/1"
            ? data.ui_session_bridge
            : null,
        );
        if (!data.markets.some((m) => m.symbol === symbol))
          setSymbol(data.markets[0].symbol);
      })
      .catch(() => setCatalogError(true));
  };
  useEffect(() => {
    refreshCatalog();
  }, []);
  useEffect(() => {
    const changed = () =>
      setFullscreenActive(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", changed);
    return () => document.removeEventListener("fullscreenchange", changed);
  }, []);
  useEffect(() => {
    if (markets.length && !markets.some((m) => m.symbol === symbol))
      setSymbol(markets[0].symbol);
  }, [markets, symbol]);
  useEffect(
    () =>
      installShellShortcuts({
        markets: () => shellActions.current.markets(),
        commands: () => shellActions.current.commands(),
        intervals: () => shellActions.current.intervals(),
        tool: (kind) => shellActions.current.tool(kind),
      }),
    [],
  );
  useEffect(() => {
    try {
      localStorage.setItem("agentrader.favorites", JSON.stringify(favorites));
    } catch {}
  }, [favorites]);
  useEffect(() => {
    try {
      localStorage.setItem(
        "agentrader.recentSymbols",
        JSON.stringify(recentSymbols),
      );
    } catch {}
  }, [recentSymbols]);
  useEffect(() => {
    if (markets.some((m) => m.symbol === symbol))
      setRecentSymbols((list) =>
        list[0] === symbol
          ? list
          : [symbol, ...list.filter((s) => s !== symbol)].slice(0, 8),
      );
  }, [symbol, markets]);
  useEffect(() => {
    if (!host.current) return;
    const instance = createChart(host.current, {
      ...navigationOptions,
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#101416" },
        textColor: "#78858b",
        fontFamily: "Consolas, monospace",
        fontSize: 11,
        attributionLogo: true,
        panes: {
          separatorColor: "#283136",
          separatorHoverColor: "#435055",
          enableResize: true,
        },
      },
      grid: {
        vertLines: { color: "#1b2226" },
        horzLines: { color: "#1b2226" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "#778890", labelBackgroundColor: "#34434b" },
        horzLine: { color: "#778890", labelBackgroundColor: "#34434b" },
      },
      rightPriceScale: {
        borderColor: "#283136",
        minimumWidth: 78,
        mode: viewScale === "LOG" ? 1 : 0,
      },
      timeScale: {
        ...navigationOptions.timeScale,
        borderColor: "#283136",
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 7,
        barSpacing: 8,
      },
      localization: { locale: "tr-TR" },
    });
    const candles = instance.addSeries(CandlestickSeries, {
      upColor: "#4cba94",
      downColor: "#db786f",
      borderVisible: false,
      wickUpColor: "#4cba94",
      wickDownColor: "#db786f",
    });
    const volumes = instance.addSeries(
      HistogramSeries,
      {
        title: "Hacim",
        priceFormat: { type: "volume" },
        priceScaleId: "right",
        priceLineVisible: false,
      },
      1,
    );
    volumes.priceScale().applyOptions({ mode: 0 });
    instance.panes()[0].setStretchFactor(4);
    instance.panes()[1].setStretchFactor(1);
    chart.current = instance;
    series.current = candles;
    histogram.current = volumes;
    const removeWheel = installDominantWheel(host.current);
    const removeGestures = installChartGestures(
      host.current,
      instance,
      candles,
      () => activeTool.current === "cursor" && !drawingManager.current.busy,
    );
    const removeCreationCancellation = installCreationCancellation(
      host.current.parentElement!,
      cancelCreation,
    );
    const removeDrawingShortcuts = installDrawingShortcuts(
      host.current.closest<HTMLElement>(".chart-panel")!,
      () => {
        const m = drawingManager.current;
        return {
          blocked: m.busy || m.loading || m.retryable,
          creating: activeTool.current !== "cursor",
          cancel: cancelCreation,
          canUndo: m.canUndo,
          canRedo: m.canRedo,
          undo: m.undoLast,
          redo: m.redoLast,
          remove: m.removeSelected,
          hasSelection: m.selectedIds.length > 0,
        };
      },
    );
    const removeKeyboard = installChartKeyboard(
      host.current.parentElement!,
      instance,
      () => {
        latestAction.current();
      },
    );
    instance.subscribeClick((event) => {
      if (
        activeTool.current === "cursor" ||
        !event.point ||
        event.paneIndex !== 0
      )
        return;
      const manager = drawingManager.current;
      if (
        !supportsView(
          activeTool.current,
          viewScaleRef.current,
          familyKinds.includes(activeTool.current as FamilyKind)
            ? "chart-channel-family/1"
            : undefined,
        )
      )
        return;
      if (!manager.available) return;
      if (manager.busy || manager.retryable || manager.loading) return;
      const time = drawingTimeAt(
        state.current.candles,
        candleLogicalAt(state.current.candles, event.point.x, instance.timeScale()),
        state.current.interval,
      );
      if (time === null) return;
      let price: number | null = candles.coordinateToPrice(event.point.y);
      if (
        price === null ||
        !Number.isFinite(price) ||
        (viewScaleRef.current === "LOG" && price <= 0)
      )
        return;
      if (magnetEnabled.current)
        price = magnetPrice(
          state.current.candles.find((c) => c.time === time),
          price,
          (p) => candles.priceToCoordinate(p),
          event.point.y,
        );
      const tick = state.current.market?.tick_size;
      if (!tick) return;
      let snapped: string;
      try {
        snapped = roundPrice(price, tick);
      } catch {
        return;
      }
      const anchor = { time, price: snapped };
      if (familyKinds.includes(activeTool.current as FamilyKind)) {
        const kind = activeTool.current as FamilyKind;
        if (!zoneStart.current) {
          zoneStart.current = anchor;
          setCreationNotice(
            kind === "regression_channel"
              ? "Regresyon aralığının son mumunu seç."
              : isPitchfork(kind)
                ? "İkinci salınım noktasını seç."
                : "Temel çizginin ikinci noktasını seç.",
          );
          return;
        }
        if (anchor.time === zoneStart.current.time && !positionStop.current) {
          setCreationNotice("İlk iki nokta farklı mumlarda olmalı.");
          return;
        }
        if (kind !== "regression_channel" && !positionStop.current) {
          positionStop.current = anchor;
          setCreationNotice(
            isPitchfork(kind)
              ? "Üçüncü salınım noktasını seç."
              : "Karşı sınırın fiyatını seç.",
          );
          return;
        }
        const geometry = familyGeometry(
          kind,
          state.current.symbol,
          kind === "regression_channel"
            ? [zoneStart.current, anchor]
            : [zoneStart.current, positionStop.current!, anchor],
        );
        try {
          validateFamily(geometry);
          if (kind === "regression_channel")
            familyModel(geometry, state.current.candles);
        } catch (e) {
          setCreationNotice(e instanceof Error ? e.message : "Çizim geçersiz.");
          return;
        }
        void manager.create(geometry);
        cancelCreation();
        return;
      }
      if (activeTool.current === "fibonacci_projection") {
        if (!zoneStart.current) {
          zoneStart.current = anchor;
          setCreationNotice("Projection: B hareket sonunu seç.");
          return;
        }
        if (!positionStop.current) {
          if (
            anchor.time === zoneStart.current.time ||
            anchor.price === zoneStart.current.price
          ) {
            setCreationNotice("A ve B farklı zaman/fiyat olmalı.");
            return;
          }
          positionStop.current = anchor;
          setCreationNotice("Projection: C projeksiyon tabanını seç.");
          return;
        }
        const g: Geometry = {
          schema: "chart-fibonacci-projection/1",
          kind: "fibonacci_projection",
          basis: "PRICE_DELTA",
          symbol: state.current.symbol,
          price_source: "LAST_PRICE",
          anchors: [zoneStart.current, positionStop.current, anchor],
          levels: extensionFibLevels,
          time_scope: "right",
          label: "Fibonacci projection",
        };
        try {
          validateFibonacci(g);
        } catch {
          setCreationNotice("Projection çapalarını kontrol et.");
          return;
        }
        void manager.create(g);
        cancelCreation();
        return;
      }
      if (
        activeTool.current === "long_plan" ||
        activeTool.current === "short_plan"
      ) {
        if (!zoneStart.current) {
          zoneStart.current = anchor;
          setCreationNotice("Stop fiyatını seç.");
          return;
        }
        if (!positionStop.current) {
          const diff = subtract(
            decimalRational(snapped),
            decimalRational(zoneStart.current.price),
          );
          if (
            activeTool.current === "long_plan" ? diff.n >= 0n : diff.n <= 0n
          ) {
            setCreationNotice(
              activeTool.current === "long_plan"
                ? "Stop girişin altında olmalı."
                : "Stop girişin üstünde olmalı.",
            );
            return;
          }
          positionStop.current = anchor;
          setCreationNotice("Hedef fiyatını ve planın bitiş mumunu seç.");
          return;
        }
        const geometry = {
          schema: "chart-position/1" as const,
          kind: activeTool.current,
          symbol: state.current.symbol,
          price_source: "LAST_PRICE" as const,
          anchors: [
            zoneStart.current,
            { ...positionStop.current, time: anchor.time },
            anchor,
          ],
          params: defaultPositionParams(),
          label:
            activeTool.current === "long_plan" ? "Long plan" : "Short plan",
        };
        try {
          positionMetrics(geometry);
        } catch (e) {
          setCreationNotice(e instanceof Error ? e.message : "Plan geçersiz.");
          return;
        }
        void manager.create(geometry);
        cancelCreation();
        return;
      }
      if (
        !["line", "horizontal_ray", ...annotationKinds].includes(
          activeTool.current,
        ) &&
        !zoneStart.current
      ) {
        zoneStart.current = anchor;
        setCreationNotice(
          activeTool.current === "ruler"
            ? "Ölçümün ikinci noktasını seç."
            : "İkinci nokta için farklı bir mum ve fiyat seç.",
        );
        return;
      }
      const anchors = !["line", "horizontal_ray", ...annotationKinds].includes(
        activeTool.current,
      )
        ? [zoneStart.current!, anchor]
        : [anchor];
      if (
        !["ruler", "ray", "extended_line"].includes(activeTool.current) &&
        anchors.length === 2 &&
        (anchors[0].time === anchors[1].time ||
          anchors[0].price === anchors[1].price)
      ) {
        setCreationNotice("İki nokta farklı zaman ve fiyatta olmalı.");
        return;
      }
      void manager.create({
        ...(annotationKinds.includes(activeTool.current)
          ? {
              schema: "chart-annotation/1" as const,
              text:
                activeTool.current === "text"
                  ? "Metin"
                  : activeTool.current === "note"
                    ? "Notunu buraya yaz."
                    : "",
            }
          : ["fibonacci", "fibonacci_extension"].includes(activeTool.current)
            ? {
                schema: "chart-fibonacci/1" as const,
                levels:
                  activeTool.current === "fibonacci"
                    ? legacyFibLevels
                    : extensionFibLevels,
                time_scope:
                  activeTool.current === "fibonacci"
                    ? ("bounded" as const)
                    : ("right" as const),
              }
            : activeTool.current === "ruler"
              ? { schema: "chart-ruler/1" as const }
              : ["ray", "extended_line", "horizontal_ray"].includes(
                    activeTool.current,
                  )
                ? { schema: "chart-line/1" as const }
                : {}),
        kind: activeTool.current === "line" ? "horizontal" : activeTool.current,
        symbol: state.current.symbol,
        price_source: "LAST_PRICE",
        anchors,
        label:
          activeTool.current === "text"
            ? "Metin"
            : activeTool.current === "note"
              ? "Not"
              : activeTool.current === "price_label"
                ? "Fiyat etiketi"
                : activeTool.current === "fibonacci_extension"
                  ? "Fibonacci extension"
                  : activeTool.current === "ruler"
                    ? "Cetvel"
                    : activeTool.current === "line"
                      ? "Yatay seviye"
                      : activeTool.current === "ray"
                        ? "Işın"
                        : activeTool.current === "extended_line"
                          ? "Uzatılmış çizgi"
                          : activeTool.current === "horizontal_ray"
                            ? "Yatay ışın"
                            : activeTool.current === "zone"
                              ? "Fiyat bölgesi"
                              : activeTool.current === "trend"
                                ? "Trend çizgisi"
                                : "Fibonacci",
      });
      cancelCreation();
    });

    instance.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (range) {
        const first = candleCoordinate(state.current.candles, 0, instance.timeScale());
        const firstIndex = first === null ? null : instance.timeScale().coordinateToLogical(first);
        if (firstIndex !== null && range.from < firstIndex + 15) loadOlder.current();
      }
    });
    return () => {
      removeCreationCancellation();
      removeDrawingShortcuts();
      removeKeyboard();
      removeWheel();
      removeGestures();
      queueMicrotask(() => instance.remove());
      chart.current = null;
      series.current = null;
      histogram.current = null;
    };
  }, []);
  useEffect(() => {
    try {
      localStorage.setItem("agentrader.theme", theme);
    } catch {
      /* Storage can be unavailable. */
    }
    const light = theme === "light",
      bg = light ? "#ffffff" : "#11151c",
      text = light ? "#526074" : "#9ba8ba",
      grid = light ? "#edf0f4" : "#1d2531",
      border = light ? "#dfe4ec" : "#293241";
    document.documentElement.style.colorScheme = theme;
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", bg);
    chart.current?.applyOptions({
      layout: {
        background: { type: ColorType.Solid, color: bg },
        textColor: text,
        fontFamily: "Arial, sans-serif",
        fontSize: 12,
        panes: {
          separatorColor: border,
          separatorHoverColor: light ? "#c2ccdd" : "#465772",
        },
      },
      grid: { vertLines: { color: grid }, horzLines: { color: grid } },
      rightPriceScale: { borderColor: border },
      timeScale: { borderColor: border },
      crosshair: {
        vertLine: {
          color: light ? "#8c99ac" : "#61728c",
          labelBackgroundColor: light ? "#526074" : "#394960",
        },
        horzLine: {
          color: light ? "#8c99ac" : "#61728c",
          labelBackgroundColor: light ? "#526074" : "#394960",
        },
      },
    });
    series.current?.applyOptions({
      upColor: "#159d82",
      downColor: "#e05a66",
      wickUpColor: "#159d82",
      wickDownColor: "#e05a66",
    });
  }, [theme]);
  useEffect(() => {
    if (series.current && selected)
      series.current.applyOptions({
        priceFormat: {
          type: "price",
          precision: decimals,
          minMove: Number(selected.tick_size),
        },
      });
  }, [selected, decimals]);
  const indicatorViewport = useRef<{symbol:string;interval:Interval;view:TimeViewport}|null>(null);
  // Layout cleanup precedes passive indicator-series disposal. Capture the old grid.
  useLayoutEffect(() => () => {
    const current = state.current, scale = chart.current?.timeScale();
    const snapshot = scale ? captureTimeViewport(current.candles, steps[current.interval], scale) : null;
    indicatorViewport.current = snapshot ? {symbol:current.symbol,interval:current.interval,view:snapshot} : null;
  }, [indicatorKey]);
  const indicatorLayers = useIndicatorLayers(chart, indicatorConfig.items, () =>
    setPaneVersion((v) => v + 1),
  );
  const { rsiSeries, atrSeries, macdLine } = indicatorLayers;
  const layersRef = useRef(indicatorLayers);
  layersRef.current = indicatorLayers;
  const followingLatest = useRef(true);
  const displayCache = useRef(new ChartDisplayCache());
  const savedViewport = useRef<{symbol:string;interval:Interval;view:TimeViewport;tail:number}|null>(null);
  const [viewportNotice, setViewportNotice] = useState("");
  useEffect(() => {
    if (!markets.length || !series.current || !histogram.current) return;
    cancelCreation();
    setViewportNotice("");
    setDateLocating(false);
    const saved = savedViewport.current;
    if (saved && saved.symbol !== symbol) followingLatest.current = true;
    let pendingLiveView = followingLatest.current && saved?.symbol === symbol ? saved : null;
    let pendingViewport = !pendingLiveView && saved?.symbol === symbol ? (saved.interval === interval ? saved.view : changeViewportInterval(saved.view, steps[interval])) : null;
    let paintedRows = state.current.symbol === symbol && state.current.interval === interval ? state.current.candles : [];
    let retired = false, locating:number|null = null, viewportIntent = 0;
    let pendingTarget:number|null=null;
    cancelViewportRestore.current = () => {viewportIntent++;pendingLiveView=null;pendingViewport = null;pendingTarget=null; setViewportNotice("");setDateLocating(false);};
    const surface = host.current?.parentElement;
    let pointerViewport:TimeViewport|null = null;
    let navigationFrame:number|undefined;
    let navigationTarget:{before:TimeViewport;intent:number}|null=null;
    const readViewport = () => {
      const scale=chart.current?.timeScale();
      return scale ? captureTimeViewport(state.current.candles,steps[interval],scale) : null;
    };
    const commitNavigation = () => {
      const target=navigationTarget;navigationTarget=null;
      if(retired||!target||target.intent!==viewportIntent)return;
      const after=readViewport(),tail=state.current.candles.at(-1)?.time,before=target.before;
      if(!after||tail===undefined||Math.abs(after.from-before.from)<.001&&Math.abs(after.to-before.to)<.001)return;
      followingLatest.current=after.from<=tail&&after.to>=tail;
    };
    const trackNavigation = (before:TimeViewport|null) => {
      if(navigationFrame!==undefined)cancelAnimationFrame(navigationFrame);
      navigationTarget=before?{before,intent:viewportIntent}:null;
      // The native chart applies wheel/drag ranges on its animation frame.
      navigationFrame=requestAnimationFrame(()=>{
        navigationFrame=requestAnimationFrame(()=>{
          navigationFrame=undefined;
          commitNavigation();
        });
      });
    };
    const userNavigation = (event: Event) => {
      if (event instanceof KeyboardEvent && !["ArrowLeft","ArrowRight","+","=","-","_","End"].includes(event.key)) return;
      if (event.target instanceof Element && event.target.closest('button,input,textarea,select,[contenteditable="true"]')) return;
      const before=readViewport();
      cancelViewportRestore.current();
      if(event.type==='pointerdown')pointerViewport=before;
      else if (!(event instanceof KeyboardEvent && event.key === 'End')) trackNavigation(before);
    };
    const pointerNavigation = (event:PointerEvent) => {
      if(!pointerViewport)return;
      trackNavigation(pointerViewport);
      if(event.type!=='pointermove')pointerViewport=null;
    };
    surface?.addEventListener("wheel", userNavigation, true);
    surface?.addEventListener("pointerdown", userNavigation, true);
    surface?.addEventListener("keydown", userNavigation, true);
    surface?.addEventListener("pointermove", pointerNavigation, true);
    surface?.addEventListener("pointerup", pointerNavigation, true);
    surface?.addEventListener("pointercancel", pointerNavigation, true);
    fit.current = false;
    layersRef.current.write(initialState(symbol, interval), true);
    series.current.setData([]);
    histogram.current.setData([]);
    series.current.priceScale().applyOptions({ autoScale: true });
    const writer = new ChartSeriesWriter(
      {
        setData: (rows) =>
          series.current!.setData(
            rows.map((c) => ({ ...c, time: c.time as UTCTimestamp })),
          ),
        update: (c, historical) =>
          series.current!.update(
            { ...c, time: c.time as UTCTimestamp },
            historical,
          ),
      },
      {
        setData: (rows) =>
          histogram.current!.setData(
            rows.map((c) => ({ ...c, time: c.time as UTCTimestamp })),
          ),
        update: (c, historical) =>
          histogram.current!.update(
            { ...c, time: c.time as UTCTimestamp },
            historical,
          ),
      },
    );
    const paint = (next: ChartState, full: boolean) => {
      if (!series.current || !histogram.current) return;
      const scale = chart.current?.timeScale();
      const previous = scale && paintedRows.length ? captureTimeViewport(paintedRows, steps[interval], scale) : null;
      const previousTail = paintedRows.at(-1)?.time;
      const result = writer.write(next.candles, full);
      if (!indicatorRecovery.current.run(full, (reset) => layersRef.current.write(next, reset))) throw Error("Indicator render failed");
      paintedRows = next.candles;
      if (!scale || !next.candles.length) return;
      if (pendingLiveView) {
        pendingViewport = followLatestViewport(pendingLiveView.view, pendingLiveView.tail, steps[pendingLiveView.interval], next.candles.at(-1)!.time, steps[interval]);
        if(next.stream_epoch)pendingLiveView = null;
      }
      if (pendingViewport) {
        restoreTimeViewport(next.candles, steps[interval], scale, pendingViewport);
        fit.current = true;
        queueMicrotask(() => { if (!retired) void locateViewport(); });
      } else if (!fit.current) {
        fit.current = true;
        restoreTimeViewport(next.candles, steps[interval], scale, {
          from: next.candles[Math.max(0,next.candles.length-110)].time,
          to: next.candles.at(-1)!.time + 7*steps[interval], bars:117,
        });
      } else if (previous && (full || result.removedLeading || followingLatest.current && previousTail !== next.candles.at(-1)!.time)) {
        const view = followingLatest.current && previousTail !== undefined
          ? followLatestViewport(previous, previousTail, steps[interval], next.candles.at(-1)!.time, steps[interval]) : previous;
        restoreTimeViewport(next.candles, steps[interval], scale, view);
      }
    };
    async function locateViewport() {
      const intent = viewportIntent;
      if (locating === intent || !pendingViewport || retired || !state.current.stream_epoch) return;
      locating = intent;
      try {
        while (!retired && pendingViewport && state.current.candles.length && state.current.candles[0].time > (pendingTarget??pendingViewport.from)) {
          const first = state.current.candles[0].time;
          setDateLocating(pendingTarget !== null);
          const outcome = await session.loadOlder();
          if (retired || intent !== viewportIntent) return;
          if (!pendingViewport) return;
          if (state.current.candles[0].time >= first) {
            pendingViewport = null;
            if(pendingTarget!==null)setViewportNotice(outcome==='READY' ? 'İstenen tarihe ulaşılamadı.' : historyLoadLabels[outcome]);
            return;
          }
        }
        if (!retired && pendingViewport && chart.current) {
          restoreTimeViewport(state.current.candles, steps[interval], chart.current.timeScale(), pendingViewport);
          if(pendingTarget!==null){
            const target=pendingTarget;
            setViewportNotice(state.current.candles.some(c=>c.time===target)
              ? new Date(target*1000).toISOString().slice(0,16).replace('T',' ')+' UTC tarihindeki mum gösteriliyor.'
              : 'Seçilen tarihte mum yok: geçmişte veri boşluğu var.');
          }
          pendingViewport = null;pendingTarget=null;
        }
      } finally { if(locating === intent) locating = null;if(!retired && intent === viewportIntent)setDateLocating(false); }
    }

    const session = startChartMarketSession({
      symbol,
      interval,
      preview: displayCache.current.get(symbol,interval),
      state,
      publish,
      paint,
      historyBusy: setHistoryBusy,
      historyError: setHistoryError,
      hasMore: setHasMore,
      historyState: setHistoryLoadState,
      beforeHistory: () => () => {},
    });
    loadOlder.current = session.loadOlder;
    goToDate.current = (requested) => {
      cancelViewportRestore.current();
      const rows=state.current.candles,scale=chart.current?.timeScale();
      if(!rows.length||!scale)return;
      const target=intervalOpen(requested,interval),tail=rows.at(-1)!;
      if(target>tail.time){setViewportNotice('Bu tarihin mumu henüz yok. Son mevcut mum için Güncel seç.');return;}
      followingLatest.current = false;
      cancelCreation();setViewportNotice('');
      const current=captureTimeViewport(rows,steps[interval],scale);
      const bars=Math.min(1000,Math.max(2,current?.bars??110));
      pendingTarget=target;
      pendingViewport={from:target-bars*steps[interval]/2,to:target+bars*steps[interval]/2,bars};
      void locateViewport();
    };
    return () => {
      commitNavigation();
      retired = true;
      displayCache.current.put(state.current);
      surface?.removeEventListener("wheel", userNavigation, true);
      surface?.removeEventListener("pointerdown", userNavigation, true);
      surface?.removeEventListener("keydown", userNavigation, true);
      surface?.removeEventListener("pointermove", pointerNavigation, true);
      surface?.removeEventListener("pointerup", pointerNavigation, true);
      surface?.removeEventListener("pointercancel", pointerNavigation, true);
      if(navigationFrame!==undefined)cancelAnimationFrame(navigationFrame);
      const scale = chart.current?.timeScale();
      const snapshot = pendingViewport ?? (scale ? captureTimeViewport(paintedRows, steps[interval], scale) : null);
      if (snapshot && paintedRows.length) savedViewport.current = {symbol, interval, view:snapshot,tail:paintedRows.at(-1)!.time};
      session.close();
      loadOlder.current = () => {};
      goToDate.current = () => {};
    };
  }, [symbol, interval, revision, markets.length]);

  useEffect(() => {
    const instance = chart.current,
      price = series.current,
      volume = histogram.current;
    if (!instance || !price || !volume) return;
    arrangeVolume(instance, volume, showVolume);
    [rsiSeries.current, atrSeries.current, macdLine.current]
      .filter((s): s is ISeriesApi<"Line"> => !!s)
      .forEach((s, i) => {
        const target = i + (showVolume ? 2 : 1);
        if (s.getPane().paneIndex() !== target)
          instance.swapPanes(s.getPane().paneIndex(), target);
      });
    applyPaneLayout(
      price,
      showVolume ? volume : null,
      rsiSeries.current,
      panePreset,
    );
    const w = pendingWeights.current;
    if (w) {
      const targets = {
        price,
        volume: showVolume ? volume : null,
        rsi: rsiSeries.current,
        atr: atrSeries.current,
        macd: macdLine.current,
      };
      for (const key of Object.keys(targets) as (keyof typeof targets)[])
        targets[key]?.getPane().setStretchFactor(w[key]);
    }
    setPaneVersion((v) => v + 1);
  }, [showVolume, rsiKey, atrKey, macdKey, panePreset]);
  useEffect(() => {
    const recovery = indicatorRecovery.current,
      wasPending = recovery.pending;
    const success = recovery.run(false, (full) =>
      indicatorLayers.write(view, full),
    );
    const saved = indicatorViewport.current, current = state.current, scale = chart.current?.timeScale();
    if (success && saved && scale && saved.symbol === current.symbol && saved.interval === current.interval) {
      restoreTimeViewport(current.candles, steps[current.interval], scale, saved.view);
      indicatorViewport.current = null;
    }
    if (!success || wasPending)
      publish(checkFreshness(state.current, Date.now()));
  }, [indicatorKey]);
  useEffect(() => {
    const p = profiles.profile;
    if (
      !profiles.ready ||
      !p ||
      p.revision === 0 ||
      appliedProfile.current === p
    )
      return;
    appliedProfile.current = p;
    cancelCreation();
    const v = p.body.view;
    setTheme(v.theme);
    setShowVolume(v.show_volume);
    setPanePreset(v.pane_preset);
    setPanel(v.panel);
    setViewScale(v.price_scale);
    viewScaleRef.current = v.price_scale;
    saveViewScale(v.price_scale);
    if (
      series.current &&
      (series.current.priceScale().options().mode === 1 ? "LOG" : "LINEAR") !==
        v.price_scale
    )
      applyViewScale(series.current, v.price_scale);
    pendingWeights.current = { ...v.pane_weights };
  }, [profiles.ready, profiles.profile]);
  useEffect(() => {
    if (!pendingWeights.current || !indicatorConfig.ready) return;
    const frame = requestAnimationFrame(() => {
      const w = pendingWeights.current;
      if (!w) return;
      const targets = {
        price: series.current,
        volume: showVolume ? histogram.current : null,
        rsi: rsiSeries.current,
        atr: atrSeries.current,
        macd: macdLine.current,
      };
      for (const key of Object.keys(targets) as (keyof typeof targets)[])
        targets[key]?.getPane().setStretchFactor(w[key]);
      setPaneVersion((v) => v + 1);
    });
    return () => cancelAnimationFrame(frame);
  }, [
    profiles.profile,
    indicatorConfig.ready,
    indicatorKey,
    showVolume,
    panePreset,
  ]);
  useEffect(() => {
    const element = host.current;
    if (!element) return;
    const resized = () => {
      const w = pendingWeights.current;
      if (!w) return;
      const targets = {
        price: series.current,
        volume: showVolume ? histogram.current : null,
        rsi: rsiSeries.current,
        atr: atrSeries.current,
        macd: macdLine.current,
      };
      for (const key of Object.keys(targets) as (keyof typeof targets)[])
        if (targets[key]) w[key] = targets[key]!.getPane().getStretchFactor();
    };
    element.addEventListener("pointerup", resized);
    return () => element.removeEventListener("pointerup", resized);
  }, [showVolume, indicatorKey]);
  const setLayoutPreset = (preset: PanePreset) => {
    pendingWeights.current = null;
    setPanePreset(preset);
    if (series.current)
      applyPaneLayout(
        series.current,
        showVolume ? histogram.current : null,
        rsiSeries.current,
        preset,
      );
    setPaneVersion((v) => v + 1);
  };
  const resetPaneLayout = () => setLayoutPreset("balanced");

  const matchedMarkets = searchMarkets(markets, query).filter(
    (m) => !favoritesOnly || favorites.includes(m.symbol),
  );
  const filtered = matchedMarkets.slice(0, marketLimit);
  const toggleFavorite = (value: string) =>
    setFavorites((list) =>
      list.includes(value)
        ? list.filter((s) => s !== value)
        : [...list, value].slice(-200),
    );
  const chooseTool = (next: ToolKind) => {
    if (
      !supportsView(
        next,
        viewScale,
        familyKinds.includes(next as FamilyKind)
          ? "chart-channel-family/1"
          : undefined,
      )
    ) {
      setCreationNotice(scaleBlockMessage);
      return;
    }
    if (
      next !== "cursor" &&
      (!profiles.ready ||
        !!profiles.error ||
        profiles.busy ||
        !drawings.available ||
        drawings.busy ||
        drawings.retryable ||
        drawings.loading ||
        !context.inspectable)
    )
      return;
    zoneStart.current = null;
    positionStop.current = null;
    setCreationNotice("");
    activeTool.current = next;
    setTool(next);
  };
  const goLive = () => {
    cancelViewportRestore.current();
    followingLatest.current = true;
    const rows=state.current.candles, scale=chart.current?.timeScale();
    if(!rows.length||!scale)return;
    const x=candleCoordinate(rows,rows.length-1,scale),range=scale.getVisibleLogicalRange();
    const last=x===null?null:scale.coordinateToLogical(x);
    if(last!==null&&range)scale.setVisibleLogicalRange({from:last+7-(range.to-range.from),to:last+7});
  };
  latestAction.current = goLive;
  const resetView = () => {
    cancelViewportRestore.current();
    followingLatest.current = true;
    const rows=state.current.candles,scale=chart.current?.timeScale();
    if(!rows.length||!scale)return;
    series.current?.priceScale().applyOptions({autoScale:true});
    restoreTimeViewport(rows,steps[state.current.interval],scale,{
      from:rows[Math.max(0,rows.length-110)].time,to:rows.at(-1)!.time+7*steps[state.current.interval],bars:117,
    });
  };
  const change = last
    ? ((last.close - last.open) / last.open) * 100
    : undefined;
  const toolDisabled =
    !profiles.ready ||
    !!profiles.error ||
    profiles.busy ||
    drawings.busy ||
    drawings.retryable ||
    drawings.loading ||
    !context.inspectable;
  const visibleDrawings = {
    ...drawings,
    items: drawings.loading
      ? []
      : drawings.items.filter((d) => d.geometry.symbol === symbol),
    selected: drawings.loading ? null : drawings.selected,
  };
  const changeViewScale = (mode: ViewScale) => {
    if (!series.current) return;
    cancelCreation();
    applyViewScale(series.current, mode);
    viewScaleRef.current = mode;
    setViewScale(mode);
    saveViewScale(mode);
  };
  const toolButton = (kind: typeof tool, label: string, icon: string) => (
    <button
      key={kind}
      type="button"
      aria-label={label}
      title={
        supportsView(
          kind,
          viewScale,
          familyKinds.includes(kind as FamilyKind)
            ? "chart-channel-family/1"
            : undefined,
        )
          ? label
          : scaleBlockMessage
      }
      aria-pressed={tool === kind}
      className={tool === kind ? "active" : ""}
      disabled={
        kind !== "cursor" &&
        (toolDisabled ||
          !supportsView(
            kind,
            viewScale,
            familyKinds.includes(kind as FamilyKind)
              ? "chart-channel-family/1"
              : undefined,
          ))
      }
      onClick={() => chooseTool(kind)}
    >
      <Icon name={icon} />
      <span>{label}</span>
    </button>
  );
  const togglePanel = (next: "markets" | "drawings" | "data") =>
    setPanel((p) => (p === next ? null : next));
  shellActions.current = {
    markets: () => {
      setPanel("markets");
      requestAnimationFrame(() =>
        document
          .querySelector<HTMLInputElement>('input[aria-label="Coin ara"]')
          ?.focus(),
      );
    },
    commands: () => setCommandMode("symbols"),
    intervals: () => setCommandMode("intervals"),
    tool: chooseTool,
  };
  const captureView = (): ChartView => {
    const weights = {
        ...(profiles.profile?.body.view.pane_weights ??
          defaultChartView().pane_weights),
      },
      targets = {
        price: series.current,
        volume: showVolume ? histogram.current : null,
        rsi: rsiSeries.current,
        atr: atrSeries.current,
        macd: macdLine.current,
      };
    for (const key of Object.keys(targets) as (keyof typeof targets)[])
      if (targets[key])
        weights[key] = targets[key]!.getPane().getStretchFactor();
    return {
      theme,
      show_volume: showVolume,
      pane_preset: panePreset,
      price_scale: viewScale,
      panel,
      pane_weights: weights,
    };
  };

  useUiSession(uiPolicy, {
    visible: terminalView === "chart",
    chart: () => chart.current,
    series: () => series.current,
    rows: activeView.candles,
    marketKey: symbol + ":" + interval,
    collect: (hover) => {
      const timeScale = chart.current?.timeScale(),
        logical = timeScale?.getVisibleLogicalRange() ?? null,
        time = timeScale?.getVisibleRange() ?? null;
      const prices = series.current?.priceScale().getVisibleRange() ?? null,
        size = chart.current?.paneSize(0);
      return {
        market: {
          source: marketSource,
          environment: marketEnvironment,
          product: "USD-M",
          price_type: "LAST_PRICE",
          symbol,
          interval,
        },
        market_data: {
          status: activeView.status,
          stream_epoch: activeView.stream_epoch ?? null,
          generation: activeView.generation,
          sequence: activeView.sequence,
        },
        viewport: {
          logical_range: logical,
          time_range:
            time && typeof time.from === "number" && typeof time.to === "number"
              ? time
              : null,
          price_range:
            prices && Number.isFinite(prices.from) && Number.isFinite(prices.to)
              ? { from: String(prices.from), to: String(prices.to) }
              : null,
          width: Math.round(size?.width ?? 0),
          height: Math.round(size?.height ?? 0),
          scale: viewScale,
          inverted: series.current?.priceScale().options().invertScale ?? false,
        },
        selection: {
          drawing_ids: drawings.loading
            ? []
            : drawings.selectedIds.filter((id) =>
                drawings.items.some(
                  (d) =>
                    d.drawing_id === id &&
                    !d.deleted &&
                    d.geometry.symbol === symbol,
                ),
              ),
          tool,
        },
        crosshair: hover,
        magnet,
        panels: {
          sidebar: panel,
          volume: showVolume,
          indicator_settings: indicatorSettingsOpen,
          alerts: alertsOpen,
          templates: templatesOpen,
          bindings: bindingsOpen,
          local_events: localEventsOpen,
          replay: replayValidationOpen,
          command_dialog: commandMode !== null,
          fullscreen: fullscreenActive,
          pane_preset: panePreset,
          pane_weights: captureView().pane_weights,
        },
        indicators: {
          settings_revision: indicatorConfig.revision,
          visible_ids: indicatorConfig.items
            .filter((i) => i.enabled)
            .map((i) => i.indicator_id),
        },
        theme,
        favorites,
        notifications: {
          in_app: alertNotifications.prefs.inApp,
          sound: alertNotifications.prefs.sound,
          desktop: alertNotifications.prefs.desktop,
          desktop_permission: alertNotifications.permission,
          sound_ready: alertNotifications.soundReady,
        },
        history: {
          can_undo: !toolDisabled && drawings.canUndo,
          can_redo: !toolDisabled && drawings.canRedo,
          ...drawings.historySummary,
        },
        persistent_refs: {
          workspace_revision: drawings.workspaceRevision,
          profile_revision: profiles.profile?.revision ?? null,
          indicator_settings_revision: indicatorConfig.revision,
        },
        loading: {
          drawings: drawings.loading,
          indicators: !indicatorConfig.ready,
          profile: !profiles.ready,
        },
      };
    },
  });
  const restoreTemplate = async (t: ChartTemplate, applyStyles: boolean) => {
    if (
      !profiles.ready ||
      !indicatorConfig.ready ||
      indicatorConfig.busy ||
      drawings.busy ||
      drawings.loading ||
      drawings.retryable
    )
      return false;
    const r = await profiles.restore(
      t,
      indicatorConfig.revision,
      drawings.items
        .filter((d) => d.geometry.symbol === symbol)
        .map((d) => ({ drawing_id: d.drawing_id, revision: d.revision })),
      applyStyles,
    );
    if (!r) return false;
    indicatorConfig.accept(r.indicators);
    profiles.accept(r.profile);
    await drawings.refresh();
    return true;
  };
  const reloadProfiles = async () => {
    const indicatorLoad = indicatorConfig.reload();
    const [p, i, d] = await Promise.all([
      profiles.reload(),
      indicatorLoad,
      drawings.refresh(),
    ]);
    return Boolean(p && i && d);
  };
  const selectedBotDrawing = drawings.items.find(
    (d) => d.drawing_id === drawings.selected && !d.deleted,
  );
  const botSourceDrawing = botDraft.source
    ? drawings.items.find(
        (d) =>
          d.drawing_id === botDraft.source!.drawingId &&
          d.workspace_id === botDraft.source!.workspace &&
          !d.deleted,
      )
    : undefined;
  const botSourceChanged = Boolean(
    botDraft.source &&
      (drawings.loading ||
        !botSourceDrawing ||
        botSourceDrawing.revision !== botDraft.source.revision),
  );
  const importBotDrawing = () => {
    try {
      if (!selectedBotDrawing || drawings.loading)
        throw Error("Geçerli bir Long/Short pozisyon çizimi seçin.");
      const next = draftFromDrawing(botDraft, selectedBotDrawing);
      setBotDraft(next);
      setTerminalView("bot");
      setBotImportError("");
    } catch (error) {
      setBotImportError(
        error instanceof Error ? error.message : "Çizim aktarılamadı.",
      );
    }
  };
  const openBotChart = (nextSymbol: string) => {
    setSymbol(nextSymbol);
    setTerminalView("chart");
    setBotPanel(false);
  };
  return (
    <div className="terminal" data-theme={theme}>
      <nav className="bot-app-nav" aria-label="Uygulama görünümleri">
        <strong>AGENTRADER</strong>
        <button
          aria-pressed={terminalView === "chart"}
          onClick={() => setTerminalView("chart")}
        >
          Grafik
        </button>
        <button
          aria-pressed={terminalView === "bot"}
          onClick={() => setTerminalView("bot")}
        >
          Bot
        </button>
        {terminalView === "chart" && (
          <button
            aria-pressed={botPanel}
            onClick={() => {
              setBotPanel((v) => !v);
            }}
          >
            İşlem paneli
          </button>
        )}
        {terminalView === "chart" && (
          <button
            disabled={
              !selectedBotDrawing ||
              drawings.loading ||
              !["long_plan", "short_plan"].includes(
                selectedBotDrawing.geometry.kind,
              )
            }
            onClick={importBotDrawing}
          >
            Seçili planı bota aktar
          </button>
        )}
        <small>USD-M · DEMO</small>
      </nav>
      <div className="bot-view" hidden={terminalView !== "bot"}>
        <Suspense fallback={<p>Bot terminali yükleniyor…</p>}>
          <BotTerminal
            active={terminalView === "bot"}
            draft={botDraft}
            onDraft={setBotDraft}
            onChart={openBotChart}
            symbols={markets.map((m) => m.symbol)}
            sourceChanged={botSourceChanged}
          />
        </Suspense>
      </div>
      {terminalView === "chart" && botPanel && (
        <aside className="bot-chart-side" aria-label="Grafik işlem paneli">
          <button onClick={() => setBotPanel(false)}>Paneli kapat</button>
          <Suspense fallback={<p>İşlem paneli yükleniyor…</p>}>
            <BotTerminal
              onTerminal={() => setTerminalView("bot")}
              compact
              draft={botDraft}
              onDraft={setBotDraft}
              onChart={openBotChart}
              symbols={markets.map((m) => m.symbol)}
              sourceChanged={botSourceChanged}
            />
          </Suspense>
        </aside>
      )}
      {botImportError && (
        <p className="bot-import-error" role="alert">
          {botImportError}
          <button onClick={() => setBotImportError("")}>Kapat</button>
        </p>
      )}
      <a
        className="skip-link"
        href="#chart-main"
        hidden={terminalView !== "chart"}
      >
        Grafiğe geç
      </a>
      <main
        id="chart-main"
        hidden={terminalView !== "chart"}
        style={terminalView !== "chart" ? { display: "none" } : undefined}
        tabIndex={-1}
      >
        <section className="chart-panel">
          {replayValidationOpen && (
            <DeferredPanel onClose={() => setReplayValidationOpen(false)}>
              <ReplayValidation
                onClose={() => setReplayValidationOpen(false)}
              />
            </DeferredPanel>
          )}
          <AlertNotificationToasts
            notifications={alertNotifications}
            onHistory={openAlertHistory}
          />
          {alertsOpen && (
            <DeferredPanel onClose={() => setAlertsOpen(false)}>
              <Alerts
                initialView={alertInitialView}
                notifications={alertNotifications}
                symbol={symbol}
                interval={interval}
                indicators={indicatorConfig.items}
                drawings={drawings.items}
                onClose={() => setAlertsOpen(false)}
              />
            </DeferredPanel>
          )}
          {localEventsOpen && (
            <DeferredPanel onClose={() => setLocalEventsOpen(false)}>
              <LocalEventHistory onClose={() => setLocalEventsOpen(false)} />
            </DeferredPanel>
          )}
          {bindingsOpen && (
            <DeferredPanel onClose={() => setBindingsOpen(false)}>
              <RuleBindings
                symbol={symbol}
                interval={interval}
                scale={viewScale}
                rows={activeView.candles}
                snapshotHash={activeView.data_proof?.snapshot_hash}
                drawings={drawings.items.filter(
                  (d) => d.geometry.symbol === symbol,
                )}
                indicators={indicatorConfig.items}
                selected={drawings.selected}
                disabled={
                  drawings.loading ||
                  drawings.busy ||
                  drawings.retryable ||
                  !indicatorConfig.ready ||
                  indicatorConfig.busy ||
                  profiles.busy
                }
                onRefreshTargets={reloadProfiles}
                onClose={() => setBindingsOpen(false)}
              />
            </DeferredPanel>
          )}
          {clipboardMode && (
            <DeferredPanel onClose={() => setClipboardMode(null)}>
              <DrawingClipboard
                mode={clipboardMode}
                symbol={symbol}
                interval={interval}
                selected={drawings.items.filter((d) =>
                  drawings.selectedIds.includes(d.drawing_id),
                )}
                busy={drawings.busy}
                retryable={drawings.retryable}
                error={drawings.message}
                onPaste={drawings.pastePackage}
                onRetry={drawings.retry}
                onClose={() => setClipboardMode(null)}
              />
            </DeferredPanel>
          )}
          {templatesOpen && (
            <DeferredPanel onClose={() => setTemplatesOpen(false)}>
              <WorkspaceTemplates
                profiles={profiles}
                indicators={indicatorConfig.items}
                indicatorsReady={indicatorConfig.ready && !indicatorConfig.busy}
                captureView={captureView}
                selected={
                  drawings.items.find(
                    (d) => d.drawing_id === drawings.selected,
                  ) ?? null
                }
                canRestore={
                  indicatorConfig.ready &&
                  !indicatorConfig.busy &&
                  !drawings.loading &&
                  !drawings.busy &&
                  !drawings.retryable
                }
                externalError={indicatorConfig.error || drawings.message}
                onRestore={restoreTemplate}
                onReload={reloadProfiles}
                onClose={() => setTemplatesOpen(false)}
              />
            </DeferredPanel>
          )}
          {indicatorSettingsOpen && (
            <DeferredPanel onClose={() => setIndicatorSettingsOpen(false)}>
              <IndicatorSettings
                symbol={symbol}
                items={indicatorConfig.items}
                busy={indicatorConfig.busy}
                error={indicatorConfig.error}
                onSave={indicatorConfig.save}
                onClose={() => setIndicatorSettingsOpen(false)}
              />
            </DeferredPanel>
          )}
          <header className="shell-header" aria-label="Grafik kontrolleri">
            <a
              className="shell-brand"
              href="#chart-main"
              aria-label="Agentrader grafik"
            >
              <span>a</span>
            </a>
            <label className="shell-symbol">
              <select
                aria-label="Sözleşme seç"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
              >
                {markets.length ? (
                  markets.map((m) => (
                    <option key={m.symbol} value={m.symbol}>
                      {m.symbol}
                    </option>
                  ))
                ) : (
                  <option value="BTCUSDT">BTCUSDT</option>
                )}
              </select>
            </label>
            <button
              className="icon-button shell-command-trigger"
              aria-label="Hızlı erişimi aç"
              title="Sembol, araç veya zaman dilimi ara · Ctrl+K"
              onClick={() => setCommandMode("symbols")}
            >
              <Icon name="search" />
            </button>
            <div className="shell-divider" />
            <div className="intervals" role="group" aria-label="Zaman dilimi">
              {intervals.map((i) => (
                <button
                  key={i}
                  className={interval === i ? "active" : ""}
                  onClick={() => setIntervalValue(i)}
                  aria-pressed={interval === i}
                >
                  {labels[i]}
                </button>
              ))}
            </div>
            <span className="shell-divider" />
            <span className="shell-chart-kind" title="Mum grafiği">
              <Icon name="candle" />
            </span>
            <ShellMenu label="Göstergeler" icon="indicator">
              <button
                disabled={!indicatorConfig.ready || indicatorConfig.busy}
                aria-pressed={showEma}
                onClick={() => setShowEma((v) => !v)}
              >
                <span>EMA</span>
                <small>
                  {fast.period} / {slow.period}
                </small>
                <b>{showEma ? "✓" : ""}</b>
              </button>
              <button
                disabled={!indicatorConfig.ready || indicatorConfig.busy}
                aria-pressed={showRsi}
                onClick={() => setShowRsi((v) => !v)}
              >
                <span>RSI</span>
                <small>
                  {oscillator.period} · {oscillator.source.toUpperCase()}
                </small>
                <b>{showRsi ? "✓" : ""}</b>
              </button>
              {[
                simple,
                volatility,
                convergence,
                bands,
                sessionVwap,
                anchoredVwap,
              ].map((c) => (
                <button
                  key={c.indicator_id}
                  disabled={!indicatorConfig.ready || indicatorConfig.busy}
                  aria-label={c.kind + " göstergesi"}
                  aria-pressed={c.enabled}
                  onClick={() =>
                    setExtra(
                      c.kind as
                        | "SMA"
                        | "ATR"
                        | "MACD"
                        | "BB"
                        | "SESSION_VWAP"
                        | "ANCHORED_VWAP",
                      !c.enabled,
                    )
                  }
                >
                  <span>{indicatorName(c)}</span>
                  <small>
                    {c.kind === "SESSION_VWAP"
                      ? "UTC"
                      : c.kind === "ANCHORED_VWAP"
                        ? "Çapa"
                        : c.period}
                  </small>
                  <b>{c.enabled ? "✓" : ""}</b>
                </button>
              ))}
              <button
                disabled={!indicatorConfig.ready || indicatorConfig.busy}
                onClick={() => setIndicatorSettingsOpen(true)}
              >
                <span>Gösterge ayarları</span>
              </button>
              {indicatorConfig.error && (
                <p role="alert">{indicatorConfig.error}</p>
              )}
              {(!indicatorConfig.ready || indicatorConfig.error) && (
                <button
                  disabled={indicatorConfig.busy}
                  onClick={() => void indicatorConfig.reload()}
                >
                  Gösterge ayarlarını yeniden yükle
                </button>
              )}
            </ShellMenu>
            <button
              className="shell-button"
              aria-label="Alarm oluştur ve yönet"
              onClick={() => {
                setAlertInitialView("editor");
                setAlertsOpen(true);
              }}
            >
              <Icon name="bell" />
              <span>Alarm</span>
              {alertNotifications.unread > 0 && (
                <span
                  className="alert-unread-badge"
                  aria-label={alertNotifications.unread + " okunmamış alarm"}
                >
                  {alertNotifications.unread}
                </span>
              )}
              {(alertNotifications.error ||
                alertNotifications.deliveryError ||
                alertNotifications.storageError) && (
                <span
                  className="alert-notification-warning"
                  title={
                    alertNotifications.error ||
                    alertNotifications.deliveryError ||
                    alertNotifications.storageError
                  }
                  aria-label={
                    alertNotifications.error ||
                    alertNotifications.deliveryError ||
                    alertNotifications.storageError
                  }
                >
                  !
                </span>
              )}
            </button>
            <ShellMenu label="Paneller" icon="panes">
              <button
                disabled={!profiles.ready}
                aria-label="Hacim paneli"
                aria-pressed={showVolume}
                onClick={() => setShowVolume((v) => !v)}
              >
                <span>Hacim paneli</span>
                <b>{showVolume ? "✓" : ""}</b>
              </button>
              <button
                disabled={!indicatorConfig.ready || indicatorConfig.busy}
                aria-label="RSI paneli"
                aria-pressed={showRsi}
                onClick={() => setShowRsi((v) => !v)}
              >
                <span>RSI paneli</span>
                <b>{showRsi ? "✓" : ""}</b>
              </button>
              <button
                aria-pressed={panePreset === "price-focus"}
                onClick={() => setLayoutPreset("price-focus")}
              >
                <span>Fiyat alanını büyüt</span>
              </button>
              <button onClick={resetPaneLayout}>
                <span>Panel boyutlarını sıfırla</span>
              </button>
              <button
                disabled={
                  drawings.loading || !indicatorConfig.ready || !profiles.ready
                }
                onClick={() => setBindingsOpen(true)}
              >
                <span>Araç / kural bağları</span>
              </button>
              <button onClick={() => setLocalEventsOpen(true)}>
                <span>Yerel olay geçmişi</span>
              </button>
              <button onClick={() => setReplayValidationOpen(true)}>
                <span>Kuru çalışma sonuçları</span>
              </button>
              <p>Ayırıcıları sürükleyerek boyutlandır.</p>
            </ShellMenu>
            <div
              className="shell-drawing-history"
              role="group"
              aria-label="Çizim geçmişi"
            >
              <button
                className="icon-button"
                aria-label="Geri al"
                title="Geri al · Ctrl+Z"
                disabled={toolDisabled || !drawings.canUndo}
                onClick={() => {
                  cancelCreation();
                  void drawings.undoLast();
                }}
              >
                <Icon name="undo" />
              </button>
              <button
                className="icon-button"
                aria-label="Yeniden yap"
                title="Yeniden yap · Ctrl+Shift+Z / Ctrl+Y"
                disabled={toolDisabled || !drawings.canRedo}
                onClick={() => {
                  cancelCreation();
                  void drawings.redoLast();
                }}
              >
                <Icon name="redo" />
              </button>
            </div>
            <div className="shell-header-end">
              <button
                className="shell-button"
                aria-label="Çizimleri kopyala"
                disabled={
                  drawings.loading ||
                  drawings.busy ||
                  drawings.retryable ||
                  !drawings.selectedIds.length
                }
                onClick={() => setClipboardMode("copy")}
              >
                Kopyala
              </button>
              <button
                className="shell-button"
                aria-label="Çizimleri yapıştır"
                disabled={
                  drawings.loading || drawings.busy || drawings.retryable
                }
                onClick={() => setClipboardMode("paste")}
              >
                Yapıştır
              </button>
              <button
                className="workspace-trigger"
                title="Çalışma alanı ve şablonlar"
                disabled={
                  !profiles.ready ||
                  profiles.busy ||
                  !indicatorConfig.ready ||
                  indicatorConfig.busy ||
                  drawings.loading ||
                  drawings.busy ||
                  drawings.retryable
                }
                aria-label="Çalışma alanı şablonları"
                onClick={() => setTemplatesOpen(true)}
              >
                <Icon name="layers" />
                <span className="workspace-label">Çalışma alanı</span>
              </button>
              <button
                disabled={!profiles.ready}
                className="icon-button"
                aria-label={
                  theme === "dark" ? "Açık temaya geç" : "Koyu temaya geç"
                }
                title={theme === "dark" ? "Açık tema" : "Koyu tema"}
                onClick={() =>
                  setTheme((t) => (t === "dark" ? "light" : "dark"))
                }
              >
                <Icon name={theme === "dark" ? "sun" : "moon"} />
              </button>
              <button
                className="icon-button"
                title={
                  fullscreenActive ? "Tam ekrandan çık" : "Grafiği tam ekran aç"
                }
                aria-label={
                  fullscreenActive ? "Tam ekrandan çık" : "Grafiği tam ekran aç"
                }
                aria-pressed={fullscreenActive}
                onClick={() => {
                  setFullscreenError("");
                  const panel =
                    host.current?.closest<HTMLElement>(".chart-panel");
                  const action = document.fullscreenElement
                    ? document.exitFullscreen()
                    : panel?.requestFullscreen();
                  action?.catch(() =>
                    setFullscreenError(
                      "Tam ekran açılamadı. Tarayıcı iznini kontrol edip yeniden deneyebilirsin.",
                    ),
                  );
                }}
              >
                <Icon name="expand" />
              </button>
              <span className="shell-execution">İşlem kapalı</span>
            </div>
          </header>
          <div className="shell-workbench">
            <nav className="drawing-tools" aria-label="Çizim araçları">
              {toolButton("cursor", "İmleç", "cursor")}
              <span className="rail-separator" />
              <ShellMenu label="Çizgi araçları" icon="trend" rail>
                {toolButton("trend", "Trend çizgisi", "trend")}
                {toolButton("line", "Yatay çizgi", "line")}
                {toolButton("ray", "Işın", "trend")}
                {toolButton("extended_line", "Uzatılmış çizgi", "trend")}
                {toolButton("horizontal_ray", "Yatay ışın", "line")}
                {familyKinds
                  .filter((k) => !isPitchfork(k))
                  .map((k) => toolButton(k, familyNames[k], "channel"))}
              </ShellMenu>
              <ShellMenu label="Pitchfork araçları" icon="pitchfork" rail>
                {familyKinds
                  .filter(isPitchfork)
                  .map((k) => toolButton(k, familyNames[k], "pitchfork"))}
              </ShellMenu>
              {toolButton("zone", "Fiyat bölgesi", "zone")}
              <ShellMenu label="Fibonacci araçları" icon="fibonacci" rail>
                {toolButton("fibonacci", "Fibonacci", "fibonacci")}
                {toolButton(
                  "fibonacci_extension",
                  "Fibonacci extension",
                  "fibonacci",
                )}
                {toolButton(
                  "fibonacci_projection",
                  "Fibonacci projection",
                  "fibonacci",
                )}
              </ShellMenu>
              {toolButton("ruler", "Fiyat-zaman cetveli", "ruler")}
              <ShellMenu label="Açıklama araçları" icon="text" rail>
                {toolButton("text", "Metin", "text")}
                {toolButton("note", "Not", "note")}
                {toolButton("price_label", "Fiyat etiketi", "price-label")}
              </ShellMenu>
              <ShellMenu label="Planlama araçları" icon="position" rail>
                {toolButton("long_plan", "Long plan", "position")}
                {toolButton("short_plan", "Short plan", "position")}
              </ShellMenu>
              <button
                aria-label="Araç ara"
                title="Araç ara"
                onClick={() => setCommandMode("tools")}
              >
                <Icon name="search" />
                <span>Araç ara</span>
              </button>
              <span className="rail-separator" />
              <button
                aria-label="Mıknatıs"
                aria-pressed={magnet}
                title="Mıknatıs: yeni noktayı yakın OHLC değerine yaklaştır"
                className={magnet ? "active" : ""}
                onClick={() => setMagnet((v) => !v)}
              >
                <Icon name="magnet" />
                <span>Mıknatıs</span>
              </button>
              <div className="rail-bottom">
                <ShellMenu label="Grafik kısayolları" icon="help" rail>
                  <p>Grafik odaktayken</p>
                  <p>← → Kaydır · + − Yakınlaştır</p>
                  <p>End Güncel mum · Esc İptal</p>
                  <p>V İmleç · T Trend · H Yatay</p>
                  <p>B Bölge · F Fibonacci · R Cetvel</p>
                  <p>/ Piyasa ara · , Zaman dilimi</p>
                  <p>Ctrl+K Hızlı erişim</p>
                </ShellMenu>
              </div>
            </nav>
            <div className="shell-chart-column">
              {profiles.error && !templatesOpen && (
                <div className="chart-data-notice" role="alert">
                  {profiles.error}{" "}
                  <button
                    disabled={profiles.busy}
                    onClick={() => void reloadProfiles()}
                  >
                    Çalışma alanını yeniden yükle
                  </button>
                </div>
              )}
              {indicatorConfig.error && !indicatorSettingsOpen && (
                <div className="chart-data-notice" role="alert">
                  {indicatorConfig.error}{" "}
                  <button
                    disabled={indicatorConfig.busy}
                    onClick={() => void indicatorConfig.reload()}
                  >
                    Gösterge ayarlarını yeniden yükle
                  </button>
                </div>
              )}
              <div className="chart-content">
                <div
                  className={
                    "chart-stage " + (tool !== "cursor" ? "placing-line" : "")
                  }
                  tabIndex={0}
                  role="region"
                  aria-label="Fiyat grafiği"
                  aria-describedby="chart-keyboard-help"
                  data-has-data={activeView.candles.length > 0}
                >
                  <div className="chart-overlay">
                    <div className="shell-instrument">
                      <b>{selected?.base_asset ?? "BTC"} / USDT</b>
                      <span>· {labels[interval]} · Binance Demo USD-M</span>
                      <span
                        className={
                          "shell-state " +
                          (activeView.status === "LIVE" ? "is-live" : "")
                        }
                        title={statusLabels[activeView.status]}
                      >
                        {statusLabels[activeView.status] ?? activeView.status}
                      </span>
                    </div>
                    <OhlcReadout
                      key={symbol + ":" + interval}
                      chart={chart.current}
                      series={series.current}
                      rows={context.renderError ? [] : activeView.candles}
                      tick={Number(selected?.tick_size ?? 0)}
                    />
                    <div className="shell-last">
                      <strong>{number(last?.close, decimals)}</strong>
                      <span
                        className={
                          change !== undefined && change < 0
                            ? "negative"
                            : "positive"
                        }
                      >
                        {change === undefined
                          ? "—"
                          : (change >= 0 ? "+" : "") + number(change, 2) + "%"}
                      </span>
                      <small>Hacim {volume(last?.volume)}</small>
                    </div>
                  </div>
                  <div className="chart-host" ref={host} />
                  <DrawingLayer
                    onPreview={setDragGeometry}
                    viewScale={viewScale}
                    symbol={symbol}
                    chart={chart.current}
                    series={series.current}
                    rows={activeView.candles}
                    items={visibleDrawings.items}
                    selected={drawings.selected}
                    selectedIds={drawings.selectedIds}
                    select={drawings.select}
                    changeMany={drawings.changeMany}
                    change={(id, g) => drawings.change(id, g)}
                    interval={interval}
                    tick={selected?.tick_size ?? ""}
                    disabled={toolDisabled || tool !== "cursor"}
                  />
                  <DrawingInteraction
                    dragGeometry={dragGeometry}
                    host={host.current}
                    chart={chart.current}
                    series={series.current}
                    rows={activeView.candles}
                    symbol={symbol}
                    interval={interval}
                    tick={selected?.tick_size ?? "0.01"}
                    tool={tool}
                    first={zoneStart.current}
                    second={positionStop.current}
                    viewScale={viewScale}
                    items={visibleDrawings.items}
                    selected={drawings.selected}
                    disabled={toolDisabled}
                    magnet={magnet}
                  />
                  {tool === "cursor" && !drawings.loading && (
                    <DrawingToolbar
                      manager={visibleDrawings}
                      rows={activeView.candles}
                      interval={interval}
                      tick={selected?.tick_size ?? "0.01"}
                      viewScale={viewScale}
                      onClose={() => drawings.setSelected(null)}
                    />
                  )}
                  <PaneLegends
                    chart={chart.current}
                    host={host.current}
                    volume={showVolume ? histogram.current : null}
                    rsi={showRsi ? rsiSeries.current : null}
                    context={symbol + ":" + interval + ":" + paneVersion}
                    onHideVolume={() => setShowVolume(false)}
                    onHideRsi={() => setShowRsi(false)}
                    rsiLabel={"RSI " + oscillator.period}
                    atr={volatility.enabled ? atrSeries.current : null}
                    atrLabel={"ATR " + volatility.period}
                    onHideAtr={() => setExtra("ATR", false)}
                    macd={convergence.enabled ? macdLine.current : null}
                    onHideMacd={() => setExtra("MACD", false)}
                  />
                  {!activeView.candles.length && (
                    <div className="chart-empty">
                      <Icon name="candle" />
                      <h2>
                        {catalogError
                          ? "Piyasa verisine ulaşılamıyor"
                          : ["CONNECTING", "SYNCING", "RECONNECTING"].includes(
                                activeView.status,
                              )
                            ? "Grafik hazırlanıyor"
                            : (statusLabels[activeView.status] ??
                              "Veri bekleniyor")}
                      </h2>
                      <p>
                        {catalogError ||
                        ["ERROR", "STOPPED"].includes(activeView.status)
                          ? "Bağlantıyı kontrol edip yeniden deneyebilirsin."
                          : activeView.status === "EMPTY"
                            ? "Bu bağlam için henüz mum verisi gelmedi."
                            : "Mum verisi ve canlı bağlantı bekleniyor."}
                      </p>
                      <button
                        onClick={() => {
                          refreshCatalog();
                          setRevision((v) => v + 1);
                        }}
                        className="retry-button"
                      >
                        Yeniden bağlan
                      </button>
                    </div>
                  )}
                  {tool !== "cursor" && (
                    <div className="tool-hint" role="status">
                      {creationNotice ||
                        (annotationKinds.includes(tool)
                          ? "Fiyat grafiğinde bir noktaya tıkla; metni açılan çizim çubuğundan düzenle."
                          : familyKinds.includes(tool as FamilyKind)
                            ? tool === "regression_channel"
                              ? "Hesaplanacak mum aralığının başlangıcını ve sonunu seç."
                              : isPitchfork(tool)
                                ? "Sırasıyla başlangıç, ikinci salınım ve üçüncü salınım noktasını seç."
                                : "Temel çizginin ilk ve ikinci noktasını, ardından karşı sınırın fiyatını seç."
                            : ["long_plan", "short_plan"].includes(tool)
                              ? "Giriş fiyatını seç; ardından stop ve hedefi yerleştir."
                              : ![
                                    "line",
                                    "horizontal_ray",
                                    ...annotationKinds,
                                  ].includes(tool)
                                ? "İlk noktayı, ardından ikinci noktayı seç."
                                : "Yatay çizgi için fiyat grafiğine tıkla.")}
                      <span>Esc · İptal</span>
                    </div>
                  )}
                </div>
              </div>
              {activeView.candles.length > 0 &&
                activeView.status !== "LIVE" && (
                  <div className="chart-data-notice" role="status">
                    {statusLabels[activeView.status] ?? activeView.status} ·{" "}
                    {context.renderError
                      ? "Grafik görüntüsü doğrulanamadı."
                      : "Son alınan veri gösteriliyor."}
                  </div>
                )}
              {viewportNotice && <div className="chart-data-notice" role="status">{viewportNotice}</div>}
              {activeView.consumer_clock_untrusted && <div className="chart-data-notice" role="status">Sistem saati değişti. Zaman doğrulaması için yeniden bağlanılıyor. <button onClick={()=>setRevision(v=>v+1)}>Yeniden bağlan</button></div>}
              {dateLocating && <div className="chart-data-notice" role="status">İstenen tarih yükleniyor… <button onClick={()=>cancelViewportRestore.current()}>Aramayı iptal et</button></div>}
              {historyLoadState!=='READY' && historyLoadState!=='LOADING' && <div className="history-load-notice" role={historyError?'alert':'status'}>{historyLoadLabels[historyLoadState]}{historyError&&<button onClick={()=>void loadOlder.current()}>Geçmişi yeniden dene</button>}</div>}
              {dateDialogOpen && <GoToDateDialog initialTime={activeView.candles.at(-1)?.time??Math.floor(Date.now()/1000)} onGo={time=>goToDate.current(time)} onClose={()=>setDateDialogOpen(false)}/>}
              <div className="chart-bottom">
                <button className="text-button" disabled={!activeView.candles.length} onClick={()=>setDateDialogOpen(true)}>Tarihe git</button>
                <button
                  className="text-button"
                  disabled={!activeView.candles.length}
                  onClick={goLive}
                >
                  <Icon name="latest" />
                  Güncel
                </button>
                <button
                  className="icon-button"
                  title="Görünümü sıfırla"
                  aria-label="Görünümü sıfırla"
                  disabled={!activeView.candles.length}
                  onClick={resetView}
                >
                  <Icon name="reset" />
                </button>
                <button
                  className="text-button shell-history"
                  disabled={
                    !hasMore || historyBusy || !activeView.candles.length
                  }
                  onClick={() => void loadOlder.current()}
                >
                  {historyBusy
                    ? "Yükleniyor…"
                    : hasMore
                      ? "Eski mumları yükle"
                      : historyLoadState==='LIMIT'?"4000 mum sınırı":"Geçmiş başlangıcı"}
                </button>
                {historyError && context.matches && (
                  <span className="history-error" role="alert">
                    Geçmiş alınamadı · Yeniden dene.
                  </span>
                )}
                <span className="shell-bottom-spacer" />
                <CandleCountdown view={activeView}/>
                {viewScale === "LOG" && (
                  <span
                    className="log-scale-notice"
                    role="status"
                    title="Yeni kanal ve pitchfork araçları log ölçekte düzenlenebilir. Eski trend, ışın ve paralel kanal kayıtları için lineer görünümü kullan."
                  >
                    Log: eski eğimli araçlar kapalı
                  </span>
                )}
                <span className="loaded-count">
                  {activeView.candles.length} mum
                </span>
                <span className="shell-timezone">UTC</span>

                <ViewScaleControl
                  mode={viewScale}
                  ready={!!series.current}
                  onChange={changeViewScale}
                />
                <PriceScaleControl
                  series={series.current}
                  host={host.current}
                  context={symbol + ":" + interval + ":" + revision}
                />
              </div>
              {fullscreenError && (
                <p className="shell-error" role="alert">
                  {fullscreenError}
                </p>
              )}
              {new URLSearchParams(location.search).get("diagnostics") ===
                "1" && (
                <div className="shell-diagnostics">
                  <AlignmentPanel
                    viewScale={viewScale}
                    chart={chart.current}
                    series={series.current}
                    rows={activeView.candles}
                    items={visibleDrawings.items}
                    symbol={symbol}
                    interval={interval}
                  />
                  <PerformancePanel
                    candles={activeView.candles.length}
                    drawings={drawings.items.length}
                    status={activeView.status}
                    symbol={symbol}
                    interval={interval}
                  />
                </div>
              )}
            </div>
            <aside
              className="shell-side"
              hidden={panel === null}
              aria-label={
                panel === "drawings"
                  ? "Çizim paneli"
                  : panel === "data"
                    ? "Veri paneli"
                    : "Piyasa paneli"
              }
            >
              <div className="shell-side-heading">
                <div role="group" aria-label="Yan panel">
                  <button
                    aria-pressed={panel === "markets"}
                    onClick={() => setPanel("markets")}
                  >
                    Piyasalar
                  </button>
                  <button
                    aria-pressed={panel === "drawings"}
                    onClick={() => setPanel("drawings")}
                  >
                    Çizimler
                  </button>
                  <button
                    aria-pressed={panel === "data"}
                    onClick={() => setPanel("data")}
                  >
                    Veri
                  </button>
                </div>
                <button
                  className="icon-button"
                  aria-label="Yan paneli kapat"
                  title="Paneli kapat"
                  onClick={() => setPanel(null)}
                >
                  <Icon name="close" />
                </button>
              </div>
              <div
                id="market-panel"
                className="shell-markets"
                hidden={panel !== "markets"}
              >
                <label className="search">
                  <Icon name="search" />
                  <input
                    value={query}
                    onChange={(e) => {
                      setQuery(e.target.value);
                      setMarketLimit(80);
                    }}
                    placeholder="Sözleşme ara"
                    aria-label="Coin ara"
                  />
                  <kbd>/</kbd>
                </label>
                <div
                  className="watchlist-filters"
                  role="group"
                  aria-label="Piyasa listesi filtresi"
                >
                  <button
                    aria-pressed={!favoritesOnly}
                    onClick={() => {
                      setFavoritesOnly(false);
                      setMarketLimit(80);
                    }}
                  >
                    Tümü
                  </button>
                  <button
                    aria-pressed={favoritesOnly}
                    onClick={() => {
                      setFavoritesOnly(true);
                      setMarketLimit(80);
                    }}
                  >
                    <Icon name="star" />
                    Favoriler
                  </button>
                </div>
                {!query &&
                  !favoritesOnly &&
                  recentSymbols.some((s) =>
                    markets.some((m) => m.symbol === s),
                  ) && (
                    <div
                      className="recent-markets"
                      aria-label="Son kullanılan sözleşmeler"
                    >
                      <span>Son kullanılan</span>
                      <div>
                        {recentSymbols
                          .filter((s) => markets.some((m) => m.symbol === s))
                          .slice(0, 4)
                          .map((s) => (
                            <button
                              key={s}
                              onClick={() => setSymbol(s)}
                              aria-label={s + " sözleşmesine dön"}
                            >
                              {s.replace(/USDT$/, "")}
                            </button>
                          ))}
                      </div>
                    </div>
                  )}
                <div className="list-caption">
                  <span>SÖZLEŞME</span>
                  <span>{matchedMarkets.length} SONUÇ</span>
                </div>
                <div className="market-list">
                  {filtered.map((m) => (
                    <div key={m.symbol} className="market-row-wrap">
                      <button
                        className={
                          "market-row " +
                          (symbol === m.symbol ? "selected" : "")
                        }
                        aria-pressed={symbol === m.symbol}
                        onClick={() => setSymbol(m.symbol)}
                      >
                        <span className="coin-icon">
                          {m.base_asset.slice(0, 1)}
                        </span>
                        <span className="market-name">
                          <b>
                            {m.base_asset}
                            <small>USDT</small>
                          </b>
                          <small>Sürekli vadeli</small>
                        </span>
                        <span className="quote">USD-M</span>
                      </button>
                      <button
                        className="market-favorite"
                        aria-label={m.symbol + " favorisi"}
                        aria-pressed={favorites.includes(m.symbol)}
                        title={
                          favorites.includes(m.symbol)
                            ? "Favorilerden çıkar"
                            : "Favorilere ekle"
                        }
                        onClick={() => toggleFavorite(m.symbol)}
                      >
                        <Icon name="star" />
                      </button>
                    </div>
                  ))}
                  {matchedMarkets.length > marketLimit && (
                    <button
                      className="market-more"
                      onClick={() => setMarketLimit((n) => n + 80)}
                    >
                      80 sözleşme daha göster
                    </button>
                  )}
                  {!markets.length && !catalogError && (
                    <p className="aside-note">Piyasalar yükleniyor…</p>
                  )}
                  {catalogError && (
                    <div className="aside-note">
                      <p>Piyasa listesi alınamadı.</p>
                      <button className="text-button" onClick={refreshCatalog}>
                        Yeniden dene
                      </button>
                    </div>
                  )}
                  {matchedMarkets.length === 0 && markets.length > 0 && (
                    <p className="aside-note">
                      {favoritesOnly && !query
                        ? "Henüz favori sözleşme yok. Yıldız ile kendi listeni oluştur."
                        : "Eşleşen sözleşme yok."}
                    </p>
                  )}
                </div>
                <div className="aside-footer">
                  Binance Demo USD-M
                  <small>
                    {markets.length || "—"} USDT sözleşmesi · Son işlem fiyatı
                  </small>
                </div>
              </div>
              <div
                id="drawing-panel"
                className="shell-drawings"
                hidden={panel !== "drawings"}
              >
                <DrawingPanel
                  viewScale={viewScale}
                  manager={visibleDrawings}
                  tick={selected?.tick_size ?? ""}
                  rows={context.renderError ? [] : activeView.candles}
                  interval={interval}
                />
              </div>
              <div
                id="data-panel"
                className="shell-data"
                hidden={panel !== "data"}
              >
                <DataWindow
                  key={symbol + ":" + interval}
                  symbol={symbol}
                  interval={interval}
                  view={activeView}
                  chart={chart.current}
                  series={series.current}
                  tick={Number(selected?.tick_size ?? ".01")}
                  showEma={showEma}
                  showRsi={showRsi}
                  indicators={indicatorConfig.items}
                  anchorBusy={!indicatorConfig.ready || indicatorConfig.busy}
                  onSetVwapAnchor={(row) =>
                    void indicatorConfig.save(
                      indicatorConfig.items.map((c) =>
                        c.kind === "ANCHORED_VWAP"
                          ? {
                              ...c,
                              enabled: true,
                              params: {
                                ...c.params,
                                anchor_time: row.time,
                                anchor_symbol: symbol,
                              },
                            }
                          : c,
                      ),
                    )
                  }
                  drawings={{
                    loading: drawings.loading,
                    busy: drawings.busy,
                    message: drawings.message,
                    retryable: drawings.retryable,
                    count: visibleDrawings.items.length,
                  }}
                  history={{
                    busy: historyBusy && context.matches,
                    error: historyError && context.matches,
                  }}
                  onRefreshDrawings={() => void drawings.refresh()}
                />
              </div>
            </aside>
            <nav className="shell-right-rail" aria-label="Panel kontrolleri">
              <button
                className={panel === "markets" ? "active" : ""}
                aria-label="Piyasaları göster veya gizle"
                aria-expanded={panel === "markets"}
                aria-controls="market-panel"
                title="Piyasalar"
                onClick={() => togglePanel("markets")}
              >
                <Icon name="markets" />
              </button>
              <button
                className={panel === "drawings" ? "active" : ""}
                aria-label="Çizimleri göster veya gizle"
                aria-expanded={panel === "drawings"}
                aria-controls="drawing-panel"
                title="Çizimler"
                onClick={() => togglePanel("drawings")}
              >
                <Icon name="layers" />
              </button>
              <button
                className={panel === "data" ? "active" : ""}
                aria-label="Veri penceresini göster veya gizle"
                aria-expanded={panel === "data"}
                aria-controls="data-panel"
                title="Veri penceresi"
                onClick={() => togglePanel("data")}
              >
                <Icon name="data" />
              </button>
            </nav>
          </div>
          <footer className="statusbar">
            <div
              className={
                "connection " + (activeView.status === "LIVE" ? "live" : "")
              }
              role="status"
            >
              <i />
              {statusLabels[activeView.status] ?? activeView.status}
            </div>
            <span>
              Binance Demo USD-M <span className="separator">/</span> Son işlem
              fiyatı
            </span>
            <span className="update-time">
              Son veri{" "}
              {activeView.received_at
                ? new Date(activeView.received_at).toLocaleTimeString("tr-TR", { timeZone: "UTC" }) + " UTC"
                : "—"}
            </span>
            <a
              href="https://www.tradingview.com/"
              target="_blank"
              rel="noreferrer"
            >
              Lightweight Charts™
            </a>
            <span className="version">İşlem yürütme kapalı</span>
          </footer>
          {commandMode && (
            <ChartCommandDialog
              viewScale={viewScale}
              initialMode={commandMode}
              markets={markets}
              symbol={symbol}
              interval={interval}
              tool={tool}
              toolsDisabled={toolDisabled || !drawings.available}
              catalogError={catalogError}
              onSymbol={setSymbol}
              onTool={chooseTool}
              onInterval={setIntervalValue}
              onClose={() => setCommandMode(null)}
              onRetry={refreshCatalog}
            />
          )}
          <p id="chart-keyboard-help" className="visually-hidden">
            Grafik odaktayken oklarla kaydır, artı ve eksi ile yakınlaştır, End
            ile güncel mumlara dön. Escape ile çizimi iptal et. Ctrl+Z geri al,
            Ctrl+Shift+Z veya Ctrl+Y yeniden yap, Delete seçili çizimi sil.
          </p>
        </section>
      </main>
    </div>
  );
}
