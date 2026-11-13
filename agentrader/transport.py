"""Shared JSON transport: bounded GET retry, persistent cooldown, no mutation retry."""
import json
import math
import re
import sqlite3
import time
from contextlib import closing
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit

from .errors import ExchangeError


def retry_after_seconds(headers, now=None):
    value = headers.get('Retry-After') if headers else None
    if value is None: return None
    try:
        seconds = float(value)
        if not math.isfinite(seconds): return None
        return max(0, seconds)
    except (TypeError,ValueError):
        try:
            stamp = parsedate_to_datetime(str(value)[:256]).timestamp()
            return max(0, stamp-(time.time() if now is None else now))
        except (TypeError,ValueError,OverflowError): return None


def rate_headers(headers):
    result = {}
    for key,value in (headers.items() if headers else []):
        name = key.lower()
        if re.fullmatch(r'x-mbx-(?:used-weight|order-count)(?:-\d+[smhd])?',name):
            if re.fullmatch(r'\d{1,15}',str(value)):
                result[name] = int(value)
    return result


class RequestGovernor:
    """Host-wide cooldown shared by local processes and independent of API key."""
    def __init__(self,path=Path('data/request-governor.sqlite3'),clock=time.time):
        self.path, self.clock = Path(path), clock

    def check(self,host):
        if not self.path.exists(): return
        with closing(sqlite3.connect(self.path,timeout=5)) as db:
            row = db.execute('SELECT until_ts FROM host_limits WHERE host=?',(host,)).fetchone()
        if row and row[0] > self.clock():
            raise ExchangeError('İstek bekleme süresi devam ediyor; ağ çağrısı yapılmadı.',
                                http_status=429,delivery_status='NOT_SENT',retry_after=row[0]-self.clock())

    def record(self,host,headers,http_status=None):
        retry = retry_after_seconds(headers,self.clock())
        limits = rate_headers(headers)
        if http_status in (418,429) and retry is None:
            retry = 300 if http_status==418 else 60
        if not limits and retry is None: return
        self.path.parent.mkdir(parents=True,exist_ok=True)
        until = self.clock()+retry if retry is not None else 0
        with closing(sqlite3.connect(self.path,timeout=5)) as db:
            with db:
                db.execute('''CREATE TABLE IF NOT EXISTS host_limits (
                    host TEXT PRIMARY KEY, until_ts REAL NOT NULL, headers TEXT NOT NULL)''')
                db.execute('''INSERT INTO host_limits VALUES (?,?,?) ON CONFLICT(host) DO UPDATE SET
                    until_ts=MAX(until_ts,excluded.until_ts),headers=excluded.headers''',
                           (host,until,json.dumps(limits)))
        return retry


class JsonTransport:
    def __init__(self,governor=None,read_attempts=2,sleep=time.sleep):
        if type(read_attempts) is not int or not 1 <= read_attempts <= 3:
            raise ValueError('Okuma denemesi 1–3 olmalı.')
        self.governor = governor or RequestGovernor()
        self.read_attempts, self.sleep = read_attempts,sleep
        self.last_rate_headers = {}

    def perform(self,opener,request_factory,method,base_url):
        host = urlsplit(base_url).netloc
        attempts = self.read_attempts if method=='GET' else 1
        for attempt in range(attempts):
            try:
                self.governor.check(host)
            except (sqlite3.Error,OSError):
                raise ExchangeError('İstek sınırı kaydı okunamadı; istek gönderilmedi.',delivery_status='NOT_SENT') from None
            request = request_factory()
            try:
                with opener.open(request,timeout=15) as response:
                    headers = getattr(response,'headers',{})
                    self.last_rate_headers = rate_headers(headers)
                    self.governor.record(host,headers)
                    result = json.load(response)
                if not isinstance(result,(dict,list)):
                    raise ValueError('Invalid root type')
                if isinstance(result,dict) and type(result.get('code')) is int and result['code']<0:
                    raise ExchangeError('Binance hata yanıtı döndürdü.',result['code'],200,
                                        delivery_status='READ_FAILED' if method=='GET' else 'UNKNOWN')
                return result
            except HTTPError as exc:
                code,body_message = None,''
                try:
                    payload=json.loads(exc.read())
                    if isinstance(payload,dict):
                        code=payload.get('code') if type(payload.get('code')) is int else None
                        body_message=payload.get('msg','')
                except (ValueError,OSError): pass
                try:
                    retry = self.governor.record(host,exc.headers,exc.code)
                except (sqlite3.Error,OSError):
                    raise ExchangeError('İstek sınırı yanıtı kaydedilemedi; yeni istekler durmalı.',
                                        code,exc.code,delivery_status='READ_FAILED' if method=='GET' else 'UNKNOWN') from None
                self.last_rate_headers=rate_headers(exc.headers)
                delivery='READ_FAILED' if method=='GET' else 'UNKNOWN'
                if method!='GET':
                    if exc.code in (400,401,403,404,405,422) and code not in (None,-1006,-1007):
                        delivery='REJECTED'
                    elif exc.code==503 and body_message in ('Service Unavailable.',
                            'Internal error; unable to process your request. Please try again.'):
                        delivery='REJECTED'
                    elif code==-1008: delivery='REJECTED'
                hints={-1021:'Bilgisayar saatini eşitleyin.',-1022:'Demo anahtar imzasını kontrol edin.',
                       -2014:'Demo API anahtar biçimini kontrol edin.',-2015:'Anahtar/IP/hesap izinlerini kontrol edin.',
                       -2013:'Sorgulanan emir bulunamadı; bu gönderimin reddedildiğini kanıtlamaz.',
                       -4130:'Mevcut Close-All korumasıyla çakışma.',-4509:'Close-All için açık pozisyon gerekli.'}
                hint = 'İstek veya hesap koşullarını kontrol edin.'
                if code in hints: hint=hints[code]
                if exc.code in (418,429): hint='İstek sınırı; ortak bekleme süresi kaydedildi.'
                if exc.code==451: hint='Bölgesel erişim kısıtı; hesap uygunluğunu kontrol edin.'
                error=ExchangeError(f'HTTP {exc.code}, Binance kodu {code}. {hint}',code,exc.code,
                                    delivery_status=delivery,retry_after=retry,
                                    retryable=exc.code in (500,502,503,504),rate_limit_headers=self.last_rate_headers)
            except (URLError,TimeoutError,OSError,sqlite3.Error):
                error=ExchangeError('Ağ/TLS veya yanıt işleme hatası; gönderim durumu doğrulanmalı.',
                                    delivery_status='READ_FAILED' if method=='GET' else 'UNKNOWN',retryable=True)
            except ValueError:
                error=ExchangeError('Binance yanıtı geçerli JSON değil.',
                                    delivery_status='READ_FAILED' if method=='GET' else 'UNKNOWN')
            if method=='GET' and error.retryable and attempt+1<attempts:
                self.sleep(.25 * 2**attempt)
                continue
            raise error from None
