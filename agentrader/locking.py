"""Süreç çökmesinde işletim sistemi tarafından bırakılan tek yürütücü kilidi."""
import os
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def execution_lock(path=Path('data/runtime.lock')):
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open('a+b')
    if path.stat().st_size == 0:
        stream.write(b'0')
        stream.flush()
    stream.seek(0)
    locked = False
    try:
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError:
            raise ValueError('Başka bir işlem motoru çalışıyor; paralel emir gönderimi reddedildi.') from None
        yield
    finally:
        if locked:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()
