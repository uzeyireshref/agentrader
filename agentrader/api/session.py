"""Local browser pairing. The configured web token never enters persistent JS storage."""
import hashlib
import hmac
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

COOKIE = 'agentrader_local_session'


def cookie_value(settings, expires=None):
    expires = int(time.time()) + 43200 if expires is None else expires
    digest = hmac.new(settings.token.encode(), ('agentrader-local-browser-v1:' + str(expires)).encode(), hashlib.sha256).hexdigest()
    return str(expires) + '.' + digest


def authenticated(request, settings):
    if not settings.token:
        return False
    supplied = request.headers.get('authorization')
    if supplied is not None:
        return hmac.compare_digest(supplied.encode('utf-8'), ('Bearer ' + settings.token).encode())
    cookie = request.cookies.get(COOKIE, '')
    try:
        expires = int(cookie.split('.', 1)[0])
        if not time.time() < expires <= time.time() + 43260:
            return False
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(cookie.encode('utf-8'), cookie_value(settings, expires).encode())


def session_router(settings):
    router = APIRouter()

    @router.get('/api/session')
    def status(request: Request):
        return {'enabled': bool(settings.token), 'authenticated': authenticated(request, settings)}

    @router.post('/api/session')
    def pair(request: Request):
        if not authenticated(request, settings):
            return JSONResponse({'error': {'code': 'UNAUTHORIZED'}}, status_code=401)
        response = JSONResponse({'enabled': True, 'authenticated': True})
        response.set_cookie(COOKIE, cookie_value(settings), max_age=43200, httponly=True,
                            samesite='strict', secure=False, path='/api')
        return response

    @router.delete('/api/session')
    def unpair():
        response = JSONResponse({'authenticated': False})
        response.delete_cookie(COOKIE, path='/api', httponly=True, samesite='strict')
        return response

    return router
