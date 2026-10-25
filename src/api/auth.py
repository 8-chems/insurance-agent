import os
from functools import lru_cache
import jwt
from fastapi import Header, HTTPException
from src.common.config import settings


@lru_cache(maxsize=1)
def _jwks() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(os.environ["JWKS_URL"], cache_keys=True)


def verified_customer(authorization: str | None = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401)
    token = authorization.removeprefix("Bearer ")
    if settings.allow_dev_tokens:          # LOCAL ONLY: token is the customer id
        return token
    try:
        key = _jwks().get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"],
                            audience=os.environ["JWT_AUDIENCE"], issuer=os.environ["JWT_ISSUER"])
    except jwt.PyJWTError:
        raise HTTPException(401)
    if not claims.get("customer_id"):
        raise HTTPException(403)
    return claims["customer_id"]
