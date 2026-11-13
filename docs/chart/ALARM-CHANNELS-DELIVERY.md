# Per-alert browser channel preferences — 2026-11-13

Delivered. Production bundle index-D8UGb9zW.js verified at localhost8765. Server PID25884 restarted; API runtime_error=null, order_authority=false. Personal workspace and alarm test writes: zero.

## User behavior

Alarm editor > Kanallar has Tarayici tercihlerini kullan (default) and a custom selection for that alarm: in-app card, sound, desktop. All custom switches off means history-only. The manager summarizes custom channels or inheritance. Settings take effect only when saving the alert; browser-wide preferences remain immediately applied in the upper Bildirimler section.

The effective delivery rule is recorded schedule permission AND selected per-alert channel AND current browser master preference, plus existing OS permission/audio activation constraints. Choosing a per-alert channel never requests permission or silently turns on a browser master switch. The editor explains blocked master switches and directs the user to Bildirimler. Existing alerts without a policy keep their previous inherited behavior.

## Contract and runtime

Optional notification_channels is independently versioned as alert-notification-channels/1 and accepted by all existing definition versions. Inherit has exactly schema/mode; custom has exactly schema/mode/inApp/sound/desktop, all booleans. Wrong types, null, extra fields and ambiguous inherit flags are rejected. No automatic rewrite of persisted alarms or migration is needed.

Existing event.definition already snapshots the full normalized definition, so channel choices are immutable event data. Editing an alarm does not rewrite old events. Inherited policies intentionally use the receiving browser's current preferences; custom selections are intersected with those preferences. Backend cannot confirm desktop/sound delivery and does not claim it.

Receipt collection silently claims history-only or invalid explicit channel policies without unread/card/sound/desktop effects. An explicitly channel-enabled event can remain unread even if browser-wide delivery is currently off, preserving the existing unread-history behavior. Schedule-muted events remain silent regardless of selected channels. Receipt claims, stale-event suppression and cross-tab Web Lock protection remain shared across all channels; changing preferences does not replay claimed events.

A fresh batch is independently filtered for cards, sound and desktop. Only card-selected events enter the card stack; sound is played once if at least one batch event selects sound; the desktop summary count/body/tag comes only from desktop-selected events. This avoids leaking another alarm's name/message into the wrong channel. Existing three-card cap, one sound/desktop summary per batch and browser/OS constraints remain.

History-only once alarms intentionally consume their one qualifying event, reaching TRIGGERED and retaining history. The special schedule-muted once behavior remains unchanged: outside-hours events do not consume the once alert. Channel settings do not alter condition algebra, frequency limits or schedule semantics.

## Verification

- Full backend981 passed; full frontend319 passed; TypeScript and production build passed. Existing Starlette/httpx deprecation and bundle-size warnings remain.
-3 new backend tests: strict policy/old and live schemas; history-only once state and immutable event policy after edits; actual API roundtrip, revision409, bad-policy422 and no execution DB.
-4 frontend tests: legacy inheritance/fail-closed invalid policy, intersection with browser switches, silent history-only and schedule gates, and snapshot retention across legacy/live/close edits.
-7 Chrome acceptance groups: history-only save; sound-only reload/edit/return to inherit without permission prompts; actual four-policy backend batch routed separately to card/sound/desktop/history; browser masters override choices; schedule gate still suppresses; reload does not replay; dark/light and600px editor.
- Actual Chromium AudioContext oscillator starts are measured. OS Notification API/permission are mocked; real OS presentation is not claimed and no OS test notification was sent.
- Fixture generator python -m scripts.create_channel_fixture uses actual PriceAlerts and a temporary migrated DB to produce four once events and verifies all4 reach TRIGGERED. Script scripts/check_alert_channels.mts reads their unmodified policy snapshots and refreshes created_at for delivery freshness. API/WebSocket browser fixture routes are isolated from personal data.
- Calendar regression Chrome8 groups passed after channel integration. Global notification regression is recorded in reports/alert-notifications-20261113/result.json.
- Evidence: reports/alert-channels-ui-20261113/result.json, engine-events.json, channels-dark.png, channels-light.png, channels-mobile.png, channel-delivery.png. Logs: reports/alert-channels-backend-tests.log and reports/alert-channels-frontend-tests.log.

The browser app must remain open for browser channels. This step adds no webhook, external push or automatic order bridge. The next agreed phase is bot integration, initially without order submission.
