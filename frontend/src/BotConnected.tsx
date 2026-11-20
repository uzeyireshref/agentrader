import BotPlanAnalytics from './BotPlanAnalytics';
import { useVisiblePolling } from "./useVisiblePolling";
import { useEffect, useRef, useState } from "react";
import BotPlanForm from "./BotPlanForm";
import BotFeedback from "./BotFeedback";
import BotLiveReview from "./BotLiveReview";
import BotLiveCommands from "./BotLiveCommands";
import {
  botRequest,
  runBotJob,
  draftForServer,
  type BotJob,
  type BotStatus,
  type BotSnapshot,
  type BotReviewResult,
  type CommandInput,
} from "./botApi";
import { jobOutcome } from "./botOutcome";
import {workerCanRead,workerIssue} from "./botConnection";
import { draftError, type BotDraft } from "./botPrototype";
type Props = {
  draft: BotDraft;
  onDraft: (d: BotDraft) => void;
  onChart: (s: string) => void;
  symbols?: string[];
  sourceChanged?: boolean;
  compact?: boolean;
  onTerminal?: () => void;
  active?: boolean;
};
export default function BotConnected({
  draft,
  onDraft,
  onChart,
  symbols,
  sourceChanged,
  compact,
  onTerminal,
  active = true,
}: Props) {
  const [session, setSession] = useState<{
      enabled: boolean;
      authenticated: boolean;
    } | null>(null),
    [token, setToken] = useState(""),
    [status, setStatus] = useState<BotStatus | null>(null),
    [snapshot, setSnapshot] = useState<BotSnapshot | null>(null),
    [jobs, setJobs] = useState<BotJob[]>([]),
    [showReadings,setShowReadings] = useState(false),
    [busy, setBusy] = useState(false),
    [refreshing, setRefreshing] = useState(false),
    [error, setError] = useState(""),
    [tab, setTab] = useState(() => {
      const section = new URLSearchParams(window.location.search).get(
        "section",
      );
      return [
        "Hesap",
        "Yeni işlem",
        "Emirler",
        "Yönetim",
        "Kayıtlar",
        "Geri bildirim",
      ].includes(section ?? "")
        ? section!
        : "Hesap";
    }),
    [review, setReview] = useState<{
      job: BotJob;
      value: BotReviewResult;
    } | null>(null),
    [now, setNow] = useState(Date.now());
  const gate = useRef(false);
  const noticeRef = useRef<HTMLParagraphElement>(null);
  const live = useRef(true);
  const refreshSerial = useRef(0);
  const accountReading = useRef(false);
  const analyticsReading = useRef(false);
  const nextAccountRead = useRef(0);
  const accountSerial = useRef(0);
  const fail = (e: unknown) => {
    if (live.current)
      setError(
        e instanceof Error
          ? e.message
          : "Bağlantı doğrulanamadı. Kayıtlı iş kimliğini kontrol edin.",
      );
  };
  async function statusRefresh(includeSnapshots=showReadings) {
    const generation = ++refreshSerial.current;
    let s = await botRequest<{
      enabled: boolean;
      authenticated: boolean;
      local_auto_login?: boolean;
    }>("/api/session");
    if (!s.authenticated && s.local_auto_login) {
      const response = await fetch("/api/session", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-Agentrader-Local-Session": "1" },
      });
      if (!response.ok)
        throw Error("Yerel oturum açılamadı. Sayfayı yenileyin.");
      s = await response.json();
    }
    if (!live.current || generation !== refreshSerial.current) return;
    setSession(s);
    if (!s.authenticated) {
      setStatus(null);
      setSnapshot(null);
      setJobs([]);
      setReview(null);
      accountSerial.current++;
    }
    if (s.authenticated) {
      const [st, j] = await Promise.all([
        botRequest<BotStatus>("/api/bot/status"),
        botRequest<{ jobs: BotJob[] }>("/api/bot/jobs?summary=true&include_snapshots="+includeSnapshots),
      ]);
      if (live.current && generation === refreshSerial.current) {
        setStatus(st);
        setJobs((previous) =>
          j.jobs.map((row) =>
            row.result_loaded === false
              ? {
                  ...row,
                  result:
                    previous.find(
                      (old) =>
                        old.job_id === row.job_id &&
                        old.updated_at === row.updated_at,
                    )?.result ?? null,
                }
              : row,
          ),
        );
        return st;
      }
    }
  }
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
      refreshSerial.current++;
      accountSerial.current++;
    };
  }, []);
  useVisiblePolling(async () => {
    if (!active) return;
    setNow(Date.now());
    const st = await statusRefresh();
    if (workerCanRead(st) && !review &&
        !gate.current && Date.now() >= nextAccountRead.current) {
      if (!analyticsReading.current) await refreshAccount();
    }
  }, fail, 5000, active);

  async function refreshAccount() {
    if (!active || !live.current || accountReading.current || gate.current ||
        document.visibilityState === "hidden") return;
    accountReading.current = true;
    const generation = ++accountSerial.current;
    nextAccountRead.current = Date.now() + 10000;
    setRefreshing(true);
    try {
      const job = await runBotJob<BotSnapshot>("SNAPSHOT", { symbol: draft.symbol });
      if (!live.current || generation !== accountSerial.current) return;
      if (job.state !== "SUCCEEDED" || !job.result)
        throw Error("Hesap görünümü henüz doğrulanamadı. Hesabı yenileyin.");
      setSnapshot(job.result);
      setNow(Date.now());
      nextAccountRead.current = job.result.observed_at * 1000 + 10000;
    } catch (error) {
      nextAccountRead.current = Date.now() + 30000;
      fail(error);
    } finally {
      accountReading.current = false;
      if (live.current) setRefreshing(false);
    }
  }

  async function task<T = unknown>(
    action: string,
    payload: Record<string, unknown>,
    done?: (j: BotJob<T> & { result: T }) => void,
  ) {
    if (gate.current) return;
    gate.current = true;
    setBusy(true);
    setError("");
    try {
      const j = await runBotJob<T>(action, payload, (j) =>
        setJobs((prev) => [j, ...prev.filter((x) => x.job_id !== j.job_id)]),
      );
      if (live.current) {
        setJobs((prev) => [j, ...prev.filter((x) => x.job_id !== j.job_id)]);
        if (j.state === "SUCCEEDED" && j.result !== null)
          done?.({ ...j, result: j.result });
        else
          setError(
            "İş " +
              j.state +
              " durumunda. Yeni emir göndermeden kayıtlı sonucu kontrol edin.",
          );
      }
      await statusRefresh();
    } catch (e) {
      fail(e);
      setTimeout(() => noticeRef.current?.focus(), 0);
    } finally {
      gate.current = false;
      if (live.current) setBusy(false);
    }
  }
  const refresh = () => { void refreshAccount(); };
  const preview = (command: CommandInput) =>
    task<BotReviewResult>("PREVIEW_COMMAND", command, (j) =>
      setReview({ job: j, value: j.result }),
    );
  const read = (command: CommandInput) => task("READ_COMMAND", command);
  const stale = !snapshot || now / 1000 - snapshot.observed_at > 15;
  const workerReady = workerCanRead(status);
  async function pair(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const response = await fetch("/api/session", {
        method: "POST",
        credentials: "same-origin",
        headers: { Authorization: "Bearer " + token },
      });
      setToken("");
      if (!response.ok) throw Error("Erişim anahtarı doğrulanamadı.");
      await statusRefresh();
      setError("");
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  const queued = jobs.some(
    (j) => ["PENDING", "RUNNING"].includes(j.state) && j.action === "CONFIRM",
  );
  const controlsDisabled = busy || refreshing || !workerReady || stale || queued;
  useEffect(() => {
    if (compact || !active) return;
    const url = new URL(window.location.href);
    url.searchParams.set("view", "bot");
    url.searchParams.set("section", tab);
    window.history.replaceState(window.history.state, "", url);
  }, [tab, compact, active]);
  const names: Record<string, string> = {
    SNAPSHOT: "Hesap yenileme",
    CONTEXT: "Bağlantı kontrolü",
    PREVIEW_PLAN: "Plan ön kontrolü",
    PREVIEW_COMMAND: "İşlem ön kontrolü",
    PREVIEW_CONTROL: "Bot yönetimi ön kontrolü",
    CONFIRM: "Kullanıcı onayı",
    RECONCILE: "Sonuç teyidi",
    SAVE_PLAN: "Plan taslağı",
    PREVIEW_PLAN_AUTHORIZATION: "Toplu giriş yetkisi",
    READ_COMMAND: "Hesap sorgusu",
  };

  return (
    <section
      className={
        "bot-terminal bot-connected" +
        (compact ? " bot-connected-compact" : "") +
        (tab !== "Yeni işlem" ? " bot-live-fullwidth" : "") +
        (tab === "Yeni işlem" ? " bot-live-ticket-only" : "")
      }
      aria-label="Demo hesap terminali"
    >
      <header className="bot-toolbar">
        <div className="bot-live-heading">
          <h1>{compact ? "İşlem paneli" : "Bot terminali"}</h1>
          <small>
            {draft.symbol} <span>·</span> Binance Demo
          </small>
        </div>
        <button
          className="bot-chart-link"
          onClick={() => onChart(draft.symbol)}
        >
          Grafiğe dön
        </button>
        {compact && (
          <button
            className="bot-open-terminal"
            onClick={() =>
              onTerminal ? onTerminal() : location.assign("/?view=bot")
            }
          >
            Tam terminal
          </button>
        )}
        <button disabled={busy || refreshing || !workerReady} onClick={refresh} aria-busy={refreshing}>
          {refreshing ? "Hesap yenileniyor…" : "Hesabı yenile"}
        </button>
        <span role="status">
          {!session?.authenticated
            ? "Yerel oturum kapalı"
            : status
              ? status.worker === "FRESH"
                ? status.execution_enabled
                  ? "Demo işlemleri açık"
                  : "Demo hesabı · salt okunur"
                : "Hesap bağlantısı kapalı"
              : "Bağlantı kontrol ediliyor"}
        </span>
      </header>
      {session?.authenticated&&status?.queue&&status.queue.pending+status.queue.running>0&&<p className="bot-queue-status" role="status">Kuyrukta {status.queue.pending} talep · İşleniyor {status.queue.running}{(status.queue.oldest_pending_age_seconds??0)>30&&<> · En eski talep {status.queue.oldest_pending_age_seconds} saniyedir bekliyor</>}</p>}
      {error && (
        <p ref={noticeRef} tabIndex={-1} role="alert" className="bot-live-notice">
          {error}
          <button onClick={() => setError("")}>Kapat</button>
        </p>
      )}
      {!session?.authenticated ? (
        <div className="bot-live-setup">
          <h2>Yerel erişim</h2>
          <p>Hesap bilgileri ve işlem komutları kimlik doğrulama gerektirir.</p>
          {session?.enabled ? (
            <form onSubmit={pair}>
              <label>
                Web erişim anahtarı
                <input
                  type="password"
                  autoComplete="off"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                />
              </label>
              <button disabled={busy || !token}>Oturumu aç</button>
            </form>
          ) : (
            <p>
              API ortamında AGENTRADER_WEB_TOKEN tanımlayın ve API'yi yeniden
              başlatın.
            </p>
          )}
          <p>
            Borsa anahtarları yalnızca worker ortamında tutulur. Bu alana borsa
            anahtarı girmeyin.
          </p>
        </div>
      ) : (
        <>
          {!status?.enabled && (
            <div className="bot-live-setup">
              <h2>Bot bağlantısı kapalı</h2>
              <p>
                API ve worker için AGENTRADER_BOT_ENABLED=1 ayarlayın. Ayrılmış
                Demo işlem veritabanını ve risk profilini yapılandırın. Worker
                ayrı bir süreç olarak başlatılır.
              </p>
              <code>python -m agentrader web bot-worker</code>
              <p>
                Bu komut salt okunurdur. Demo yürütmesi ayrıca --execute-demo
                gerektirir.
              </p>
            </div>
          )}
          <div className="bot-metrics" hidden={compact || tab !== "Hesap"}>
            {[
              ["Cüzdan", snapshot?.account.totalWalletBalance],
              ["Kullanılabilir", snapshot?.account.availableBalance],
              ["Açık kâr / zarar", snapshot?.account.totalUnrealizedProfit],
            ].map(([label, value]) => (
              <div key={label}>
                <small>{label} · USDT</small>
                <strong>
                  {value === undefined
                    ? "—"
                    : new Intl.NumberFormat("tr-TR", {
                        maximumFractionDigits: 2,
                      }).format(Number(value))}
                </strong>
              </div>
            ))}
            <div>
              <small>Veri zamanı</small>
              <strong className="bot-data-time">
                {snapshot
                  ? new Date(snapshot.observed_at * 1000).toLocaleTimeString('tr-TR')
                  : "Bağlantı hazır"}
              </strong>
              <small>
                {stale
                  ? "Güncel hesap verisi gerekli"
                  : "Seri anlık görüntü · atomik değil"}
              </small>
            </div>
          </div>
          <nav
            className="bot-live-nav"
            hidden={compact}
            aria-label="Demo hesap bölümleri"
          >
            {[
              "Hesap",
              "Yeni işlem",
              "Emirler",
              "Yönetim",
              "Kayıtlar",
              "Geri bildirim",
            ].map((t) => (
              <button
                key={t}
                aria-pressed={tab === t}
                onClick={() => setTab(t)}
              >
                {t}
              </button>
            ))}
          </nav>
          {!compact && ["Hesap", "Yeni işlem"].includes(tab) && (
            <div className="bot-live-context">
              <div>
                <strong>
                  {tab === "Hesap"
                    ? "Hesaba genel bakış"
                    : tab === "Yeni işlem"
                      ? "Yeni işlem oluştur"
                      : tab === "Emirler"
                        ? "Açık emirler"
                        : tab === "Yönetim"
                          ? "İşlem ve hesap yönetimi"
                          : tab === "Kayıtlar"
                            ? "İşlem geçmişi ve sonuçlar"
                            : "Geri bildirim"}
                </strong>
                <span>
                  {tab === "Hesap"
                    ? "Pozisyonları ve botun yönettiği oturumları buradan takip edin."
                    : tab === "Yeni işlem"
                      ? "Planı oluşturun, hesap ön kontrolünü inceleyin ve ayrı adımda onaylayın."
                      : tab === "Emirler"
                        ? "Açık normal ve koşullu emirleri inceleyin."
                        : tab === "Yönetim"
                          ? "Önce işlem grubunu, ardından yapmak istediğiniz işlemi seçin."
                          : tab === "Kayıtlar"
                            ? "Gönderilen talepleri ve borsa sonuçlarını kimlikleriyle takip edin."
                            : "Sorunu veya önerinizi kaydedin."}
                </span>
              </div>
              {tab === "Hesap" && (
                <button
                  className="bot-new-plan"
                  onClick={() => setTab("Yeni işlem")}
                >
                  Yeni işlem oluştur
                </button>
              )}
            </div>
          )}
          {session.authenticated &&
            tab !== "Geri bildirim" &&
            tab !== "Kayıtlar" &&
            (!snapshot || stale || !status?.execution_enabled) && (
              <div className="bot-live-guidance" role="status">
                <span>
                  {!workerReady
                    ? workerIssue(status)
                    : refreshing
                      ? "Güncel hesap verileri alınıyor…"
                    : !snapshot
                    ? "Hesap görünümü otomatik alınıyor."
                    : stale
                      ? "Hesap görünümü eski. Ön kontrol için tekrar yenileyin."
                      : !status?.execution_enabled
                        ? "Salt okunur bağlantı · Hesabı inceleyebilir ve plan önizleyebilirsiniz. Emir gönderimi kapalı."
                        : ""}
                </span>
              </div>
            )}
          <div className="bot-workspace">
            <div
              className="bot-content"
              hidden={compact || tab === "Yeni işlem"}
            >
              {tab === "Geri bildirim" && <BotFeedback />}
              {tab === "Hesap" && (
                <>
                  <h2>
                    Açık pozisyonlar{" "}
                    <small>
                      {snapshot?.positions.filter(
                        (p) => Number(p.positionAmt) !== 0,
                      ).length ?? 0}
                    </small>
                  </h2>
                  {snapshot && (
                    <p className="bot-account-caption">
                      {snapshot.entry_halted
                        ? "Yeni girişler durdurulmuş"
                        : "USD-M vadeli işlemler hesabı"}
                    </p>
                  )}
                  <div className="bot-table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Sembol</th>
                          <th>Yön</th>
                          <th>Miktar</th>
                          <th>Giriş</th>
                          <th>Mark</th>
                          <th>Açık kâr / zarar</th><th>ROE · %</th><th>Likidasyon · borsa</th><th>Likidasyon mesafesi · %</th>
                        </tr>
                      </thead>
                      <tbody>
                        {snapshot?.positions
                          .filter((p) => Number(p.positionAmt) !== 0)
                          .map((p, i) => (
                            <tr key={i}>
                              <td>
                                <button onClick={() => onChart(p.symbol)}>
                                  {p.symbol}
                                </button>
                              </td>
                              <td>{p.positionSide}</td>
                              <td>{p.positionAmt}</td>
                              <td>{p.entryPrice}</td>
                              <td>{p.markPrice}</td>
                              <td>
                                {stale?'—':p.unRealizedProfit ?? p.unrealizedProfit}
                              </td><td>{stale?'—':p.analytics?.roe_percent??'—'}</td><td>{stale||!p.liquidationPrice||Number(p.liquidationPrice)<=0?'—':p.liquidationPrice}</td><td>{stale?'—':p.analytics?.liquidation_distance_percent??'—'}</td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                  {!snapshot && (
                    <p>
                      Worker hazır olduğunda “Hesabı yenile” ile gerçek hesap
                      verisini alın.
                    </p>
                  )}
                  {snapshot &&
                    !snapshot.positions.some(
                      (p) => Number(p.positionAmt) !== 0,
                    ) && (
                      <div className="bot-empty-state">
                        <strong>Açık pozisyon yok</strong>
                        <p>
                          Hesabınızdaki pozisyonlar burada listelenir. Yeni bir
                          plan oluşturmak için işlem panelini kullanın.
                        </p>
                      </div>
                    )}
                  <h2>
                    Botun yönettiği oturumlar{" "}
                    <small>{snapshot?.sessions.length ?? 0}</small>
                  </h2>
                  {snapshot?.sessions.length === 0 && (
                    <p>Bu günlükte doğrulanmış bot oturumu yok.</p>
                  )}
                  {snapshot?.sessions.map((s) => (
                    <article className="bot-live-session" key={s.session_id}>
                      <strong>
                        {s.symbol} · {s.engine} · {s.state}
                      </strong>
                      <details className="bot-technical">
                        <summary>Oturum kimliği</summary>
                        <small>{s.session_id}</small>
                      </details>
                      {s.monitor_paused && (
                        <p role="alert">
                          Otomatik izleme durduruldu; oturumu inceleyin ve salt
                          okunur uzlaştırma sonrası devam edin. Yeniden başlatma
                          bu durumu temizlemez.
                        </p>
                      )}
                      {s.monitor_paused && (
                        <button
                          disabled={busy || !workerReady || queued}
                          onClick={() =>
                            task<BotReviewResult>(
                              "PREVIEW_CONTROL",
                              {
                                session_id: s.session_id,
                                kind: "RESUME_MONITOR",
                                close_position: false,
                              },
                              (j) => setReview({ job: j, value: j.result }),
                            )
                          }
                        >
                          İzlemeye dönüşü incele
                        </button>
                      )}
                      {s.runtime_health && (
                        <small>
                          Son izleme: {s.runtime_health.state} ·{" "}
                          {new Date(
                            s.runtime_health.observed_at * 1000,
                          ).toLocaleTimeString()}
                        </small>
                      )}
                      <button
                        disabled={controlsDisabled}
                        onClick={() =>
                          task<BotReviewResult>(
                            "PREVIEW_CONTROL",
                            {
                              session_id: s.session_id,
                              kind: "HALT_ENTRY",
                              close_position: false,
                            },
                            (j) => setReview({ job: j, value: j.result }),
                          )
                        }
                      >
                        Yeni girişleri durdur
                      </button>
                      {["grid-v2", "neutral-v2"].includes(s.engine) && (
                        <>
                          <button
                            disabled={controlsDisabled}
                            onClick={() =>
                              task<BotReviewResult>(
                                "PREVIEW_CONTROL",
                                {
                                  session_id: s.session_id,
                                  kind: "STOP_GRID",
                                  close_position: false,
                                },
                                (j) => setReview({ job: j, value: j.result }),
                              )
                            }
                          >
                            Gridi durdur · korumayı bırak
                          </button>
                          <button
                            disabled={controlsDisabled}
                            onClick={() =>
                              task<BotReviewResult>(
                                "PREVIEW_CONTROL",
                                {
                                  session_id: s.session_id,
                                  kind: "STOP_GRID",
                                  close_position: true,
                                },
                                (j) => setReview({ job: j, value: j.result }),
                              )
                            }
                          >
                            Gridi durdur ve kapat
                          </button>
                        </>
                      )}
                    </article>
                  ))}
                </>
              )}
              {tab === "Emirler" && (
                <>
                  <h2>Açık emirler</h2>
                  <p>
                    Normal ve algo kimlikleri ayrı tutulur. Koruma iptalleri
                    sunucuda denetlenir.
                  </p>
                  {(["NORMAL", "ALGO"] as const).map((ns) => (
                    <div key={ns}>
                      <h3>
                        {ns === "NORMAL"
                          ? "Normal emirler"
                          : "Koşullu emirler · Algo"}{" "}
                        <small>
                          {(ns === "NORMAL"
                            ? snapshot?.orders
                            : snapshot?.algo_orders
                          )?.length ?? 0}
                        </small>
                      </h3>
                      <div className="bot-table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>Sembol</th>
                              <th>Kimlik</th>
                              <th>Tür</th>
                              <th>Yön</th>
                              <th>Miktar</th>
                              <th>Fiyat / Tetik</th>
                              <th>İşlem</th>
                            </tr>
                          </thead>
                          <tbody>
                            {snapshot &&
                              (ns === "NORMAL"
                                ? snapshot.orders
                                : snapshot.algo_orders
                              ).length === 0 && (
                                <tr>
                                  <td colSpan={7} className="bot-empty-orders">
                                    Bu grupta açık emir yok.
                                  </td>
                                </tr>
                              )}
                            {(ns === "NORMAL"
                              ? snapshot?.orders
                              : snapshot?.algo_orders
                            )?.map((o, i) => (
                              <tr key={i}>
                                <td>{o.symbol}</td>
                                <td>
                                  {o.clientOrderId ??
                                    o.clientAlgoId ??
                                    o.orderId ??
                                    o.algoId}
                                </td>
                                <td>{o.type ?? o.orderType}</td>
                                <td>{o.side}</td>
                                <td>{o.origQty ?? o.quantity}</td>
                                <td>{o.triggerPrice ?? o.price}</td>
                                <td>
                                  <button
                                    disabled={
                                      controlsDisabled ||
                                      !(o.clientOrderId ?? o.clientAlgoId)
                                    }
                                    onClick={() =>
                                      preview({
                                        operation: "CANCEL_SELECTED_ORDERS",
                                        scope: { symbol: o.symbol },
                                        parameters: {
                                          targets: [
                                            {
                                              namespace: ns,
                                              client_id:
                                                o.clientOrderId ??
                                                o.clientAlgoId,
                                            },
                                          ],
                                          include_foreign: false,
                                        },
                                      })
                                    }
                                  >
                                    İptali incele
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </>
              )}
              {tab === "Yönetim" && (
                <BotLiveCommands
                  snapshot={snapshot}
                  symbol={draft.symbol}
                  disabled={controlsDisabled}
                  readDisabled={busy || !workerReady}
                  preview={preview}
                  read={read}
                />
              )}
              {tab === "Kayıtlar" && (
                <>
                  <h2>Kalıcı iş günlüğü</h2>
                  <p>
                    Her talebin durumunu buradan takip edin. Tamamlanan bir
                    talebin borsa sonucu ayrıntılardadır; belirsiz sonuçlar
                    otomatik yeniden gönderilmez.
                  </p>
                  <label className="bot-check"><input type="checkbox" checked={showReadings} onChange={e=>{setShowReadings(e.target.checked);void statusRefresh(e.target.checked).catch(fail);}}/>Otomatik okumaları ve hesaplamaları da göster</label><p className="bot-note">{showReadings?'Son 100 talep gösteriliyor.':'Son 100 işlem talebi gösteriliyor; otomatik okumalar ve hesaplamalar gizli.'}</p>
                  {jobs.length===0&&<p className="bot-empty">Bu filtrede henüz işlem kaydı yok.</p>}
                  {jobs.map((j) => (
                    <article className="bot-live-session" key={j.job_id}>
                      <strong>{names[j.action] ?? j.action}</strong>
                      <span className="bot-job-state" data-state={j.state}>
                        {jobOutcome(j)}
                      </span>
                      <time>
                        {new Date(j.updated_at * 1000).toLocaleString("tr-TR")}
                      </time>
                      {j.error_code && <p>{j.error_code}</p>}
                      <details>
                        <summary
                          onClick={() => {
                            if (j.result_loaded === false && !j.result)
                              botRequest<BotJob>(
                                "/api/bot/jobs/" + encodeURIComponent(j.job_id),
                              )
                                .then((detail) => {
                                  if (live.current)
                                    setJobs((rows) =>
                                      rows.map((row) =>
                                        row.job_id === detail.job_id
                                          ? detail
                                          : row,
                                      ),
                                    );
                                })
                                .catch(fail);
                          }}
                        >
                          Sonuç ve işlem kimliği
                        </summary>
                        <small>{j.job_id}</small>
                        <pre>{JSON.stringify(j.result, null, 2)}</pre>
                      </details>
                    </article>
                  ))}
                  <h2>Borsa komutları</h2>
                  {snapshot?.commands.map((c) => (
                    <article className="bot-live-session" key={c.command_id}>
                      <strong>
                        {c.operation ?? c.request?.operation} · {c.state}
                      </strong>
                      <small>{c.command_id}</small>
                      <button
                        disabled={busy || !workerReady}
                        onClick={() =>
                          task("RECONCILE", { command_id: c.command_id })
                        }
                      >
                        Kimliğiyle sonucu sorgula
                      </button>
                      <details>
                        <summary>Komut ayrıntısı</summary>
                        <pre>{JSON.stringify(c, null, 2)}</pre>
                      </details>
                    </article>
                  ))}
                </>
              )}
            </div>
            {(compact || tab === "Yeni işlem") && (
              <BotPlanForm
                draft={draft}
                onDraft={onDraft}
                symbols={symbols}
                pending={busy}
                marketPrice={snapshot?.mark?.symbol===draft.symbol&&now/1000-snapshot.mark.observed_at<=15?snapshot.mark.price:undefined}
                canSave={workerReady && !busy}
                canPreview={!busy && workerReady && !queued && !sourceChanged}
                onPreview={(mode) => {
                  const invalid = draftError(draft);
                  if (invalid) {
                    setError(invalid);
                    return;
                  }
                  task<BotReviewResult>(
                    mode ?? "PREVIEW_PLAN",
                    { draft: draftForServer(draft) },
                    (j) => {
                      if (mode === "SAVE_PLAN") {
                        setSnapshot(null);
                        setTab("Kayıtlar");
                      } else setReview({ job: j, value: j.result });
                    },
                  );
                }}
              ><BotPlanAnalytics draft={draft} active={active&&(compact||tab==='Yeni işlem')} enabled={workerReady&&!busy&&!review} readGate={accountReading} onPending={pending => { analyticsReading.current = pending; }}/></BotPlanForm>
            )}
          </div>
          {sourceChanged && (
            <p role="alert">Kaynak çizim değişti; grafikten yeniden aktarın.</p>
          )}
          {jobs.some((j) => j.state === "NEEDS_REVIEW") && (
            <p role="alert">
              Kesintiye uğramış işler var. Kayıtlardaki kimlikleri ve oturumları
              inceleyin; aynı işlemi yeni bir kimlikle tekrar göndermeyin.
            </p>
          )}
          {queued && (
            <p role="status">
              Onaylı işin sonucu bekleniyor. Kayıtlar bölümünden kontrol edin.
            </p>
          )}
        </>
      )}
      {review && (
        <BotLiveReview
          key={review.job.job_id}
          review={review.value}
          pending={busy}
          canExecute={
            Boolean(status?.execution_enabled) &&
            !(review.value.kind === "PLAN" && sourceChanged)
          }
          onClose={() => setReview(null)}
          onConfirm={() =>
            task(
              "CONFIRM",
              {
                review_id: review.job.job_id,
                review_digest: review.value.review_digest,
                account_ref: review.value.account_ref,
                execute_demo: true,
              },
              () => {
                setReview(null);
                setSnapshot(null);
                setTab("Kayıtlar");
              },
            )
          }
        />
      )}
    </section>
  );
}
