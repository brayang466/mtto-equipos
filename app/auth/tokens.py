from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


def _serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt="pw-reset-mtto-equipos")


def make_password_reset_token(secret_key: str, user_id: int) -> str:
    return _serializer(secret_key).dumps({"uid": int(user_id)})


def read_password_reset_token(secret_key: str, token: str, max_age: int = 86400) -> int | None:
    try:
        data = _serializer(secret_key).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    uid = data.get("uid")
    if uid is None:
        return None
    try:
        return int(uid)
    except (TypeError, ValueError):
        return None
