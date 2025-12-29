# pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt] pymongo python-multipart

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
from pymongo import MongoClient
from bson import ObjectId

# ============================================
# CONFIGURATION
# ============================================
SECRET_KEY = "bilalrafiquesecretkeyishere"  # Use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client["school_db"]
users_collection = db["users"]
students_collection = db["students"]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app = FastAPI()

# ============================================
# MODELS
# ============================================
class User(BaseModel):
    username: str
    email: str
    password: str
    role: str = "user"  # user, admin, teacher, etc.

class UserInDB(BaseModel):
    username: str
    email: str
    hashed_password: str
    role: str

class Student(BaseModel):
    name: str
    age: int
    grade: str
    email: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# ============================================
# HELPER FUNCTIONS
# ============================================
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user(username: str):
    user = users_collection.find_one({"username": username})
    if user:
        return UserInDB(
            username=user["username"],
            email=user["email"],
            hashed_password=user["hashed_password"],
            role=user.get("role", "user")
        )
    return None

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

# ============================================
# 1. REGISTER USER
# ============================================
@app.post("/register", status_code=status.HTTP_201_CREATED, tags=["REGISTER"])
async def register(user: User):
    # Check if user already exists
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create user document
    user_dict = {
        "username": user.username,
        "email": user.email,
        "hashed_password": get_password_hash(user.password),
        "role": user.role,
        "created_at": datetime.utcnow()
    }
    
    result = users_collection.insert_one(user_dict)
    
    return {
        "message": "User registered successfully",
        "user_id": str(result.inserted_id),
        "username": user.username
    }

# ============================================
# 2. LOGIN - RETURN JWT TOKEN
# ============================================
@app.post("/login", response_model=Token ,tags=["LOGIN"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# ============================================
# 3. PROTECTED ROUTES - USE TOKEN FOR AUTHORIZATION
# ============================================

# Get current user info
@app.get("/users/me", tags=['READ'])
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role
    }

# Create student (protected route)
@app.post("/students", status_code=status.HTTP_201_CREATED, tags=['CREATE'])
async def create_student(
    student: Student,
    current_user: UserInDB = Depends(get_current_user)
):
    student_dict = student.dict()
    student_dict["created_by"] = current_user.username
    student_dict["created_at"] = datetime.utcnow()
    
    result = students_collection.insert_one(student_dict)
    
    return {
        "message": "Student created successfully",
        "student_id": str(result.inserted_id),
        "name": student.name
    }

# Get all students (protected route)
@app.get("/students", tags=["READ"])
async def get_students(current_user: UserInDB = Depends(get_current_user)):
    students = []
    for student in students_collection.find():
        student["_id"] = str(student["_id"])
        students.append(student)
    
    return {
        "students": students,
        "count": len(students)
    }

# Get specific student (protected route)
@app.get("/students/{student_id}", tags=["READ"])
async def get_student(
    student_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        student = students_collection.find_one({"_id": ObjectId(student_id)})
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        student["_id"] = str(student["_id"])
        return student
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid student ID"
        )

# Update student (protected route)
@app.put("/students/{student_id}", tags=["UPDATE"])
async def update_student(
    student_id: str,
    student: Student,
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        result = students_collection.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": student.dict()}
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        return {"message": "Student updated successfully"}
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid student ID"
        )

# Delete student (protected route - admin only example)
@app.delete("/students/{student_id}", tags=["DELETE"])
async def delete_student(
    student_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    # Role-based access control
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        result = students_collection.delete_one({"_id": ObjectId(student_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        return {"message": "Student deleted successfully"}
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid student ID"
        )

# Public route (no authentication required)
@app.get("/")
async def root():
    return {"message": "Welcome to Student Management API"}

# ============================================
# RUN SERVER
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# ============================================
# USAGE EXAMPLES WITH CURL/HTTPIE:
# ============================================
"""
1. Register a user:
POST http://localhost:8000/register
{
  "username": "john",
  "email": "john@example.com",
  "password": "secret123",
  "role": "teacher"
}

2. Login (get token):
POST http://localhost:8000/login
Form data: username=john&password=secret123

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
  "token_type": "bearer"
}

3. Get current user info (with token):
GET http://localhost:8000/users/me
Headers: Authorization: Bearer <your-token>

4. Create a student (with token):
POST http://localhost:8000/students
Headers: Authorization: Bearer <your-token>
{
  "name": "Alice Smith",
  "age": 15,
  "grade": "10th",
  "email": "alice@example.com"
}

5. Get all students (with token):
GET http://localhost:8000/students
Headers: Authorization: Bearer <your-token>

6. Get specific student (with token):
GET http://localhost:8000/students/<student_id>
Headers: Authorization: Bearer <your-token>
"""