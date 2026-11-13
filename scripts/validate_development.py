"""Run offline regression checks and record evidence without any trade probe."""
import io
import json
from pathlib import Path
import sys
import unittest
from datetime import datetime,timedelta,timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    output=io.StringIO()
    result=unittest.TextTestRunner(stream=output,verbosity=1).run(suite)
    date=datetime.now(timezone(timedelta(hours=4))).date().isoformat()
    report_path=ROOT/('reports/development-validation-'+date.replace('-','')+'.json')
    report={'date':date,'test_command':'python scripts/validate_development.py',
            'suite':'complete repository suite','test_count':result.testsRun,
            'result':'PASSED' if result.wasSuccessful() else 'FAILED',
            'verification':'OFFLINE_AND_FAKE_EXCHANGE','demo_writes_performed':0,
            'background_monitor_started':False,'real_demo_write_verified':False,
            'telegram_messages_sent':0,'scheduled_tasks_registered':0,
            'failures':[str(case) for case,_ in result.failures+result.errors],
            'skipped_count':len(result.skipped),
            'details':'18-GRID-BORSA-STOP-YENILEME.md',
            'covered_scenarios':['LONG_SHORT_trailing','staged_exit_remaining_quantity',
                'stop_replacement_before_cancel','restart_and_unknown_delivery',
                'managed_isolated_margin','dynamic_grid_brackets','batch_create_amend_cancel',
                'WebSocket_REST_barrier','notification_retry_lease','service_stop_entry_revocation',
                'multi_session_distinct_symbol_ownership','shared_single_grid_reservations',
                'multi_start_combined_budget_before_any_post','peer_unrealized_and_daily_loss',
                'independent_close_stop_and_atomic_release','pre_claim_unused_reservation_recovery',
                'neutral_shared_budget_two_hedge_legs','neutral_partial_fill_restart_unknown_delivery',
                'neutral_gross_stop_and_native_child_cleanup','neutral_self_cross_cancel_barrier',
                'neutral_active_leg_protection_before_flat_retirement',
                'multi_session_margin_ownership_and_projected_collateral',
                'grid_margin_pending_refill_budget','neutral_side_specific_margin',
                'margin_cli_selected_risk_profile','margin_unknown_post_never_resent',
                'grid_bot_trailing_long_short_restart','grid_trailing_partial_and_cancel_race',
                'grid_trailing_unknown_close_and_refill_barrier',
                'grid_native_close_all_replacement_before_cancel','grid_native_stop_unknown_post_delete',
                'grid_native_child_partial_full_and_pending','grid_native_stop_peer_ownership'],
            'real_demo_event_test':'PENDING_CONCRETE_VALID_TRADE_AUTHORIZATION'}
    report_path.write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(output.getvalue(),end='')
    print(json.dumps({'result':report['result'],'test_count':report['test_count'],
                      'report':report_path.relative_to(ROOT).as_posix()}))
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
