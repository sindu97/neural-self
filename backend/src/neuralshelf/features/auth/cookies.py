"""Refresh-token transport: httpOnly cookie for browsers, body for native apps.

Browsers (default): the refresh token is set as an httpOnly, SameSite cookie
scoped to the auth endpoints and never appears in a response body, so
JavaScript (and therefore XSS) cannot read it. The access token is returned
in the body and kept in memory only.

Native apps send ``X-Auth-Mode: token`` and get the refresh token in the body
to keep in the OS's secure storage; they send it back in the request body.
"""

from fastapi import Request, Response

from neuralshelf.core.config import get_settings
from neuralshelf.core.constants import AUTH_MODE_HEADER, CSRF_HEADER
from neuralshelf.core.exceptions import ApplicationError
from neuralshelf.core.messages import Message, MessageCode


class CsrfCheckFailedError(ApplicationError):
    """A cookie-authenticated request arrived without the CSRF header (HTTP 403)."""

    def __init__(self) -> None:
        super().__init__(
            message=Message.CSRF_CHECK_FAILED,
            code=MessageCode.CSRF_CHECK_FAILED,
            status_code=403,
        )


def uses_token_mode(request: Request) -> bool:
    """Whether a native client asked for tokens in the body (``X-Auth-Mode: token``)."""
    return request.headers.get(AUTH_MODE_HEADER, "").strip().lower() == "token"


def refresh_token_from_request(request: Request, body_token: str | None) -> str | None:
    """The refresh token from the body (native) or the cookie (browser).

    Cookies are sent by the browser automatically, even on requests another
    site triggers, so a cookie is only accepted together with the custom CSRF
    header, which cross-site requests cannot carry without passing CORS.
    """
    if body_token:
        return body_token

    cookie_token = request.cookies.get(get_settings().auth_cookie_name)
    if cookie_token is None:
        return None
    if request.headers.get(CSRF_HEADER) != "1":
        raise CsrfCheckFailedError()
    return cookie_token


def deliver_tokens(request: Request, response: Response, tokens: dict) -> dict:
    """Put the refresh token in a cookie (browser) or leave it in the body (native)."""
    if uses_token_mode(request):
        return tokens

    body = dict(tokens)
    set_refresh_cookie(response, body.pop("refresh_token"))
    return body


def set_refresh_cookie(response: Response, token: str) -> None:
    """Set the httpOnly refresh-token cookie on ``response``."""
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        path=settings.refresh_cookie_path,
        domain=settings.auth_cookie_domain,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )


def clear_refresh_cookie(response: Response) -> None:
    """Expire the refresh-token cookie (logout)."""
    settings = get_settings()
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path=settings.refresh_cookie_path,
        domain=settings.auth_cookie_domain,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )
