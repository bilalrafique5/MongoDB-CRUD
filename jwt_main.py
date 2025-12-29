from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
from typing import Optional

app = FastAPI()

# Configuration
SECRET_KEY = "qYpCjxZ3FvL5M1hTfGKs7PbX5I2N4QWyNsF3EoVZ1gU="
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()


# Models
class User(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Helper functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    
    # Encode token using secret key and algorithm
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify and decode JWT token from bearer header"""
    token = credentials.credentials
    
    try:
        # Decode token using secret key - THIS IS WHERE DECRYPTION HAPPENS
        # jwt.decode() uses the SECRET_KEY to verify the signature and decrypt the payload
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("Decoded payload:", payload)  # Debugging line to see the decoded payload
        username: str = payload.get("user").get("email") if payload.get("user") else None
        
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return username
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Routes
@app.post("/login", response_model=Token)
async def login(user: User):
    """
    Endpoint to generate access token.
    Frontend sends username/password, gets back a bearer token.
    """
    # In real app, verify password against database
    if user.username == "testuser" and user.password == "password123":
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )

@app.get("/protected")
async def protected_route(username: str = Depends(verify_token)):
    """
    Protected route. Frontend must send:
    Authorization: Bearer <token>
    """
    return {"message": f"Hello {username}, this is a protected route"}

@app.get("/user-profile")
async def get_profile(username: str = Depends(verify_token)):
    """Another protected route"""
    return {
        "username": username,
        "email": f"{username}@example.com",
        "role": "user"
    }