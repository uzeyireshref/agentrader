# Alarm evaluation timing and frequency — 2026-11-13

Status: delivered. Production bundle index-DnWt9qhF.js, local server PID4752 restarted with new backend. API scope now CLOSED_AND_SAMPLED_LIVE_CANDLE_LOCAL_HISTORY; runtime_error=null and order_authority=false checked. No personal test alarm was created or modified.

## REA investigation

Connected to the existing Chrome target for REA Arastirma (E7UZkcrO) on port9338. Initial9222 probe was unreachable; process inspection identified the actual port. Used declared REA scenarios to open the editor, expand the price frequency menu, select the existing BB source and expand its frequency menu. No Create action was used, no subscription gate bypassed and no server alarm was created.

Price UI exposes Once only and Every time, with the latter explicitly described as once per minute while the condition remains met. BB exposes Once only, Once per bar, Once per bar close and Once per minute. This is observed UI behavior, not observation of TradingView server evaluator execution. A few transient source-selector captures failed while its UI changed between input and button; the settled button scenario succeeded. Escape closed the entire draft rather than just the dropdown; the following Cancel action therefore failed. Passive follow-up verified no Cancel/draft and the chart remained1W with All changes saved. The original chart/layout was retained.

Evidence identifiers:
- discovery ev_5b82045657fb138959f5ff8be52b1c4ee9fe1a682c7cfe721d909b09db5230f8
- price frequency ev_2378dcbc1ef0987be24913fefae1688de5eea4cc2f3c8fbcfb336dd9b5fc4928
- BB frequency and draft dismissal: see focused REA summary JSON alongside this report
- passive cleanup ev_ba0e496d4748258d859cb068eeaa4d5a056209366335061c1e66ae10659e36b6

Full authenticated REA export: reports/rea-alert-frequencies-20261113.json (50 records, includes other records retained in this REA session). The export is evidence coverage, not a claim of server runtime parity.

## Local contract

Existing saved definitions are unchanged: legacy/v2/v3 once still means once at bar close, and bar_close means each qualifying close. New intrabar settings use strict technical-alert/4 with evaluation=intrabar, resolved explicit per-condition intervals and frequency once/bar/minute. No silent migration of active alarms.

- once: first qualifying new observed sample, then state TRIGGERED.
- bar: at most once per smallest-interval candle, even if conditions alternate false/true within it.
- minute: at least60000 exchange-event milliseconds between qualifying events. This is a local rolling interval; TradingView's precise calendar-vs-rolling boundary was not established.

The existing worker samples latest feed contexts approximately once per second, plus processing time. It does not subscribe to every exchange tick and can miss brief between-sample transitions. There is deliberately no every-tick/zero-latency option. Base timeframe uses the current forming/just-closed row; indicators recompute from the same canonical candle algorithms. Other timeframes use only their latest fully closed rows as of the base exchange event time, with no future bar leakage. Cross/enter/exit operators compare the previous candle against the current candle snapshot, as in existing candle-series algebra; they are not tick-to-tick crossings. A higher-timeframe cross can remain true until its next close.

A live condition can disappear by candle close. The committed event is not erased; it records evaluation, observed_at (exchange milliseconds), confirmed, source opening timestamps, immutable definition, sampled close and condition results. History displays the real observation timestamp for intrabar events and labels forming vs confirmed candles. No order authority or external service delivery added.

New sample identity includes base revision/time and the aligned source epoch/close identity. Repeated or backwards samples do not generate another event. The event and checkpoint commit in the same SQLite transaction. Bar and minute limits survive worker boot, stale recovery and source epoch changes. Explicit edit/pause/resume re-arms as before and resets checkpoint limits; these are user lifecycle actions, unlike process restart.

Initial startup, reconnect/epoch change, stale/invalid data and sample gaps over20seconds baseline without replay. The first valid sample does not fire; later fresh qualifying samples can fire. A late higher-timeframe close waits without advancing the base sample checkpoint. All operands must be known, including ANY combinations. Unsupported geometry remains excluded; indicator warmup stays WAITING_CALCULATION. Capacity remains the existing shared feed cap.

## Verification

- Full backend regression:967 passed when11 new tests were present. Subsequently added two boundary/thread tests; targeted final13 intrabar tests all passed. Existing full-suite warning is the Starlette/httpx deprecation.
-13 new tests cover strict schema and compatibility, once/repainting retention, per-bar flip/reconnect/new-bar gating, rolling minute across UTC boundary and boot, duplicate/backwards sample, stale/invalid input, missing sample window, candle-reference crossover, forming indicator/warmup, higher-timeframe future exclusion, API persistence/conflict, delayed boundary exactly-once, and actual worker thread without browser/close event.
- Full frontend312 passed; TypeScript and production build passed (existing bundle-size warning).
- Chart P7 evidence check36/36 passed after regenerating binding_evidence.json for the market_feed context metadata addition.
- New production Chrome acceptance7 groups passed; existing multi-condition editor11 groups passed. No page errors. Dark/light/600px screenshots reviewed. All browser API writes use isolated fixtures, not personal workspace data.
- Actual real-engine forming event generated in a temporary migrated database by python -m scripts.create_intrabar_fixture. Browser acceptance: scripts/check_alert_frequencies.mts. Evidence: reports/alert-frequencies-ui-20261113/result.json and screenshots. Test logs: reports/alert-frequencies-backend-tests.log and reports/alert-frequencies-frontend-tests.log.

## Primary references

[TradingView frequency choices by alert type](https://www.tradingview.com/support/solutions/43000690908-why-is-the-once-per-bar-option-missing/)

[TradingView alert frequency explanations](https://www.tradingview.com/support/solutions/43000474415-differences-between-alert-frequencies/)

[TradingView intrabar indicator alert mismatch explanation](https://www.tradingview.com/support/solutions/43000741171-issue-with-once-per-bar-alert/)

[TradingView Pine alert frequency and repainting contract](https://www.tradingview.com/pine-script-docs/concepts/alerts/)
