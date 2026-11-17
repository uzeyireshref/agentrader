import { useState } from "react";
import type { BotSnapshot, CommandInput } from "./botApi";
import {batchPlanRows,planSelectionKey,reversePlanRows} from './botPlanSelection';
type Values = Record<string, string>;
const valueLabels:Record<string,string>={ISOLATED:'İzole',CROSSED:'Çapraz',PERCENT:'Yüzde · %',QUANTITY:'Miktar · baz varlık',MARK_PRICE:'Mark fiyatı',CONTRACT_PRICE:'Sözleşme fiyatı'};
const choices = [
  ["SET_LEVERAGE", "Kaldıraç"],
  ["SET_MARGIN_TYPE", "Teminat modu"],
  ["SET_POSITION_MODE", "Pozisyon modu · USD-M ve COIN-M"],
  ["SET_MULTI_ASSETS_MODE", "Çoklu varlık modu · hesap"],
  ["SET_FEE_BURN", "Komisyon indirimi · hesap"],
  ["INCREASE_POSITION", "Pozisyon artır"],
  ["REDUCE_POSITION", "Pozisyon azalt"],
  ["CLOSE_POSITION", "Pozisyon kapat"],
  ["REVERSE_POSITION", "Ters yön planı uygula"],
  ["CREATE_NATIVE_TRAILING", "Native trailing oluştur"],
  ["QUERY_NATIVE_TRAILING", "Native trailing sorgula"],
  ["CANCEL_NATIVE_TRAILING", "Native trailing iptal"],
  ["CANCEL_SYMBOL_ORDERS", "Sembol emirlerini iptal"],
  ["CANCEL_ACCOUNT_ORDERS", "Hesap emirlerini iptal"],
  ["SET_CANCEL_TIMER", "Sembol iptal zamanlayıcısı kur"],
  ["REFRESH_CANCEL_TIMER", "Zamanlayıcı heartbeat gönder · mevcut kira"],
  ["DISABLE_CANCEL_TIMER", "Zamanlayıcıyı kapat"],
  ["QUERY_CANCEL_TIMER", "Zamanlayıcıyı sorgula"],
  ["QUERY_HISTORY", "Geçmiş sorgusu"],
  ["CREATE_HISTORY_EXPORT", "Geçmiş dışa aktarma işi oluştur"],
  ["QUERY_HISTORY_EXPORT", "Dışa aktarma sonucunu sorgula"],
  ["PRIVATE_QUERY", "Hesap sorgusu"],
  ["GET_MARK_PRICE", "Mark fiyatı sorgusu"],
  ["BATCH_CREATE_ORDERS", "Toplu plan girişi"],
  ["BATCH_AMEND_ORDERS", "Toplu normal emir düzeltme"],
  ["BATCH_CANCEL_ORDERS", "Toplu normal emir iptal"],
];
const groups: Record<string, string[]> = {
  Pozisyon: [
    "INCREASE_POSITION",
    "REDUCE_POSITION",
    "CLOSE_POSITION",
    "REVERSE_POSITION",
  ],
  "Takip stopu": [
    "CREATE_NATIVE_TRAILING",
    "QUERY_NATIVE_TRAILING",
    "CANCEL_NATIVE_TRAILING",
  ],
  "Emir ve zamanlayıcı": [
    "CANCEL_SYMBOL_ORDERS",
    "CANCEL_ACCOUNT_ORDERS",
    "SET_CANCEL_TIMER",
    "REFRESH_CANCEL_TIMER",
    "DISABLE_CANCEL_TIMER",
    "QUERY_CANCEL_TIMER",
  ],
  "Hesap ayarları": [
    "SET_LEVERAGE",
    "SET_MARGIN_TYPE",
    "SET_POSITION_MODE",
    "SET_MULTI_ASSETS_MODE",
    "SET_FEE_BURN",
  ],
  "Toplu işlemler": [
    "BATCH_CREATE_ORDERS",
    "BATCH_AMEND_ORDERS",
    "BATCH_CANCEL_ORDERS",
  ],
  "Sorgu ve geçmiş": [
    "QUERY_HISTORY",
    "CREATE_HISTORY_EXPORT",
    "QUERY_HISTORY_EXPORT",
    "PRIVATE_QUERY",
    "GET_MARK_PRICE",
  ],
};
const readOnly = new Set([
  "QUERY_NATIVE_TRAILING",
  "QUERY_CANCEL_TIMER",
  "QUERY_HISTORY_EXPORT",
  "QUERY_HISTORY",
  "PRIVATE_QUERY",
  "GET_MARK_PRICE",
]);
export function liveCommand(
  op: string,
  symbol: string,
  v: Values,
  snapshot: BotSnapshot | null,
  selected: string[],
  members: { client_id: string; quantity: string; price: string }[],
): CommandInput {
  let scope: Record<string, unknown> = { symbol },
    p: Record<string, unknown> = {};
  const session = snapshot?.sessions.find((s) => s.session_id === v.session);
  if (
    [
      "INCREASE_POSITION",
      "REDUCE_POSITION",
      "CLOSE_POSITION",
      "REVERSE_POSITION",
      "CREATE_NATIVE_TRAILING",
      "BATCH_AMEND_ORDERS",
    ].includes(op)
  ) {
    if (!session) throw Error("Doğrulanmış bot oturumu seçin.");
    scope = { symbol: session.symbol };
    p.session_id = session.session_id;
  }
  switch (op) {
    case "SET_LEVERAGE":
      p = { leverage: Number(v.leverage) };
      break;
    case "SET_MARGIN_TYPE":
      p = { margin_type: v.margin };
      break;
    case "SET_POSITION_MODE":
      scope = { affected_products: ["USD-M", "COIN-M"] };
      p = { enabled: v.enabled === "true" };
      break;
    case "SET_MULTI_ASSETS_MODE":
    case "SET_FEE_BURN":
      scope = { account_wide: true };
      p = { enabled: v.enabled === "true" };
      break;
    case "INCREASE_POSITION":
      Object.assign(p, {
        quantity: v.quantity,
        price_floor: v.floor,
        price_ceiling: v.ceiling,
      });
      break;
    case "REDUCE_POSITION":
      p.reduction = { kind: v.reductionKind, value: v.quantity };
      break;
    case "REVERSE_POSITION": {
      const row = reversePlanRows(snapshot?.plans??[],session).find((r) => planSelectionKey(r) === v.nextPlan);
      if (!row) throw Error("Karşı yön için önceden önizlenmiş plan seçin.");
      Object.assign(p, {
        next_plan_id: row.plan.plan_id,
        next_version: row.plan.version,
        next_digest: row.digest,
      });
      break;
    }
    case "CREATE_NATIVE_TRAILING":
      Object.assign(p, {
        quantity: v.quantity,
        activate_price: v.activation,
        callback_rate: v.callback,
        working_type: v.working,
      });
      break;
    case "QUERY_NATIVE_TRAILING":
    case "CANCEL_NATIVE_TRAILING":
      p = { create_command_id: v.source };
      break;
    case "CANCEL_ACCOUNT_ORDERS":
      scope = { account_wide: true };
      p = { include_foreign: v.foreign === "true" };
      break;
    case "CANCEL_SYMBOL_ORDERS":
      p = { include_foreign: v.foreign === "true" };
      break;
    case "SET_CANCEL_TIMER":
      p = {
        countdown_ms: Number(v.countdown) * 1000,
        heartbeat_ms: Number(v.heartbeat) * 1000,
        lease_ms: Number(v.lease) * 1000,
        acknowledge_symbol_wide: true,
      };
      break;
    case "REFRESH_CANCEL_TIMER":
    case "DISABLE_CANCEL_TIMER":
    case "QUERY_CANCEL_TIMER":
      p = { timer_id: v.timer };
      break;
    case "QUERY_HISTORY":
    case "CREATE_HISTORY_EXPORT":
      p = {
        kind: v.history,
        start_ms: Date.parse(v.start),
        end_ms: Date.parse(v.end),
      };
      if (v.history === "INCOME" || op === "CREATE_HISTORY_EXPORT")
        scope = { account_wide: true };
      if (op === "QUERY_HISTORY")
        Object.assign(p, { page_size: 100, max_requests: 5 });
      break;
    case "QUERY_HISTORY_EXPORT":
      scope = { account_wide: true };
      p = { source_command_id: v.source };
      break;
    case "PRIVATE_QUERY":
      scope = [
        "ACCOUNT_V3",
        "BALANCE_V3",
        "POSITIONS_V3",
        "OPEN_ORDERS",
        "OPEN_ALGO_ORDERS",
        "ACCOUNT_CONFIG",
        "POSITION_MODE",
        "MULTI_ASSETS_MODE",
      ].includes(v.query)
        ? { account_wide: true }
        : { symbol };
      p = { query: v.query, arguments: {} };
      break;
    case "BATCH_CREATE_ORDERS": {
      const rows = batchPlanRows(snapshot?.plans??[],selected);
      scope = { symbols: [...new Set(rows.map((r) => r.plan.symbol))] };
      p = {
        plans: rows.map((r) => ({
          plan_id: r.plan.plan_id,
          version: r.plan.version,
          plan_digest: r.digest,
        })),
      };
      break;
    }
    case "BATCH_AMEND_ORDERS":
      p.changes = members.map((m) => ({ ...m }));
      break;
    case "BATCH_CANCEL_ORDERS":
      p = {
        targets: members.map((m) => ({
          namespace: "NORMAL",
          client_id: m.client_id,
        })),
        include_foreign: v.foreign === "true",
      };
      break;
  }
  return { operation: op, scope, parameters: p };
}
export default function BotLiveCommands({
  snapshot,
  symbol,
  disabled,
  readDisabled,
  preview,
  read,
}: {
  snapshot: BotSnapshot | null;
  symbol: string;
  disabled: boolean;
  readDisabled: boolean;
  preview: (c: CommandInput) => void;
  read: (c: CommandInput) => void;
}) {
  const [group, setGroup] = useState("Pozisyon");
  const [op, setOp] = useState("REDUCE_POSITION"),
    [v, setV] = useState<Values>({
      leverage: "3",
      margin: "ISOLATED",
      enabled: "false",
      session: "",
      quantity: "",
      floor: "",
      ceiling: "",
      reductionKind: "PERCENT",
      activation: "",
      callback: "1",
      working: "MARK_PRICE",
      source: "",
      foreign: "false",
      timer: "",
      countdown: "120",
      heartbeat: "10",
      lease: "60",
      history: "TRADES",
      start: "",
      end: "",
      query: "ACCOUNT_V3",
      nextPlan: "",
    }),
    [selected, setSelected] = useState<string[]>([]),
    [members, setMembers] = useState([
      { client_id: "", quantity: "", price: "" },
    ]),
    [error, setError] = useState("");
  const field = (key: string, label: string, type = "text") => (
    <label key={key}>
      {label}
      <input
        name={key}
        autoComplete="off"
        required
        type={type}
        value={v[key]}
        onChange={(e) => setV({ ...v, [key]: e.target.value })}
      />
    </label>
  );
  const select = (key: string, label: string, values: string[]) => (
    <label>
      {label}
      <select
        name={key}
        value={v[key]}
        onChange={(e) => setV({ ...v, [key]: e.target.value })}
      >
        {values.map((k) => (
          <option key={k} value={k}>{valueLabels[k]??k}</option>
        ))}
      </select>
    </label>
  );
  const sessions = [
    "INCREASE_POSITION",
    "REDUCE_POSITION",
    "CLOSE_POSITION",
    "REVERSE_POSITION",
    "CREATE_NATIVE_TRAILING",
    "BATCH_AMEND_ORDERS",
  ].includes(op);
  return (
    <section className="bot-live-commands">
      <h2>Hesap ve bot yönetimi</h2>
      <p>
        Her değişiklik önce hazırlanır; borsaya gönderilmesi ayrı onay
        gerektirir. Hesap ve sembol çapında işlemler diğer işlemleri de
        etkileyebilir.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          try {
            const c = liveCommand(op, symbol, v, snapshot, selected, members);
            setError("");
            (readOnly.has(op) ? read : preview)(c);
          } catch (e) {
            setError(e instanceof Error ? e.message : "Alanları kontrol edin.");
          }
        }}
      >
        <div
          className="bot-command-groups"
          role="group"
          aria-label="Yönetim kategorisi"
        >
          {Object.keys(groups).map((g) => (
            <button
              type="button"
              aria-pressed={group === g}
              key={g}
              onClick={() => {
                setGroup(g);
                setOp(groups[g][0]);
                setError("");
              }}
            >
              {g}
            </button>
          ))}
        </div>
        <div className="bot-command-editor">
          <label>
            Yapılacak işlem
            <select
              value={op}
              onChange={(e) => {
                setOp(e.target.value);
                setError("");
              }}
            >
              {choices
                .filter(([id]) => groups[group].includes(id))
                .map(([id, label]) => (
                  <option value={id} key={id}>
                    {label}
                  </option>
                ))}
            </select>
          </label>
          <p className="bot-scope-label">
            İşlem kapsamı <strong>{symbol}</strong>
          </p>
          <fieldset
            className="bot-live-fieldset"
            disabled={readOnly.has(op) ? readDisabled : disabled}
          >
            <div className="bot-field-grid">
              {sessions && (
                <label>
                  Bot oturumu
                  <select
                    required
                    value={v.session}
                    onChange={(e) => setV({ ...v, session: e.target.value })}
                  >
                    <option value="">Seçin</option>
                    {snapshot?.sessions
                      .filter((s) => s.engine === "v2" && s.plan.execution?.strategy === 'SINGLE' && !['CLOSED','REJECTED','FAILED'].includes(s.state))
                      .map((s) => (
                        <option value={s.session_id} key={s.session_id}>
                          {s.symbol} · {s.state} · {s.session_id}
                        </option>
                      ))}
                  </select>
                  {!snapshot?.sessions.some(s=>s.engine==='v2'&&s.plan.execution?.strategy==='SINGLE'&&!['CLOSED','REJECTED','FAILED'].includes(s.state))&&<small>Bu işlem için uygun tek işlem oturumu yok. Önce Hesap sekmesindeki bot oturumlarını kontrol edin.</small>}
                </label>
              )}
              {op === "SET_LEVERAGE" && field("leverage", "Kaldıraç", "number")}
              {op === "SET_MARGIN_TYPE" &&
                select("margin", "Teminat", ["ISOLATED", "CROSSED"])}
              {[
                "SET_POSITION_MODE",
                "SET_MULTI_ASSETS_MODE",
                "SET_FEE_BURN",
              ].includes(op) && (
                <label>
                  {op === "SET_POSITION_MODE" ? "Pozisyon modu" : "Durum"}
                  <select
                    value={v.enabled}
                    onChange={(e) => setV({ ...v, enabled: e.target.value })}
                  >
                    <option value="false">
                      {op === "SET_POSITION_MODE" ? "Tek yön" : "Kapalı"}
                    </option>
                    <option value="true">
                      {op === "SET_POSITION_MODE" ? "Hedge" : "Açık"}
                    </option>
                  </select>
                </label>
              )}
              {[
                "INCREASE_POSITION",
                "REDUCE_POSITION",
                "CREATE_NATIVE_TRAILING",
              ].includes(op) &&
                field(
                  "quantity",
                  op === "REDUCE_POSITION"
                    ? "Azaltma değeri"
                    : "Miktar · baz varlık",
                )}
              {op === "REDUCE_POSITION" &&
                select("reductionKind", "Azaltma türü", [
                  "PERCENT",
                  "QUANTITY",
                ])}
              {op === "INCREASE_POSITION" && (
                <>
                  {field("floor", "Onaylanan alt fiyat")}
                  {field("ceiling", "Onaylanan üst fiyat")}
                </>
              )}
              {op === "REVERSE_POSITION" && (
                <label>
                  Karşı yön planı
                  <select
                    required
                    value={v.nextPlan}
                    onChange={(e) => setV({ ...v, nextPlan: e.target.value })}
                  >
                    <option value="">Seçin</option>
                    {reversePlanRows(snapshot?.plans??[],snapshot?.sessions.find(s=>s.session_id===v.session))
                      .map((r) => (
                        <option key={planSelectionKey(r)} value={planSelectionKey(r)}>
                          {r.plan.symbol} · {r.plan.direction} ·{" "}
                          {r.plan.plan_id} · sürüm {r.plan.version}
                        </option>
                      ))}
                  </select>
                </label>
              )}
              {op === "CREATE_NATIVE_TRAILING" && (
                <>
                  {field("activation", "Aktivasyon fiyatı")}
                  {field("callback", "Callback · % 0.1–20")}
                  {select("working", "Tetik referansı", [
                    "MARK_PRICE",
                    "CONTRACT_PRICE",
                  ])}
                </>
              )}
              {[
                "QUERY_NATIVE_TRAILING",
                "CANCEL_NATIVE_TRAILING",
                "QUERY_HISTORY_EXPORT",
              ].includes(op) &&
                field("source", "Kaynak oluşturma komut kimliği")}
              {op.includes("CANCEL") &&
                [
                  "CANCEL_ACCOUNT_ORDERS",
                  "CANCEL_SYMBOL_ORDERS",
                  "BATCH_CANCEL_ORDERS",
                ].includes(op) && (
                  <label>
                    <input
                      type="checkbox"
                      checked={v.foreign === "true"}
                      onChange={(e) =>
                        setV({ ...v, foreign: String(e.target.checked) })
                      }
                    />
                    Diğer istemcilerin emirlerini de kapsa
                  </label>
                )}
              {op === "SET_CANCEL_TIMER" && (
                <>
                  {field("countdown", "İptale kalan · saniye", "number")}
                  {field("heartbeat", "Heartbeat · saniye", "number")}
                  {field("lease", "Worker kiralama · saniye", "number")}
                  <p>
                    Zamanlayıcı sembol çapındadır. Worker durunca heartbeat
                    kesilir; borsa geri sayımı devam eder. Yeniden başlatma
                    otomatik kurmaz.
                  </p>
                </>
              )}
              {[
                "REFRESH_CANCEL_TIMER",
                "DISABLE_CANCEL_TIMER",
                "QUERY_CANCEL_TIMER",
              ].includes(op) && field("timer", "Zamanlayıcı kimliği")}
              {["QUERY_HISTORY", "CREATE_HISTORY_EXPORT"].includes(op) && (
                <>
                  {select(
                    "history",
                    "Geçmiş ailesi",
                    op === "QUERY_HISTORY"
                      ? ["TRADES", "ORDERS", "ALGO_ORDERS", "INCOME"]
                      : ["TRADES", "ORDERS", "INCOME"],
                  )}
                  {field("start", "Başlangıç · yerel saat", "datetime-local")}
                  {field("end", "Bitiş · yerel saat", "datetime-local")}
                </>
              )}
              {op === "PRIVATE_QUERY" &&
                select("query", "Adlandırılmış sorgu", [
                  "ACCOUNT_V3",
                  "BALANCE_V3",
                  "POSITIONS_V3",
                  "OPEN_ORDERS",
                  "OPEN_ALGO_ORDERS",
                  "ACCOUNT_CONFIG",
                  "POSITION_MODE",
                  "MULTI_ASSETS_MODE",
                  "LEVERAGE_BRACKETS",
                ])}
            </div>
            {op === "BATCH_CREATE_ORDERS" && (
              <div>
                <p>1–5 yetkili plan sürümü seçin. Her sözleşme yalnız bir kez yer alabilir; üye sonuçları ayrı değerlendirilir.</p><button type="button" onClick={()=>setSelected([])}>Seçimi temizle</button>
                {snapshot?.plans
                  .filter(
                    (r) =>
                      r.plan.execution?.strategy === "SINGLE" &&
                      r.state === "AUTHORIZED",
                  )
                  .map((r) => (
                    <label className="bot-check" key={planSelectionKey(r)}>
                      <input
                        type="checkbox"
                        checked={selected.includes(planSelectionKey(r))}
                        onChange={(e) =>
                          setSelected(
                            e.target.checked
                              ? [...selected, planSelectionKey(r)]
                              : selected.filter((id) => id !== planSelectionKey(r)),
                          )
                        }
                      />
                      {r.plan.symbol} · {r.plan.direction} · {r.plan.plan_id} · sürüm {r.plan.version}
                    </label>
                  ))}
              </div>
            )}
            {["BATCH_AMEND_ORDERS", "BATCH_CANCEL_ORDERS"].includes(op) && (
              <div>
                {members.map((m, i) => (
                  <div className="bot-field-grid" key={i}>
                    {(
                      [
                        "client_id",
                        ...(op === "BATCH_AMEND_ORDERS"
                          ? ["quantity", "price"]
                          : []),
                      ] as const
                    ).map((k) => (
                      <label key={k}>
                        {k === "client_id"
                          ? "Normal emir istemci kimliği"
                          : k === "quantity"
                            ? "Yeni miktar"
                            : "Yeni fiyat"}
                        <input
                          required
                          value={m[k as keyof typeof m]}
                          onChange={(e) =>
                            setMembers(
                              members.map((r, n) =>
                                n === i ? { ...r, [k]: e.target.value } : r,
                              ),
                            )
                          }
                        />
                      </label>
                    ))}
                    <button
                      type="button"
                      disabled={members.length === 1}
                      onClick={() =>
                        setMembers(members.filter((_, n) => n !== i))
                      }
                    >
                      Satırı kaldır
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  disabled={
                    members.length >= (op === "BATCH_AMEND_ORDERS" ? 5 : 10)
                  }
                  onClick={() =>
                    setMembers([
                      ...members,
                      { client_id: "", quantity: "", price: "" },
                    ])
                  }
                >
                  Üye ekle
                </button>
              </div>
            )}
            <button className="bot-primary">
              {readOnly.has(op)
                ? "Sorgula · sonuç Kayıtlar bölümünde"
                : "Hesapta ön kontrol yap"}
            </button>
          </fieldset>
          {error && <p role="alert">{error}</p>}
        </div>
      </form>
    </section>
  );
}
