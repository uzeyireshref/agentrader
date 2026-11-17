import type { BotJob } from "./botApi";
const states: Record<string, string> = {
  SUCCEEDED: "Talep işlendi",
  PENDING: "Sırada",
  RUNNING: "İşleniyor",
  FAILED: "Başarısız",
  NEEDS_REVIEW: "İnceleme gerekiyor",
};
const outcomes: Record<string, string> = {
  APPLIED: "Uygulandı",
  REJECTED: "Borsa veya işlem kontrolü reddetti",
  UNKNOWN: "Sonuç belirsiz · inceleme gerekiyor",
  READ_FAILED: "Sorgu doğrulanamadı",
  FINAL_WITH_ERRORS: "Kısmi sonuç · hata var",
  NOT_SENT: "Gönderilmedi",
  EXPIRED: "Süresi doldu",
  CANCELED: "İptal edildi",
  MANAGING: "Pozisyon yönetiliyor",
  CLOSED: "Kapandı",
  AUTHORIZED: "Plan yetkilendirildi",
};
export function jobOutcome(job: BotJob): string {
  if (job.state !== "SUCCEEDED") return states[job.state] ?? job.state;
  const value: unknown = job.result;
  if (
    value &&
    typeof value === "object" &&
    "state" in value &&
    typeof value.state === "string"
  )
    return outcomes[value.state] ?? "Talep işlendi · " + value.state;
  return job.result_state
    ? (outcomes[job.result_state] ?? "Talep işlendi · " + job.result_state)
    : states.SUCCEEDED;
}
