from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer
import bcrypt as _bcrypt

from app.config import settings

_serializer = URLSafeTimedSerializer(settings.secret_key)
SESSION_COOKIE = "emne_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return _bcrypt.checkpw(password.encode(), hashed.encode())


def create_session_token() -> str:
    return _serializer.dumps("authenticated")


def verify_session_token(token: str) -> bool:
    try:
        return _serializer.loads(token, max_age=SESSION_MAX_AGE) == "authenticated"
    except Exception:
        return False


def get_current_user(request: Request) -> bool:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401)
    if not verify_session_token(token):
        raise HTTPException(status_code=401)
    return True


def login_user(response: Response) -> None:
    token = create_session_token()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )


def logout_user(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)
