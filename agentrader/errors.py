"""Safe exchange errors: never include signed URLs, credentials or raw bodies."""


class ExchangeError(Exception):
    def __init__(self, message, code=None, http_status=None, *, delivery_status=None,
                 retry_after=None, retryable=False, rate_limit_headers=None):
        super().__init__(message)
        self.code, self.http_status = code, http_status
        self.delivery_status = delivery_status
        self.retry_after = retry_after
        self.retryable = retryable
        self.rate_limit_headers = rate_limit_headers or {}
