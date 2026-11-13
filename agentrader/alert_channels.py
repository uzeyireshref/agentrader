"""Per-alert browser channel policy; browser permissions remain a separate ceiling."""
def validate_channels(value):
    if not isinstance(value,dict) or value.get('schema')!='alert-notification-channels/1':
        raise ValueError('INVALID_NOTIFICATION_CHANNELS')
    if value.get('mode')=='inherit' and set(value)=={'schema','mode'}:
        return dict(value)
    keys={'schema','mode','inApp','sound','desktop'}
    if value.get('mode')!='custom' or set(value)!=keys or any(type(value[k]) is not bool for k in ('inApp','sound','desktop')):
        raise ValueError('INVALID_NOTIFICATION_CHANNELS')
    return dict(value)
