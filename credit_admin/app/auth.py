import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Admin credentials from environment
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # Change this!

# API Key for extensions - use a fixed default that matches extensions
API_KEY = os.getenv("CREDITS_API_KEY", "vY97Yvh6qKywm8xE-ErTGfUofV0t1BiZ36wR3lLNHIY")

# Security setup
security = HTTPBearer()

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    is_admin: bool = False

class UserInDB(User):
    hashed_password: str

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    password_byte_enc = plain_password.encode('utf-8')
    # Handle both string and bytes for hashed_password
    hashed_bytes = hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
    return bcrypt.checkpw(password=password_byte_enc, hashed_password=hashed_bytes)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password.decode('utf-8')

def get_user(username: str) -> Optional[UserInDB]:
    """Get user from our simple in-memory store"""
    if username == ADMIN_USERNAME:
        return UserInDB(
            username=ADMIN_USERNAME,
            hashed_password=get_password_hash(ADMIN_PASSWORD),
            is_admin=True
        )
    return None

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return User(username=user.username, is_admin=user.is_admin)

async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def verify_api_key(request: Request):
    """Verify API key for extension access"""
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    return True

def create_api_key_header():
    """Helper to create API key header for extension configuration"""
    return {"X-API-Key": API_KEY}

# Print configuration on startup
def print_security_config():
    print("🔐 Security Configuration:")
    print(f"   Admin Username: {ADMIN_USERNAME}")
    print(f"   Admin Password: {'*' * len(ADMIN_PASSWORD)}")
    print(f"   API Key: {API_KEY[:8]}...{API_KEY[-8:]}")
    print(f"   Token Expiry: {ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
    if ADMIN_PASSWORD == "admin123":
        print("⚠️  WARNING: Using default admin password! Change ADMIN_PASSWORD environment variable!")
