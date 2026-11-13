# Per-alert notification schedule delivery — 2026-11-13

Status: delivered. Production index-D4BFG9TI.js; server PID2280 restarted. Actual GET /api/alerts runtime_error=null and order_authority=false, and production bundle availability verified. No personal alarm or workspace test writes.

## Investigation

REA used the existing REA Arastirma layout E7UZkcrO through CDP9338. Notifications menu, 24/7, weekday/workday presets and custom day/time editor were inspected. A draft custom Monday–Friday22:00–04:00 range was accepted by Set schedule and displayed in the notifications draft. No Create or Apply action was used. Escape discarded the draft; passive cleanup verified no editor and original1W layout saved. A subsequent fresh editor confirmed the original24/7 default was retained, then was discarded too.

One attempt selected literal role attributes that were not present in DOM; the corrected Playwright role-engine locator succeeded. Failed and successful steps are retained. REA observation establishes UI configuration, not real server triggering or DST behavior on TradingView. No server-side TradingView test alarm was created.

Evidence: reports/rea-alert-schedule-summary-20261113.json and authenticated full export reports/rea-alert-schedule-20261113.json (59 retained session records, including prior investigations). Final cleanup ev_99803ea8179a0d4b6215d5a2007a317c7b011c92251221c6c6b55ab995e01548. Original24/7 default reinspection is retained in the export.

[TradingView's primary announcement](https://www.tradingview.com/blog/en/notification-schedule-for-alerts-59369/) documents silent history outside scheduled hours, overnight sessions and the special behavior whereby a muted single-use alert remains active. Those semantics informed the implementation below. UI observation did not independently exercise TradingView's single-use runtime.

## User interface

Alarm editor > Takvim is specific to the alarm being created/edited. It provides24/7, weekdays all day, weekdays09:00–18:00 and custom presets; IANA timezone input with suggestions/local-time preview; up to7 OR windows; day buttons; full-day toggle; start/end times; overnight explanation. The manager shows configured custom windows and zone. History identifies muted records and their decision's local timestamp/zone.

Global browser sound/desktop preferences stay under Bildirimler. Per-alarm channel choices remain the next separate step. Saving the alarm uses the existing explicit save-and-restart/re-arm lifecycle. No sticky schedule inheritance was introduced for new alerts; their default is24/7.

## Persistent contract

Optional notification_schedule is validated for legacy and technical-alert/2,/3,/4 definitions, without silently rewriting existing definitions. It has its own alert-notification-schedule/1 version, mode always/custom, timezone and windows. Always requires an empty windows array. Custom requires1–7 windows with unique integer weekdays0(Monday)–6(Sunday), HH:MM start and end. Start24:00 is rejected; end24:00 is allowed for a selected day's midnight endpoint. Equal times are rejected; full-day is explicit00:00–24:00. Multiple windows are a union; overlaps are allowed.

Event generation, condition watching, frequency limits and history remain active outside the notification window. At committed event creation time (server timestamp, not candle opening time or browser receipt time), the backend stores notification_gate with a version, allowed flag, reason, IANA zone and local offset-aware timestamp. Legacy definitions without a schedule retain implicit24/7 and no added gate. Both confirmed-close and sampled-live paths use the same gate. Invalid persisted schedule data fails closed for notification and is visible in history.

Start is inclusive, end exclusive. Overnight sessions belong to the selected start day, including Sunday to Monday. IANA wall-clock conversion handles offsets and DST: a repeated local hour matches on both occurrences; a skipped local interval has no corresponding instants. tzdata is declared as a runtime dependency for Windows, where a system IANA database is not generally available. The environment already supplied tzdata2025.3; no package installation was needed. [Python zoneinfo documentation](https://docs.python.org/3/library/zoneinfo.html) describes this fallback.

Single-use alerts do not enter TRIGGERED for muted events. The next new qualifying occurrence inside a window can consume the alert. A sampled-live once alarm records at most one muted history record per base candle to avoid one silent record per sampled tick; this does not block an allowed occurrence in the same candle. Other bar/minute gates continue to apply, so opening a schedule is not a re-arm or deferred replay of an earlier condition.

Browser receipt collection claims muted events silently and creates neither toast, sound, desktop delivery nor unread badge for them. They remain in server history. No later browser clock/window change replays a muted event. A scheduled event missing a recognized gate is also suppressed, rather than evaluated with a separate browser timezone algorithm. Existing delivery preference, staleness and atomic two-tab receipt guards remain active.

## Verification

- Full backend978 passed, full frontend315 passed, TypeScript and production build passed. Existing Starlette/httpx deprecation and bundle-size warnings remain.
-9 new backend tests: strict inputs, legacy/always, Baku boundary and Nepal45minute offset, full day, Friday overnight/week wrap, New York DST fold/gap, OR windows, immutable snapshots, confirmed once muted/allowed state, sampled once muted dedup/allowed same candle, regular muted monitoring, API roundtrip/revision conflict/invalid timezone/no execution DB.
-3 new frontend tests cover presets/error validation, snapshot preservation across legacy/live/close edits, and mute/receipt/no replay behavior.
-8 new Chrome production acceptance groups pass: save Friday overnight/Baku, reload/edit/summary, invalid zone/empty day no writes, multiple/full-day windows, presets/return24/7, real muted history with no notifications, real allowed notification/read/reload, dark/light/600px layout. No page errors.
- Regression Chrome suites:7 frequency groups and11 notification groups passed, including real AudioContext oscillator starts, mocked desktop permission, real Web Locks coordination, network/storage recovery. OS notification display is mocked; no test OS notification was sent.
- Fixtures come from actual PriceAlerts with temporary DB and controlled server clock: python -m scripts.create_schedule_fixture. It asserts muted single-use ACTIVE then allowed TRIGGERED. Browser fixture replaces created_at only for freshness testing while preserving the recorded gate. scripts/check_alert_schedule.mts reproduces browser acceptance with app running on8765.
- Evidence: reports/alert-schedule-ui-20261113/result.json, engine-events.json, schedule-dark.png, schedule-light.png, schedule-mobile.png, muted-history.png. Logs: reports/alert-schedule-backend-tests.log and reports/alert-schedule-frontend-tests.log.

Browser deliveries still need an open application tab and are subject to browser/OS scheduling. No external delivery channel, closed-browser push, per-alarm channel preference or bot-order bridge was added by this step.
