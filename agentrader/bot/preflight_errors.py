"""Stable, public rejection reasons; never serialize arbitrary exception text."""
REASONS = frozenset({
    'ACCOUNT_NOT_ELIGIBLE', 'ACCOUNT_MODE_MISMATCH', 'ACCOUNT_SETTINGS_MISMATCH',
    'ACCOUNT_NOT_FLAT', 'SNAPSHOT_STALE', 'COLLATERAL_INSUFFICIENT',
    'BUDGET_TOO_SMALL', 'PRICE_OUTSIDE_PROTECTION', 'PRICE_DRIFT_EXCEEDED',
    'NOTIONAL_LIMIT', 'POSITION_COUNT_LIMIT', 'TRADE_RISK_LIMIT',
    'TOTAL_RISK_LIMIT', 'DAILY_LOSS_LIMIT', 'LIQUIDATION_BUFFER',
    'GRID_PRICE_OUTSIDE_BAND', 'GRID_BUDGET_TOO_SMALL',
})


class PreflightRejection(ValueError):
    def __init__(self, reason, message):
        if reason not in REASONS:
            raise ValueError('Unknown public preflight reason')
        self.reason = reason
        super().__init__(message)
