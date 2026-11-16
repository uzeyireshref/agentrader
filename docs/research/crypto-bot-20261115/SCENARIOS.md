# İşlem ve geliştirme senaryoları

128 senaryo bulunur. İlk 64 senaryo mevcut kod ve tekil regresyon tanığıyla eşleşir. Son 64 senaryoda incelenen üretim yollarında tam kabul akışı bulunamadı. Kod parçası veya benzer bir hesap olması bu son grubun uçtan uca kapsamını tamamlamaz.

Her satırın beklenen sonucu JSON katalogda bulunur. Regresyon sonuçları güncel audit raporundan okunur. Sembol başına borsa yürütme kabulü ayrıca ölçülmelidir.

## Emir doğrulama

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-001 | Long ve short emir parametreleri | Regresyon tanığı mevcut, tests/test_order_rules.py / test_long_and_short_open_orders | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-002 | Hedge positionSide ve reduceOnly kuralları | Regresyon tanığı mevcut, tests/test_order_rules.py / test_hedge_side_and_reduce_only_rules | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-003 | Minimum nominalin altında pozisyon azaltma | Regresyon tanığı mevcut, tests/test_order_rules.py / test_reducing_market_exit_can_be_below_entry_minimum | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-004 | Close-all stop ile miktar çakışması | Regresyon tanığı mevcut, tests/test_order_rules.py / test_stop_close_all_and_quantity_conflict | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-005 | Tick, lot ve bilinmeyen alan reddi | Regresyon tanığı mevcut, tests/test_order_rules.py / test_minimum_steps_and_unknown_fields | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-006 | Market emrine limit alanı ekleme | Regresyon tanığı mevcut, tests/test_order_rules.py / test_market_does_not_accept_limit_fields | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-007 | GTD vadesi ve saat kontrolü | Regresyon tanığı mevcut, tests/test_order_rules.py / test_gtd_requires_a_valid_future_time | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-008 | Native trailing yönü ve callback doğrulama | Regresyon tanığı mevcut, tests/test_order_rules.py / test_trailing_stop_direction_and_callback | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |

## Tek pozisyon yürütme

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-009 | Onaylı long giriş ve korumalar | Regresyon tanığı mevcut, tests/test_v2_runner.py / test_authorized_long_protects_and_restart_never_reenters | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-010 | Short hedge giriş ve korumalar | Regresyon tanığı mevcut, tests/test_v2_runner.py / test_short_hedge_uses_correct_entry_and_protection_sides | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-011 | Kaybolan giriş yanıtında çift emir önleme | Regresyon tanığı mevcut, tests/test_v2_runner.py / test_lost_entry_response_is_recovered_without_second_entry | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-012 | Kısmi girişin kalanını iptal ve koruma | Regresyon tanığı mevcut, tests/test_v2_runner.py / test_partial_entry_is_canceled_before_protection | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-013 | Bekleyen limit emrinin restart sonrası yönetimi | Regresyon tanığı mevcut, tests/test_v2_runner.py / test_limit_pending_restart_does_not_cancel_or_reenter | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-014 | Limit emrin vade sonunda iptali | Regresyon tanığı mevcut, tests/test_v2_runner.py / test_limit_expiry_cancels_without_opening_position | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-015 | Kademeli long hedefte artık miktarı koruma | Regresyon tanığı mevcut, tests/test_v2_runner.py / test_staged_long_exit_leaves_residual_and_keeps_final_target | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-016 | Break-even stopu doğrulayarak değiştirme | Regresyon tanığı mevcut, tests/test_v2_runner.py / test_break_even_verifies_new_quantity_stop_before_canceling_old | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |

## Grid yürütme

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-017 | Başlangıç grid hücreleri ve seed koruması | Regresyon tanığı mevcut, tests/test_grid_runner.py / test_grid_initializes_four_slots_and_protects_seed | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-018 | Al-sat-yenile döngüsünde kapasite | Regresyon tanığı mevcut, tests/test_grid_runner.py / test_fill_sell_refill_cycle_preserves_slot_capacity | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-019 | Kısmi alışta gerçek dolan miktarı satma | Regresyon tanığı mevcut, tests/test_grid_runner.py / test_partial_buy_cancels_remaining_then_sells_actual_fill | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-020 | Kısmi satış tamamlanmadan yenilememe | Regresyon tanığı mevcut, tests/test_grid_runner.py / test_partial_sell_never_refills_before_residual_is_sold | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-021 | Grid restart sonrası çift emir önleme | Regresyon tanığı mevcut, tests/test_grid_runner.py / test_restart_queries_existing_orders_without_duplicate_posts | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-022 | Short hedge geometrik grid | Regresyon tanığı mevcut, tests/test_grid_runner.py / test_short_hedge_and_geometric_grid_use_inverse_sides | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-023 | Native stop dolunca ikinci kapanış göndermeme | Regresyon tanığı mevcut, tests/test_grid_runner.py / test_native_stop_fill_closes_grid_without_another_market_exit | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-024 | Düşen kaldıraç sınırında refill engeli | Regresyon tanığı mevcut, tests/test_grid_runner.py / test_lowered_exchange_leverage_cap_blocks_refill_before_new_open | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |

## Çoklu coin ve hesap riski

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-025 | İki sembolün sahipli emirlerle eşzamanlı yönetimi | Regresyon tanığı mevcut, tests/test_multi_session.py / test_two_symbols_open_and_manage_without_adopting_each_others_orders | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-026 | Toplam nominal bütçenin paylaşılması | Regresyon tanığı mevcut, tests/test_multi_session.py / test_individually_valid_plans_cannot_exceed_shared_notional | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-027 | Bir oturum kapanınca diğer korumaların korunması | Regresyon tanığı mevcut, tests/test_multi_session.py / test_closing_one_session_preserves_peer_protections_and_reservation | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-028 | Restart sonrası ortak rezervasyon | Regresyon tanığı mevcut, tests/test_multi_session.py / test_restart_preserves_ownership_and_full_reservations | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-029 | Dolmamış girişlerin risk ayırması | Regresyon tanığı mevcut, tests/test_multi_session.py / test_two_pending_entries_reserve_capacity_even_with_no_fills | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-030 | Single ve grid oturumlarının birlikte çalışması | Regresyon tanığı mevcut, tests/test_multi_session.py / test_single_and_grid_coexist_and_stop_only_cancels_grid_symbol | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-031 | İki grid oturumunun bağımsız kapanması | Regresyon tanığı mevcut, tests/test_multi_session.py / test_two_grids_manage_and_close_independently | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-032 | Hesap genelinde günlük kayıp bütçesi | Regresyon tanığı mevcut, tests/test_multi_session.py / test_joint_stop_loss_and_daily_loss_are_account_wide | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |

## Portföy ve teminat

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-033 | Nominal, teminat ve stop zararını ayrı hesaplama | Regresyon tanığı mevcut, tests/test_portfolio.py / test_nominal_margin_and_stop_are_different | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-034 | Long/short hedge riskini koruma | Regresyon tanığı mevcut, tests/test_portfolio.py / test_long_and_short_hedge_risk_is_not_netted | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-035 | Bekleyen girişlerin riskini toplama | Regresyon tanığı mevcut, tests/test_portfolio.py / test_pending_entries_aggregate_instead_of_releasing_risk | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-036 | Likidasyon ötesi stopu reddetme | Regresyon tanığı mevcut, tests/test_portfolio.py / test_isolated_stop_beyond_liquidation_is_rejected | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-037 | Doğrulanmış ek izole teminat etkisi | Regresyon tanığı mevcut, tests/test_portfolio.py / test_verified_extra_isolated_margin_can_move_liquidation | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-038 | Eski portföy görünümünde giriş engeli | Regresyon tanığı mevcut, tests/test_portfolio.py / test_insufficient_margin_and_stale_snapshot_block | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-039 | Değerlenmemiş teminatı reddetme | Regresyon tanığı mevcut, tests/test_portfolio.py / test_unvalued_collateral_never_assumed_usdt | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-040 | Kaldıraçtan bağımsız kayıp bütçesi | Regresyon tanığı mevcut, tests/test_portfolio.py / test_loss_budget_is_not_multiplied_by_leverage | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |

## Takip stopu

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-041 | Yalnız iyileşen watermark ve tick yuvarlama | Regresyon tanığı mevcut, tests/test_trailing.py / test_watermark_is_monotonic_and_tick_rounding_is_conservative | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-042 | Aktivasyon öncesinde stopu koruma | Regresyon tanığı mevcut, tests/test_trailing.py / test_before_activation_and_small_steps_do_not_replace_stop | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-043 | Short takip hesabı | Regresyon tanığı mevcut, tests/test_trailing.py / test_short_watermark_and_rounding_are_mirrored | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-044 | Long stopu bir kez sıkılaştırma | Regresyon tanığı mevcut, tests/test_trailing.py / test_long_tightens_once_and_never_moves_back | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-045 | Restart sonrası watermark koruma | Regresyon tanığı mevcut, tests/test_trailing.py / test_restart_preserves_watermark_and_replaces_only_on_new_high | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-046 | Kaybolan stop POST/DELETE yanıtlarında uzlaştırma | Regresyon tanığı mevcut, tests/test_trailing.py / test_lost_post_and_lost_cancel_are_never_repeated | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-047 | Kademeli çıkışta takip stopu miktarı | Regresyon tanığı mevcut, tests/test_trailing.py / test_staged_exit_resizes_without_break_even_loosening_trailing | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-048 | Stop geçilince yalnız artık miktarı kapatma | Regresyon tanığı mevcut, tests/test_trailing.py / test_retrace_below_effective_stop_closes_residual_only | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |

## Kullanıcı akışı ve taşıma

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-049 | Yinelenen akış olayını tek sayma | Regresyon tanığı mevcut, tests/test_user_stream.py / test_duplicate_delivery_does_not_wake_or_double_count | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-050 | Aynı zamanlı farklı hesap olaylarını ayırt etme | Regresyon tanığı mevcut, tests/test_user_stream.py / test_same_time_account_changes_have_distinct_identity | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-051 | Bozuk olayın projeksiyonu değiştirmemesi | Regresyon tanığı mevcut, tests/test_user_stream.py / test_invalid_event_cannot_change_projection | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-052 | Algo olayından REST uzlaştırması | Regresyon tanığı mevcut, tests/test_user_stream.py / test_algo_and_unknown_events_wake_rest_without_inventing_inventory | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-053 | Keepalive ve anahtar rotasyonu | Regresyon tanığı mevcut, tests/test_user_stream.py / test_keepalive_after_30_minutes_and_23_hour_rotation | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-054 | Yinelenen olay selini sınırlama | Regresyon tanığı mevcut, tests/test_user_stream.py / test_duplicate_flood_is_bounded | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-055 | Sessiz WebSocket kopmasını algılama | Regresyon tanığı mevcut, tests/test_user_stream.py / test_silent_connection_is_detected_after_ping_deadline | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-056 | Özel bağlantı hatalarında hassas veriyi gizleme | Regresyon tanığı mevcut, tests/test_user_stream.py / test_closed_socket_is_not_idle_and_errors_hide_private_url | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |

## Grafik ve sinyal entegrasyonu

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-057 | Bot kimliği ve yetenek kataloğu | Regresyon tanığı mevcut, tests/test_chart_bot.py / test_identity_catalog_namespace_and_explicit_snapshot | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-058 | Kalıcı çizim işlemlerinde tekrar güvenliği | Regresyon tanığı mevcut, tests/test_chart_bot.py / test_create_cached_replay_changed_payload_conflict_and_restart_discovery | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-059 | Yanıt kaybında çizimi çift oluşturmama | Regresyon tanığı mevcut, tests/test_chart_bot.py / test_response_lost_after_commit_pending_survives_adapter_restart | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-060 | Manuel çizim ve not sahipliğini koruma | Regresyon tanığı mevcut, tests/test_chart_bot.py / test_manual_object_and_note_preserved_adapter_and_server_protection | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-061 | Revizyon çakışmasını görünür kılma | Regresyon tanığı mevcut, tests/test_chart_bot.py / test_explicit_revision_conflict_and_race_do_not_rebase | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-062 | Çizim matematiği ve gösterge okuma | Regresyon tanığı mevcut, tests/test_chart_bot.py / test_calculation_structured_blocks_explicit_time_context_and_indicator_reads | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-063 | Eşzamanlı aynı işlemde tek nesne | Regresyon tanığı mevcut, tests/test_chart_bot.py / test_concurrent_duplicate_operation_has_one_object | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |
| CB-064 | Güvensiz uzak çizim API erişimini reddetme | Regresyon tanığı mevcut, tests/test_chart_bot.py / test_local_transport_rejects_remote_credentials_urls_and_unsafe_paths | İlgili regresyon geçmeli. Sembol bazında borsa kabulü ayrıca ölçülür. |

## Coin evreni ve tarayıcı

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-065 | 528 sembollük evreni otomatik yenileme | Geliştirme açığı, P1 | exchangeInfo değiştiğinde listeleme/delist farkı ve evren sürümü kaydedilmeli |
| CB-066 | Hacim ve spread tabanlı coin seçimi | Geliştirme açığı, P1 | Hacmi yüksek fakat spreadi geniş coin elenmeli |
| CB-067 | Listeleme yaşı ve yeterli geçmiş filtresi | Geliştirme açığı, P1 | Yeni coin warmup tamamlanmadan sinyale alınmamalı |
| CB-068 | Likidite ve emir defteri derinliği filtresi | Geliştirme açığı, P1 | Hedef miktarın tahmini kayması limite uymazsa aday elenmeli |
| CB-069 | Volatiliteye göre dinamik evren | Geliştirme açığı, P1 | ATR yüzdesi eşiği ve seçim zamanı tekrar üretilebilmeli |
| CB-070 | Çoklu coin sinyal sıralaması | Geliştirme açığı, P1 | Aynı kapanışta gelen adaylar puan ve eşitlik kuralıyla seçilmeli |
| CB-071 | Yüzlerce sembol için abonelik bütçesi | Geliştirme açığı, P1 | REST ağırlığı ve WebSocket bağlantı sınırları ölçülmeli |
| CB-072 | 500+ sembol yük ve dayanıklılık kabulü | Geliştirme açığı, P1 | Gecikme, bellek ve atlanan olaylar uzun süre ölçülmeli |

## Yönlü strateji araştırması

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-073 | EMA trend kesişimiyle giriş çıkış | Geliştirme açığı, P1 | Kapalı mum sinyali, stop, hedef ve maliyet modeli birlikte sınanmalı |
| CB-074 | Donchian kanal kırılımı | Geliştirme açığı, P1 | Geçmiş kanal sınırı yalnız karar anındaki mumlardan oluşmalı |
| CB-075 | RSI ortalamaya dönüş | Geliştirme açığı, P1 | Trend filtresi ve stopla örnek dışı dönem sınanmalı |
| CB-076 | Bollinger bant dönüşü | Geliştirme açığı, P1 | Bant dışı kapanış ve yeniden giriş kuralları tek anlamlı olmalı |
| CB-077 | VWAP sapmasıyla gün içi strateji | Geliştirme açığı, P1 | Session ve anchored VWAP kaynakları ayrı tanımlanmalı |
| CB-078 | ATR volatilite kırılımı | Geliştirme açığı, P1 | Pozisyon miktarı ve stop volatiliteye göre hesaplanmalı |
| CB-079 | Çoklu zaman dilimli trend teyidi | Geliştirme açığı, P1 | Üst zaman diliminde son kapanmış mum kullanılmalı |
| CB-080 | Rejim bazlı strateji seçimi | Geliştirme açığı, P1 | Trend, yatay ve yüksek volatilite geçişlerinde maliyet sonrası sonuç ölçülmeli |

## Gelişmiş yürütme

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-081 | Takvimli DCA alım yürütücüsü | Geliştirme açığı, P2 | Dilim sayısı, toplam bütçe ve iptal davranışı tanımlanmalı |
| CB-082 | TWAP dilimleme | Geliştirme açığı, P2 | Zaman dilimleri, kısmi dolum ve son kalan miktar bütçeyi aşmamalı |
| CB-083 | Hacme katılım yürütmesi | Geliştirme açığı, P2 | POV oranı ve gözlenen hacim gecikmesi sınırlanmalı |
| CB-084 | VWAP hedefli yürütme | Geliştirme açığı, P2 | Geçmiş hacim profili ve gerçekleşen fiyat farkı ölçülmeli |
| CB-085 | Iceberg emir dilimleri | Geliştirme açığı, P2 | Görünür miktar ve toplam artık miktar tutarlı kalmalı |
| CB-086 | Limitten markete kontrollü geçiş | Geliştirme açığı, P2 | Süre ve spread koşulunda kalan miktar bir kez gönderilmeli |
| CB-087 | Yürütme maliyeti analizi | Geliştirme açığı, P2 | Arrival price karşısında ücret, kayma ve implementation shortfall raporlanmalı |
| CB-088 | Çoklu borsa akıllı yönlendirme | Geliştirme açığı, P2 | Maliyet, derinlik, bakiye ve eksik dolum birlikte yönetilmeli |

## Arbitraj ve piyasa yapıcılık

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-089 | Borsalar arası fiyat arbitrajı | Geliştirme açığı, P3 | İki bacak ücret ve kayma sonrası pozitif eşik sağlamalı |
| CB-090 | Üçgen arbitraj | Geliştirme açığı, P3 | Üç işlemde lot yuvarlaması ve artık varlık takip edilmeli |
| CB-091 | Spot-perpetual baz işlemi | Geliştirme açığı, P3 | Spot ve perpetual miktarı ile funding nakit akışı eşlenmeli |
| CB-092 | Borsalar arası funding farkı | Geliştirme açığı, P3 | Ödeme zamanı, oran değişimi ve hedge sapması ölçülmeli |
| CB-093 | Vadeli kontrat taşıma işlemi | Geliştirme açığı, P3 | Vade, uzlaşma ve rollover maliyeti hesaba katılmalı |
| CB-094 | Envanter kontrollü piyasa yapıcılık | Geliştirme açığı, P3 | Kotasyon fiyatı envanter ve adverse selection sınırlarına uymalı |
| CB-095 | Cross-exchange market making | Geliştirme açığı, P3 | Maker dolumu sonrası hedge zaman aşımı ve artığı yönetilmeli |
| CB-096 | DEX LP ve CEX hedge | Geliştirme açığı, P3 | Gas, onay, MEV, aralık dışına çıkma ve zincir riski modellenmeli |

## Backtest ve istatistik

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-097 | Çoklu coin portföy PnL backtesti | Geliştirme açığı, P1 | Emir, dolum, nakit, ücret ve pozisyon defteri aynı olay saatini kullanmalı |
| CB-098 | Spread ve kayma modeli | Geliştirme açığı, P1 | Maliyetin iki katına çıktığı duyarlılık testi raporlanmalı |
| CB-099 | Funding muhasebesi | Geliştirme açığı, P1 | Gerçek ödeme zamanları ve pozisyon yönü uygulanmalı |
| CB-100 | Aynı mum stop ve hedef belirsizliği | Geliştirme açığı, P1 | Alt zaman dilimi veya ihtiyatlı öncelik politikası açık olmalı |
| CB-101 | Lookahead analizi | Geliştirme açığı, P1 | Gelecek veri kesilince geçmiş sinyaller değişmemeli |
| CB-102 | Recursive warmup analizi | Geliştirme açığı, P1 | Geçmiş uzunluğu değişince göstergedeki sapma raporlanmalı |
| CB-103 | Walk-forward örnek dışı değerlendirme | Geliştirme açığı, P1 | Eğitim, seçim ve test pencereleri kronolojik ayrılmalı |
| CB-104 | Çoklu deneme ve bootstrap sağlamlığı | Geliştirme açığı, P1 | Parametre araması sayısı ve blok bootstrap dağılımı kaydedilmeli |

## Portföy araştırması ve maliyet

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-105 | Korelasyon kümeleri için risk bütçesi | Geliştirme açığı, P2 | Aynı yöne korele coin grubu toplam limiti aşmamalı |
| CB-106 | Volatilite hedefli pozisyon büyüklüğü | Geliştirme açığı, P2 | Sakin ve stres rejimlerinde toplam risk hedefi ölçülmeli |
| CB-107 | Drawdown devre kesici | Geliştirme açığı, P2 | Equity tepesinden düşüşte yeni giriş durmalı ve dönüş kuralı tanımlanmalı |
| CB-108 | Portföy yeniden dengeleme | Geliştirme açığı, P2 | Hedef ağırlık, minimum işlem ve maliyet eşiği birlikte çalışmalı |
| CB-109 | VaR ve expected shortfall stres raporu | Geliştirme açığı, P2 | Aşırı olaylar ve korelasyon yükselişi ayrı senaryolanmalı |
| CB-110 | Stablecoin depeg stresi | Geliştirme açığı, P2 | Teminat iskonto değişiminde marj ve stop mesafesi yeniden ölçülmeli |
| CB-111 | Strateji ve sektör bazlı atıf | Geliştirme açığı, P2 | PnL ücret ve funding dahil strateji/sektör bazında uzlaşmalı |
| CB-112 | Kapasite ve piyasa etkisi analizi | Geliştirme açığı, P2 | Artan emir büyüklüğünde net performans ve dolum değişimi ölçülmeli |

## Veri ve yeni pazarlar

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-113 | L2 defter snapshot-delta yeniden kurma | Geliştirme açığı, P3 | Sequence boşluğu resnapshot ile kapatılmalı |
| CB-114 | Tick geçmişi ve deterministik replay | Geliştirme açığı, P3 | Girdi hashleriyle aynı sonuç yeniden üretilebilmeli |
| CB-115 | Delist dahil tarihsel evren | Geliştirme açığı, P3 | Geçmişte işlem gören ve sonradan kaldırılan coinler korunmalı |
| CB-116 | Spot hesap ve envanter yürütmesi | Geliştirme açığı, P3 | Spot bakiye ve satış limiti için ayrı adaptör sözleşmesi olmalı |
| CB-117 | COIN-M ters kontrat muhasebesi | Geliştirme açığı, P3 | Kontrat çarpanı ve coin cinsi PnL doğru hesaplanmalı |
| CB-118 | Opsiyon işlemleri ve Greeks riski | Geliştirme açığı, P3 | Vade ve delta/gamma/vega bütçesi tanımlanmalı |
| CB-119 | On-chain ve haber veri bağlama | Geliştirme açığı, P3 | Yayın zamanı, elde edilme zamanı ve gecikme kaydedilmeli |
| CB-120 | ML eğitim ve model yaşam döngüsü | Geliştirme açığı, P3 | Veri sızıntısı, drift, model sürümü ve geri alma sınanmalı |

## Operasyon ve ölçülebilir kabul

| Kimlik | Senaryo | Değerlendirme | Kabul ölçütü |
|---|---|---|---|
| CB-121 | Paper işlem için tam dolum simülatörü | Geliştirme açığı, P2 | Gerçek hesaba bağlanmadan emir defteri ve portföy yürütülmeli |
| CB-122 | Prometheus operasyon metrikleri | Geliştirme açığı, P2 | Veri yaşı, kuyruk, rate limit ve korumasız pozisyon ölçülmeli |
| CB-123 | Yedekten geri dönüş tatbikatı | Geliştirme açığı, P2 | Plan, rezervasyon ve order journal tutarlı geri yüklenmeli |
| CB-124 | Çok makineli lider seçimi | Geliştirme açığı, P2 | İki makine aynı hesabın yürütücülüğünü eşzamanlı alamamalı |
| CB-125 | Uzun süreli hata enjeksiyonu | Geliştirme açığı, P2 | Ağ bölünmesi, disk dolması ve süreç öldürme zincirleri raporlanmalı |
| CB-126 | Canary ve sürüm geri alma | Geliştirme açığı, P2 | Eski kayıtların yeni/eski sürümde okunabilirliği doğrulanmalı |
| CB-127 | Sembol bazlı kabul panosu | Geliştirme açığı, P2 | Her coin için doğrulama, simülasyon ve borsa kabulü ayrı gösterilmeli |
| CB-128 | Net performans karşılaştırma raporu | Geliştirme açığı, P2 | Buy-and-hold, nakit ve basit strateji kıyasları aynı maliyetle sunulmalı |
