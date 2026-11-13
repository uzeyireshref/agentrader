"""Explicit local worker. W1 processes runtime.inspect only, never trading actions."""
import time

from ..locking import execution_lock
from .queries import StorageUnavailable


def process_one(service):
    claimed = service.queue.claim(service.settings.owner)
    if claimed is None:
        return {'state': 'IDLE'}
    if claimed['state'] == 'FAILED':
        return claimed
    rid = claimed['request_id']
    try:
        result = service.status()
    except (StorageUnavailable, OSError):
        service.queue.finish(service.settings.owner, rid, error_code='STATUS_UNAVAILABLE')
    else:
        service.queue.finish(service.settings.owner, rid, result=result)
    return service.command(rid)


def run_worker(service, *, once=False, interval=2, sleep=time.sleep, emit=None):
    if type(interval) is not int or not 1 <= interval <= 10:
        raise ValueError('İşçi aralığı 1–10 saniye olmalı.')
    service.initialize()
    # Separate from the financial execution_lock path: read-only work may coexist
    # with an existing trading monitor. Only one application worker may claim.
    with execution_lock(service.settings.worker_lock):
        try:
            while True:
                service.queue.heartbeat('RUNNING')
                result = process_one(service)
                if emit is not None:
                    emit(result)
                if once:
                    return result
                sleep(interval)
        finally:
            service.queue.heartbeat('STOPPED')
