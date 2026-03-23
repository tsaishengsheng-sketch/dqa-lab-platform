import os
import time
import hashlib
import secrets
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import APIRouter
from pydantic import BaseModel
from .models import SessionLocal, User
from typing import Optional

DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "")

_fail_tracker: dict = {}
_FAIL_TRACKER_MAXSIZE = 1000

# token → {user_id, role, expires_at}
_token_store: dict = {}
TOKEN_TTL = 8 * 60 * 60  # 8 小時

SKIP_PATHS = {
    "/api/line/webhook",
    "/docs",
    "/openapi.json",
    "/api/latest",
    "/health",
    "/api/auth/login",
}
MAX_ATTEMPTS = 5
BLOCK_SECONDS = 600

router = APIRouter()


# ---------- 密碼雜湊 ----------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


# ---------- Token ----------
def create_token(user_id: int, role: str) -> str:
    token = secrets.token_hex(32)
    _token_store[token] = {
        "user_id": user_id,
        "role": role,
        "expires_at": time.time() + TOKEN_TTL,
    }
    return token


def get_token_info(token: str) -> Optional[dict]:
    info = _token_store.get(token)
    if not info:
        return None
    if info["expires_at"] < time.time():
        del _token_store[token]
        return None
    return info


def revoke_token(token: str):
    _token_store.pop(token, None)


# ---------- Rate limiting ----------
def _get_tracker(ip: str) -> dict:
    if ip not in _fail_tracker:
        if len(_fail_tracker) >= _FAIL_TRACKER_MAXSIZE:
            now = time.time()
            expired = [
                k
                for k, v in _fail_tracker.items()
                if v["blocked_until"] < now and v["count"] == 0
            ]
            for k in expired:
                del _fail_tracker[k]
            if len(_fail_tracker) >= _FAIL_TRACKER_MAXSIZE:
                keys_to_remove = list(_fail_tracker.keys())[
                    : _FAIL_TRACKER_MAXSIZE // 2
                ]
                for k in keys_to_remove:
                    del _fail_tracker[k]
        _fail_tracker[ip] = {"count": 0, "blocked_until": 0.0}
    return _fail_tracker[ip]


# ---------- 登入 API ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    role: str
    display_name: str


@router.post("/api/auth/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request):
    ip = request.client.host
    tracker = _get_tracker(ip)
    now = time.time()

    if tracker["blocked_until"] > now:
        remaining = int(tracker["blocked_until"] - now)
        return JSONResponse(
            status_code=429, content={"detail": f"太多次錯誤，請 {remaining} 秒後再試"}
        )

    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(User.username == body.username, User.is_active == True)
            .first()
        )

        if not user or not verify_password(body.password, user.hashed_password):
            tracker["count"] += 1
            if tracker["count"] >= MAX_ATTEMPTS:
                tracker["blocked_until"] = now + BLOCK_SECONDS
                tracker["count"] = 0
                return JSONResponse(
                    status_code=429, content={"detail": "錯誤次數過多，封鎖 10 分鐘"}
                )
            return JSONResponse(status_code=401, content={"detail": "帳號或密碼錯誤"})

        tracker["count"] = 0
        token = create_token(user.id, user.role)
        return LoginResponse(
            token=token, role=user.role, display_name=user.display_name
        )
    finally:
        db.close()


@router.post("/api/auth/logout")
def logout(request: Request):
    token = request.headers.get("X-User-Token", "")
    if token:
        revoke_token(token)
    return {"ok": True}


# ---------- Middleware ----------
async def auth_middleware(request: Request, call_next):
    if any(request.url.path.startswith(p) for p in SKIP_PATHS):
        return await call_next(request)

    if request.method == "OPTIONS":
        return await call_next(request)

    if not DEMO_PASSWORD:
        return await call_next(request)

    ip = request.client.host
    tracker = _get_tracker(ip)
    now = time.time()

    if tracker["blocked_until"] > now:
        remaining = int(tracker["blocked_until"] - now)
        return JSONResponse(
            status_code=429, content={"detail": f"太多次錯誤，請 {remaining} 秒後再試"}
        )

    # 方式一：X-User-Token（帳號登入）
    user_token = request.headers.get("X-User-Token", "")
    if user_token:
        info = get_token_info(user_token)
        if info:
            request.state.user_role = info["role"]
            request.state.user_id = info["user_id"]
            tracker["count"] = 0
            return await call_next(request)
        return JSONResponse(status_code=401, content={"detail": "Token 無效或已過期"})

    # 方式二：X-Demo-Password（訪客模式，保留現有功能）
    provided = request.headers.get("X-Demo-Password", "")
    if provided == DEMO_PASSWORD:
        request.state.user_role = "guest"
        request.state.user_id = None
        tracker["count"] = 0
        return await call_next(request)

    tracker["count"] += 1
    if tracker["count"] >= MAX_ATTEMPTS:
        tracker["blocked_until"] = now + BLOCK_SECONDS
        tracker["count"] = 0
        return JSONResponse(
            status_code=429, content={"detail": "錯誤次數過多，封鎖 10 分鐘"}
        )

    return JSONResponse(status_code=401, content={"detail": "密碼錯誤"})
