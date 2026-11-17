import type { BotDraft } from "./botPrototype";
export type BotJob<T = unknown> = {
  job_id: string;
  action: string;
  state: string;
  created_at: number;
  updated_at: number;
  error_code: string | null;
  result: T | null;
  automatic_resend: false;
  result_loaded?: boolean;
  result_state?: string | null;
};
export type BotStatus = {
  enabled: boolean;
  worker: string;
  execution_enabled: boolean;
  error_code: string | null;
  environment: string;
  product: string;
  queue?: {pending:number;running:number;oldest_pending_age_seconds:number|null};
};
export type CommandInput = {
  operation: string;
  scope: Record<string, unknown>;
  parameters: Record<string, unknown>;
};
export type PlanRow = {
  state: string;
  digest: string;
  plan: {
    plan_id: string;
    version: number;
    symbol: string;
    direction: string;
    execution?: { strategy: string };
  };
};
export type LiveSession = {
  session_id: string;
  symbol: string;
  engine: string;
  state: string;
  monitor_paused?: boolean;
  runtime_health?: { state: string; observed_at: number } | null;
  plan_ref: { plan_id: string; version: number; digest: string };
  plan: PlanRow["plan"];
};
export type ExchangePosition = {
  symbol: string;
  positionAmt: string;
  positionSide: string;
  entryPrice?: string;
  markPrice?: string;
  unRealizedProfit?: string;
  unrealizedProfit?: string;
};
export type ExchangeOrder = {
  symbol: string;
  clientOrderId?: string;
  clientAlgoId?: string;
  orderId?: number;
  algoId?: number;
  type?: string;
  orderType?: string;
  side: string;
  origQty?: string;
  quantity?: string;
  triggerPrice?: string;
  price?: string;
};
export type CommandResult = {
  command_id: string;
  state: string;
  operation?: string;
  request: CommandInput;
  parameters?: Record<string, unknown>;
  prepared_details?: Record<string, unknown>;
  result?: unknown;
};
export type BotSnapshot = {
  account_ref: string;
  observed_at: number;
  account: {
    totalWalletBalance?: string;
    availableBalance?: string;
    totalUnrealizedProfit?: string;
  };
  positions: ExchangePosition[];
  orders: ExchangeOrder[];
  algo_orders: ExchangeOrder[];
  sessions: LiveSession[];
  plans: PlanRow[];
  commands: CommandResult[];
  risk_limits: Record<string, string | number>;
  entry_halted: boolean;
};
type ReviewBase = {
  account_ref: string;
  expires_at: number;
  review_digest: string;
  risk_limits: Record<string, string | number>;
};
export type BotReviewResult = ReviewBase &
  (
    | {
        kind: "PLAN";
        payload: { draft: BotDraft; authorize_only?: boolean };
        data: {
          preflight: {
            state: string;
            quantity?: string;
            seed_quantity?: string;
          };
        };
      }
    | {
        kind: "COMMAND";
        payload: { authorize_only?: false; kind?: never };
        data: CommandResult;
      }
    | {
        kind: "CONTROL";
        payload: { kind: string; close_position?:boolean; authorize_only?: false };
        data: {
          request?: never;
          session_id: string;
          symbol: string;
          engine: string;
          state: string;
        };
      }
  );
const messages: Record<string, string> = {
  UNAUTHORIZED: "Yerel web erişim anahtarıyla oturum açın.",
  PRIVATE_API_DISABLED: "Web erişim anahtarı yapılandırılmamış.",
  BOT_DISABLED: "Bot bağlantısını sunucu ayarlarında etkinleştirin.",
  BOT_WORKER_READ_ONLY:
    "Worker salt okunur modda; Demo yürütmesi için açıkça --execute-demo ile başlatılmalı.",
  EXECUTION_CONTEXT_UNVERIFIED:
    "İşlem günlüğünün ortamı doğrulanmamış. Ayrılmış bir Demo veritabanı kullanın.",
  DEMO_CREDENTIALS_REQUIRED:
    "Demo borsa anahtarı ve secret worker ortamında birlikte tanımlanmalı.",
  BOT_VALIDATION_OR_PREFLIGHT_REJECTED:
    "Plan, hesap, risk, filtre veya sahiplik ön kontrolü reddetti. Alanları ve hesap durumunu yeniden inceleyin.",
  BOT_EXCHANGE_UNAVAILABLE:
    "Borsa yanıtı doğrulanamadı. Sonucu mevcut kimlikle kontrol edin; yeni emir göndermeyin.",
  BOT_TIMER_PRIORITY_REQUIRED:
    "Timer kontrolü öncelikli; yeni iş gönderilmedi. Timer durumunu inceleyin veya mevcut onay akışıyla kapatın. İş otomatik tekrarlanmaz.",
  BOT_TIMER_CONTEXT_CHANGED:
    "Timer bağlamı doğrulanamadı; yeni iş gönderilmedi. Kayıtlı timer ve hesap bağlamını inceleyin.",
  CHART_SOURCE_CHANGED: "Grafik çizimi değişti. Planı yeniden aktarın.",
  REVIEW_EXPIRED_OR_RISK_CHANGED:
    "Önizlemenin süresi doldu veya risk profili değişti. Yeniden önizleyin.",
  PLAN_PREFLIGHT_CHANGED:
    "Ön kontrol sonucu değişti. Güncel planı yeniden önizleyin.",
  WORKER_INTERRUPTED:
    "Worker kesildi. Bu iş yeniden gönderilmedi; kayıtlı komut/plan sonucunu kontrol edin.",
};
export class BotApiError extends Error {
  constructor(public code: string,diagnostic?:unknown) {
    super(exchangeDiagnosticMessage(diagnostic) ?? messages[code] ?? "İşlem tamamlanamadı: " + code);
  }
}
export function exchangeDiagnosticMessage(value:unknown):string|null{
 if(!value||typeof value!=='object')return null;
 const d=value as Record<string,unknown>;
 if(d.category!=='EXCHANGE'||d.delivery_status!=='REJECTED')return null;
 const explanations:Record<number,string>={
  [-2019]:'Kullanılabilir teminat yetersiz. Bütçeyi ve açık emirlerin ayırdığı teminatı kontrol edip yeniden önizleyin.',
  [-2027]:'Seçilen kaldıraç için pozisyon sınırı aşılıyor. Pozisyon büyüklüğünü ve hesap kaldıraç basamağını inceleyin.',
  [-4061]:'Emrin pozisyon yönü hesap moduyla uyuşmuyor. Tek yön / Hedge modunu kontrol edip yeniden önizleyin.',
  [-1111]:'Fiyat veya miktar hassasiyeti borsa kuralına uymuyor. Sözleşmenin fiyat adımı ve miktar adımını kontrol edin.',
  [-4164]:'Emir tutarı sözleşmenin asgari nominal tutarını karşılamıyor. Bütçeyi ve sözleşme limitlerini kontrol edip yeniden önizleyin.',
 };
 return typeof d.code==='number'?explanations[d.code]??null:null;
}
export async function botRequest<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    credentials: "same-origin",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  const data = await response.json();
  if (!response.ok)
    throw new BotApiError(data.error?.code ?? "HTTP_" + response.status);
  return data;
}
export async function runBotJob<T = unknown>(
  action: string,
  payload: Record<string, unknown>,
  onQueued?: (job: BotJob<T>) => void,
): Promise<BotJob<T>> {
  let job = await botRequest<BotJob<T>>("/api/bot/jobs", {
    request_id: crypto.randomUUID(),
    action,
    payload,
  });
  onQueued?.(job);
  for (let i = 0; i < 90 && ["PENDING", "RUNNING"].includes(job.state); i++) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    job = await botRequest<BotJob<T>>(
      "/api/bot/jobs/" + encodeURIComponent(job.job_id),
    );
  }
  if (job.state === "FAILED")
    throw new BotApiError(job.error_code ?? "BOT_JOB_FAILED",(job.result as {diagnostic?:unknown}|null)?.diagnostic);
  return job;
}
export function draftForServer(draft: BotDraft) {
  const copy = structuredClone(draft);
  if (copy.options?.tif === "GTD")
    return {
      ...copy,
      options: {
        ...copy.options,
        expires_ms: Date.parse(copy.options.expires),
      },
    };
  return copy;
}
