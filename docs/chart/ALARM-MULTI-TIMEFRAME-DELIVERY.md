# Multi-timeframe alarm delivery — 2026-11-13

Status: delivered. Production bundle index-CAHG0i0h.js; local server restarted and GET /api/alerts runtime_error=null, order_authority=false.

## Contract

Each condition can inherit the common interval or select its own supported interval. The smallest condition interval drives evaluation. All operands within a condition use that condition's interval; indicator and drawing configurations remain immutable snapshots. Definitions use technical-alert/3 with explicit resolved condition intervals; legacy and technical-alert/2 definitions keep their original behavior. Returning all conditions to the inherited interval saves technical-alert/2.

At each smallest-interval close, each source is trimmed to bars whose close boundary is at or before the evaluation cutoff. The expected last completed source bucket is required, including Monday-anchored weekly buckets. Open and future higher-timeframe bars are excluded. Conditions use their source's last two completed bars or configured lookback, never synthetic interpolated prices.

Example: at 10:11 on a 1m clock with a 5m condition, the higher source uses the 10:05–10:10 bar. Its result remains applicable until the next 5m bar closes. This also means a higher-timeframe crossover remains true during that period: bar_close frequency can record it at each qualifying smallest-interval close; once frequency records only once.

Fresh sources arriving at slightly different times wait in WAITING_ALIGNMENT without advancing the checkpoint, allowing the pending boundary to evaluate when its source arrives. Stale, wrong-identity, malformed or disconnected sources fail closed. Missing multiple smallest-interval bars, worker restart or any source epoch change reseeds without historical replay. Insufficient indicator history stays WAITING_CALCULATION. These rules also apply to ANY conditions; unknown sources cannot be ignored.

The worker owns and deduplicates every required symbol/interval feed and releases references on pause, deletion, expiry and close. Existing shared hub capacity remains eight feeds; unavailable capacity waits for data. Events record source_closes (bar opening timestamps) alongside the immutable definition and condition outcomes.

## Verification

- Six dedicated backend tests: definition validation and minimum clock, future exclusion and exact boundary, weekly anchoring, stale/identity/epoch guards, delayed close exactly-once plus restart suppression, and feed ownership/release.
- Full backend: 956 passed. Full frontend: 307 passed. TypeScript and production build passed.
- Chrome production browser: 11 acceptance groups including independent 1h/15m selection, save/reload/edit, return to inherited interval, 600px layout, dark/light views, expiry and existing lifecycle. No browser console errors; isolated API fixtures, no personal workspace writes.
- Evidence: reports/alerts-conditions-ui-20261113/result.json and screenshots. scripts/check_alert_conditions.mts reproduces acceptance.

Closed-bar evaluation only. Multi-symbol conditions, intrabar evaluation, external notification delivery and automatic orders remain separate work. New channel/pitchfork-family display-only sources are still excluded from alarm operands.
