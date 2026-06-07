from __future__ import annotations

from fastapi import HTTPException, Request, status


def get_bearer_or_api_key(request: Request) -> str:
    auth_header = request.headers.get('authorization', '')
    if auth_header.lower().startswith('bearer '):
        return auth_header.split(' ', 1)[1].strip()

    x_api_key = request.headers.get('x-api-key')
    if x_api_key:
        return x_api_key.strip()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Missing API key',
    )


def get_session_cookie(request: Request, cookie_name: str) -> str:
    session_token = request.cookies.get(cookie_name)
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Not signed in',
        )
    return session_token
