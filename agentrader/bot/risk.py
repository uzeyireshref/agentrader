"""Modelden bağımsız, Decimal tabanlı demo risk denetimi."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR, InvalidOperation
import time
import json
from pathlib import Path


@dataclass(frozen=True)
class RiskLimits:
    # Yalnızca otomatik demo deneyleri için; canlı risk tercihleri değildir.
    max_trade_loss: Decimal = Decimal('5')
    max_total_loss: Decimal = Decimal('10')
    max_daily_loss: Decimal = Decimal('25')
    max_notional: Decimal = Decimal('100')
    max_positions: int = 1
    max_age_seconds: int = 15

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        expected = set(cls.__dataclass_fields__)
        if set(data) != expected:
            raise ValueError('Demo risk profili alanları eksik veya desteklenmiyor.')
        for key in expected:
            data[key] = number(data[key])
            if data[key] <= 0:
                raise ValueError('Risk sınırları pozitif olmalı.')
        for key in ('max_positions', 'max_age_seconds'):
            if data[key] != data[key].to_integral_value():
                raise ValueError('Pozisyon sayısı ve veri yaşı tam sayı olmalı.')
            data[key] = int(data[key])
        return cls(**data)


def number(value):
    try:result = Decimal(str(value))
    except (InvalidOperation,ValueError,TypeError):raise ValueError('Risk girdisi geçerli sayı olmalı.') from None
    if not result.is_finite():
        raise ValueError('Risk girdisi sonlu sayı olmalı.')
    return result


def evaluate(entry, stop, quantity, equity, open_risk, daily_loss, positions,
             observed_at, limits=RiskLimits(), now=None):
    now = time.time() if now is None else now
    entry, stop, quantity, equity, open_risk, daily_loss = map(
        number, (entry, stop, quantity, equity, open_risk, daily_loss))
    if min(entry, stop, quantity, equity) <= 0 or min(open_risk, daily_loss) < 0:
        raise ValueError('Risk girdileri geçersiz.')
    if not 0 <= number(now) - number(observed_at) <= limits.max_age_seconds:
        raise ValueError('Veri eski veya gelecekte tarihli.')
    risk = abs(entry - stop) * quantity
    if risk == 0:
        raise ValueError('Stop ile giriş aynı olamaz.')
    checks = [(risk <= limits.max_trade_loss, 'İşlem başına kayıp sınırı'),
              (risk + open_risk <= limits.max_total_loss, 'Toplam açık risk sınırı'),
              (daily_loss + open_risk + risk <= limits.max_daily_loss, 'Günlük kayıp bütçesi'),
              (positions < limits.max_positions, 'Pozisyon sayısı sınırı'),
              (entry * quantity <= limits.max_notional, 'Nominal tutar sınırı'),
              (entry * quantity <= equity, 'Kullanılabilir bakiye sınırı')]
    for valid, reason in checks:
        if not valid:
            raise ValueError(reason)
    return {'estimated_stop_loss': str(risk), 'notional': str(entry * quantity)}


def size_for_risk(entry, stop, loss_budget, step):
    entry, stop, loss_budget, step = map(number, (entry, stop, loss_budget, step))
    if min(entry, stop, loss_budget, step) <= 0 or entry == stop:
        raise ValueError('Miktar hesabı girdileri geçersiz.')
    return (loss_budget / abs(entry - stop) / step).to_integral_value(rounding=ROUND_FLOOR) * step
