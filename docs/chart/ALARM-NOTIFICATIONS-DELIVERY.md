# Alarm notifications delivery — 2026-11-13

Delivered in production bundle index-D2PRm3DF.js. Localhost8765 serves the current bundle; alarm runtime_error=null, order_authority=false. Backend definition schemas and delivery=LOCAL_HISTORY remain unchanged: browser notifications are presentation of committed events, not a new server delivery guarantee.

## Behavior

App-level event polling runs independently of whether the alarm dialog is open. The upper Alarm button shows unread count; up to three persistent dismissible cards show new events. Opening history acknowledges unread events. Dismissing a card does not mark history read. Notification text is rendered as text, including user messages.

Alarm > Bildirimler contains browser-wide preferences (immediately persisted): in-app cards on by default, sound and desktop off by default. Preferences apply to all alarms in this browser, not per-alarm or across devices. The test-sound button activates the current tab AudioContext and plays a short two-tone chime. Saved sound preference needs user activation in a new/reloaded tab; the UI explains this and failed playback shows a warning. Desktop permission is requested only on explicit user action. Denial, unavailable API, OS delivery errors and polling/storage errors have visible status; the upper Alarm button also signals runtime delivery errors.

First-ever sync baselines old history silently. Subsequent unknown event IDs become unread; only events created within 120 seconds (and not more than 5 seconds in the future) attempt disruptive delivery. Receipt IDs persist across reload and are claimed before delivery under a same-origin Web Lock. Repeated/reordered responses and two Chromium tabs cannot attempt desktop delivery twice for the same receipt. With no Web Locks API, claim coordination is best-effort across tabs; receipt dedup still works within each tab. If storage fails, status discloses tab-only memory persistence. Receipt retention: 1000 IDs, 100 unread IDs; source API returns the latest 100 events. A claim records an attempt, not OS acknowledgement: crash/OS suppression does not trigger resend.

One sound and at most one desktop summary are attempted per newly collected batch. Existing cards are capped at three; all committed events remain available through server history. Desktop notification closes after 15 seconds and its click focuses the application and opens history. Sound can only play in a tab whose audio context is running; a different unactivated tab winning the shared event claim can require that tab's sound activation.

The application tab must stay open for these channels. Background scheduling/OS settings can delay or suppress notification/audio; this is not closed-browser push. Server-side monitoring and event history continue while the server is running. No external service, webhook or order submission was added.

## Verification

- Four notification-state tests: baseline/reorder/reload dedup, stale/future backlog, malformed preferences/receipts, bounded retention/read IDs.
- Full frontend suite: 311 passed. TypeScript and production build passed. Existing bundle size warning remains.
- Backend alarm regression: 29 passed (no backend implementation changed in this delivery).
- Browser acceptance: 11 groups passed, no page errors. Actual Chromium AudioContext oscillator starts and Web Locks were exercised. OS Notification API and permission are mocked deliberately; no test OS messages are sent and real OS presentation is not verified.
- Fixture engine-event.json is produced by actual PriceAlerts crossing in a temporary migrated DB; production personal alerts/workspace are never written. Browser fixture preserves its event shape and replaces ID/created_at for deterministic delivery checks.
- Cases: initial history silence; explicit permission/audio unlock; event to card/count/sound/desktop; repeated polling; reload/preferences/unread; history acknowledgement; channels disabled; denied permission recovery text; shared two-tab claim; dark/light/600px layout; polling failure/recovery; blocked storage with memory dedup.
- Evidence: reports/alert-notifications-20261113/result.json, preferences-dark.png, preferences-light.png, preferences-mobile.png, toast-dark.png; frontend log reports/alert-notifications-frontend-tests.log.

Reproduce fixture: python -m scripts.create_notification_fixture. Run browser acceptance with bundled node and frontend/node_modules/tsx/dist/cli.mjs scripts/check_alert_notifications.mts (local app running on 8765). Existing scripts/check_alert_conditions.mts also passed after integration.

## Browser references

[Notifications API and user gesture/secure context](https://developer.mozilla.org/en-US/docs/Web/API/Notifications_API/Using_the_Notifications_API)

[Chrome audio autoplay and suspended AudioContext](https://developer.chrome.com/blog/autoplay)

[Web Locks standard](https://www.w3.org/TR/web-locks/)
