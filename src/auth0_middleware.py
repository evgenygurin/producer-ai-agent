"""
Auth0 authentication middleware for FastAPI
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


class Auth0Config:
    """Auth0 configuration"""

    def __init__(
        self,
        domain: str,
        audience: str,
        client_id: str,
        client_secret: Optional[str] = None,
        algorithms: list[str] = None
    ):
        self.domain = domain
        self.audience = audience
        self.client_id = client_id
        self.client_secret = client_secret
        self.algorithms = algorithms or ["RS256"]
        self.issuer = f"https://{domain}/"
        self.jwks_url = f"https://{domain}/.well-known/jwks.json"


@lru_cache()
def get_jwks(jwks_url: str) -> Dict[str, Any]:
    """
    Fetch JWKS (JSON Web Key Set) from Auth0
    Cached to avoid repeated requests
    """
    try:
        response = httpx.get(jwks_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching JWKS: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not fetch authentication keys"
        )


def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
    auth0_config: Auth0Config = None
) -> Dict[str, Any]:
    """
    Verify JWT token from Auth0

    Args:
        credentials: HTTP bearer token credentials
        auth0_config: Auth0 configuration

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid
    """
    if not auth0_config:
        raise HTTPException(
            status_code=500,
            detail="Auth0 configuration not provided"
        )

    token = credentials.credentials

    try:
        # Get JWKS
        jwks = get_jwks(auth0_config.jwks_url)

        # Decode token header to get key ID
        unverified_header = jwt.get_unverified_header(token)

        # Find the key
        rsa_key = {}
        for key in jwks.get("keys", []):
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break

        if not rsa_key:
            raise HTTPException(
                status_code=401,
                detail="Unable to find appropriate key"
            )

        # Verify and decode token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=auth0_config.algorithms,
            audience=auth0_config.audience,
            issuer=auth0_config.issuer
        )

        logger.info(f"Token verified for user: {payload.get('sub')}")
        return payload

    except JWTError as e:
        logger.error(f"JWT verification error: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )


class Auth0User:
    """Represents authenticated user from Auth0"""

    def __init__(self, token_payload: Dict[str, Any]):
        self.sub = token_payload.get("sub")  # Auth0 user ID
        self.email = token_payload.get("email")
        self.name = token_payload.get("name")
        self.nickname = token_payload.get("nickname")
        self.picture = token_payload.get("picture")
        self.permissions = token_payload.get("permissions", [])
        self.scope = token_payload.get("scope", "").split()
        self.raw_payload = token_payload

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions

    def has_scope(self, scope: str) -> bool:
        """Check if user has specific scope"""
        return scope in self.scope


def get_current_user(
    token_payload: Dict[str, Any] = Depends(verify_token)
) -> Auth0User:
    """
    Dependency to get current authenticated user

    Usage:
        @app.get("/protected")
        async def protected_route(user: Auth0User = Depends(get_current_user)):
            return {"user_id": user.sub}
    """
    return Auth0User(token_payload)


def require_permission(permission: str):
    """
    Decorator to require specific permission

    Usage:
        @app.get("/admin")
        @require_permission("admin:access")
        async def admin_route(user: Auth0User = Depends(get_current_user)):
            return {"message": "Admin access granted"}
    """
    def permission_checker(user: Auth0User = Depends(get_current_user)):
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission required: {permission}"
            )
        return user
    return permission_checker
