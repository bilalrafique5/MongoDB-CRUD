from passlib.hash import argon2
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional

# JWT Config
SECRET_KEY = "YOUR_SECRET_KEY_HERE"  # Change to a strong secret in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# --- PASSWORD HASHING ---
def hash_password(password: str) -> str:
    return argon2.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return argon2.verify(plain_password, hashed_password)

# --- JWT TOKEN ---
def create_access_token(username: str, email: str, expires_delta: Optional[timedelta] = None):
    to_encode = {"sub": username, "email": email}  # include email in token
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # payload will have 'sub', 'email', 'exp'
        return payload
    except JWTError:
        return None
