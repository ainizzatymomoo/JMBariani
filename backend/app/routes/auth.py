"""Authentication routes for JM Baryani HQ."""

from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import settings

router = APIRouter()

# --- Admin credentials (hardcoded for now, move to DB later) ---
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "abc123"

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    username: str


class TokenData(BaseModel):
    username: str


def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return TokenData(username=username)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Dependency to get the current authenticated user from token."""
    return verify_token(token)


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user and return JWT token.
    Username: admin | Password: abc123
    """
    if form_data.username != ADMIN_USERNAME or form_data.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": form_data.username})

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        username=form_data.username
    )


@router.get("/me")
async def get_me(current_user: TokenData = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {
        "username": current_user.username,
        "role": "admin"
    }


@router.post("/verify")
async def verify_token_endpoint(current_user: TokenData = Depends(get_current_user)):
    """Verify if token is still valid."""
    return {"valid": True, "username": current_user.username}
