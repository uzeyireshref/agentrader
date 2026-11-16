"""View policy is separate from immutable LINEAR geometry semantics."""
LOG_BLOCKED = ('trend', 'ray', 'extended_line', 'parallel_channel')


def view_policy(kind, implemented=True):
    return dict(schema='chart-scale-policy/1', geometry_scale='LINEAR',
                LINEAR='SUPPORTED' if implemented else 'NOT_IMPLEMENTED',
                LOG=('ANCHOR_LABEL_ONLY' if kind in ('text', 'note', 'price_label') else 'PRICE_LEVELS_OR_ENDPOINT_MEASUREMENT' if kind in ('horizontal', 'horizontal_ray', 'zone', 'fibonacci', 'fibonacci_extension', 'fibonacci_projection', 'ruler', 'long_plan', 'short_plan') else 'BLOCKED_STRAIGHT_SLOPE') if implemented else 'NOT_IMPLEMENTED',
                log_geometry_query='SUPPORTED_PRICE_DELTA' if kind=='fibonacci_projection' else 'BLOCKED_UNSUPPORTED_SCALE',
                view_change_mutates_geometry=False)
