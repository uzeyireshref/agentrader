"""Versioned wall-clock notification windows. Monitoring is never gated here."""
from datetime import datetime, timezone
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def minute(value, *, end=False):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{2}:[0-9]{2}', value):
        raise ValueError('INVALID_SCHEDULE_TIME')
    h, m = map(int, value.split(':'))
    if m > 59 or h > 23 and not (end and h == 24 and m == 0):
        raise ValueError('INVALID_SCHEDULE_TIME')
    return h*60+m


def validate_schedule(value):
    if not isinstance(value, dict) or set(value) != {'schema', 'mode', 'timezone', 'windows'}:
        raise ValueError('INVALID_NOTIFICATION_SCHEDULE')
    if value['schema'] != 'alert-notification-schedule/1' or value['mode'] not in ('always', 'custom'):
        raise ValueError('INVALID_NOTIFICATION_SCHEDULE')
    name = value['timezone']
    if not isinstance(name, str) or not 1 <= len(name) <= 100:
        raise ValueError('INVALID_SCHEDULE_TIMEZONE')
    try:
        ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError):
        raise ValueError('INVALID_SCHEDULE_TIMEZONE') from None
    windows = value['windows']
    if not isinstance(windows, list) or (value['mode'] == 'always' and windows) or (value['mode'] == 'custom' and not 1 <= len(windows) <= 7):
        raise ValueError('INVALID_SCHEDULE_WINDOWS')
    checked = []
    for window in windows:
        if not isinstance(window, dict) or set(window) != {'days', 'start', 'end'}:
            raise ValueError('INVALID_SCHEDULE_WINDOW')
        days = window['days']
        if not isinstance(days, list) or not 1 <= len(days) <= 7 or any(type(d) is not int or d not in range(7) for d in days) or len(set(days)) != len(days):
            raise ValueError('INVALID_SCHEDULE_DAYS')
        if minute(window['start']) == minute(window['end'], end=True):
            raise ValueError('EMPTY_SCHEDULE_WINDOW')
        checked.append(dict(days=sorted(days), start=window['start'], end=window['end']))
    return dict(schema=value['schema'], mode=value['mode'], timezone=name, windows=checked)


def notification_gate(definition, timestamp):
    value = definition.get('notification_schedule')
    if 'notification_schedule' not in definition:
        return None  # legacy event contract, implicitly 24/7
    try:
        schedule = validate_schedule(value)
        local = datetime.fromtimestamp(timestamp, timezone.utc).astimezone(ZoneInfo(schedule['timezone']))
        now = local.hour*60+local.minute
        allowed = schedule['mode'] == 'always'
        for window in schedule['windows']:
            start, end = minute(window['start']), minute(window['end'], end=True)
            if start < end:
                allowed |= local.weekday() in window['days'] and start <= now < end
            else:
                # The selected weekday owns the start of an overnight session.
                allowed |= (local.weekday() in window['days'] and now >= start
                            or (local.weekday()-1) % 7 in window['days'] and now < end)
        return dict(schema='alert-notification-gate/1', allowed=allowed,
                    reason='IN_SCHEDULE' if allowed else 'OUTSIDE_SCHEDULE',
                    timezone=schedule['timezone'], local_time=local.isoformat())
    except (ValueError, TypeError, KeyError, ArithmeticError, OSError):
        return dict(schema='alert-notification-gate/1', allowed=False, reason='INVALID_SCHEDULE',
                    timezone=str(value.get('timezone', '')) if isinstance(value, dict) else '')


def apply_notification_schedule(event, definition, timestamp):
    gate = notification_gate(definition, timestamp)
    if gate is not None:
        event['notification_gate'] = gate
    return gate is None or gate['allowed']
