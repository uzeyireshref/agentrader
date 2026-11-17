export type HistoryLoadState = 'READY'|'LOADING'|'EXHAUSTED'|'LIMIT'|'NETWORK_ERROR'|'INVALID_DATA'|'RENDER_ERROR';
export const historyLoadLabels:Record<HistoryLoadState,string> = {
 READY:'Geçmiş hazır', LOADING:'Eski mumlar yükleniyor…',
 EXHAUSTED:'Sağlayıcının sunduğu geçmişin başlangıcına ulaşıldı.',
 LIMIT:'4000 mumluk görünüm sınırına ulaşıldı. Daha eski tarih bu oturumda yüklenemiyor.',
 NETWORK_ERROR:'Geçmiş alınamadı. Bağlantıyı kontrol edip yeniden dene.',
 INVALID_DATA:'Geçmiş yanıtı doğrulanamadı. Yeniden dene.',
 RENDER_ERROR:'Geçmiş görüntülenemedi. Yeniden dene.',
};
