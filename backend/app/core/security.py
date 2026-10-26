import uuid
from datetime import datetime, timedelta, timezone
import bcrypt, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings

ALG = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()

def verify_password(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw.encode(), hashed.encode())

def create_access_token(subject: str, role: str, ttl_minutes: int | None = None) -> str:
    ttl = settings.jwt_ttl_minutes if ttl_minutes is None else ttl_minutes
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": subject, "role": role, "iat": now,
                       "exp": now + timedelta(minutes=ttl), "jti": uuid.uuid4().hex},
                      settings.jwt_secret, algorithm=ALG)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALG])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Токен недействителен или истёк",
                           headers={"WWW-Authenticate": "Bearer"}) from exc

def current_user(token: str = Depends(oauth2_scheme)) -> dict:
    return decode_token(token)

def require_admin(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "ADMIN":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав (RBAC)")
    return user