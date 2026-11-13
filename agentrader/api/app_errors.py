from fastapi.responses import JSONResponse


def error_response(code, status):
    return JSONResponse({'error': {'code': code}}, status_code=status)
