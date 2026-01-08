from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# App imports
from app.models import MongoCRUD
from app.auth_utils import hash_password, verify_password, create_access_token, decode_access_token
from app.jwt_middleware import jwt_middleware

# --- APP ---
app = FastAPI(title="MongoDB CRUD + JWT Authentication")
app.middleware("http")(jwt_middleware)

# --- DB ---
db = MongoCRUD()

# --- Security ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
bearer_scheme = HTTPBearer()

# --- OPENAPI JWT ---
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    for path in openapi_schema["paths"]:
        if path not in ["/register", "/token"]:
            for method in openapi_schema["paths"][path]:
                openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# --- Pydantic Models ---
class Student(BaseModel):
    name: str
    age: int
    city: str
    email: str

class UpdateStudent(BaseModel):
    age: Optional[int] = None
    city: Optional[str] = None
    email: Optional[str] = None

class User(BaseModel):
    username: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# --- Helpers ---
def student_helper(student):
    if not student:
        return None
    return {
        "id": str(student.get("_id")),
        "name": student.get("name"),
        "email": student.get("email"),
        "age": student.get("age"),
        "city": student.get("city")
    }

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.find_user({"username": payload.get("sub")})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# --- AUTH ROUTES ---
@app.post("/register", response_model=dict, tags=["AUTHENTICATION"])
def register(user: User):
    existing_user = db.find_user({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_pwd = hash_password(user.password)
    db.create_user({"username": user.username, "email": user.email, "password": hashed_pwd})
    return {"message": f"User {user.username} created successfully"}

@app.post("/token", response_model=Token, tags=["AUTHENTICATION"])
def login(user: User):
    db_user = db.find_user({"username": user.username})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(username=db_user["username"], email=db_user["email"])
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/decode-token", tags=["AUTHENTICATION"])
def decode_token(request: Request):
    return {"verified": True, "user_info": request.state.user}

# --- STUDENT CRUD ROUTES ---

# READ ALL
@app.get("/students/", response_model=List[Student], tags=["READ"])
def get_all_students(request: Request):
    return [student_helper(s) for s in db.read_all()]

# READ BY NAME
@app.get("/students/name/{name}", response_model=Student, tags=["READ"])
def get_student_by_name(name: str, request: Request):
    student = db.read_one({"name": name})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student_helper(student)

# READ BY ID
@app.get("/students/id/{id}", response_model=Student, tags=["READ"])
def get_student_by_id(id: str, request: Request):
    try:
        student = db.read_one({"_id": ObjectId(id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    if not student:
        raise HTTPException(status_code=404, detail="Student ID not found")
    return student_helper(student)

# FILTER BY AGE
@app.get("/students/filter/age", response_model=List[Student], tags=["READ"])
def get_students_by_age(min_age: int, request: Request):
    students = db.read_many({"age": {"$gt": min_age}})
    if not students:
        raise HTTPException(status_code=404, detail="No students found")
    return [student_helper(s) for s in students]

# FILTER BY NAME START
@app.get("/students/filter/name", response_model=List[Student], tags=["READ"])
def get_students_by_name_starts(letter: str, request: Request):
    students = db.read_many({"name": {"$regex": f"^{letter}", "$options": "i"}})
    if not students:
        raise HTTPException(status_code=404, detail=f"No students found starting with {letter}")
    return [student_helper(s) for s in students]

# CREATE ONE STUDENT
@app.post("/students/", tags=["CREATE"])
def create_student(student: Student, request: Request):
    user = request.state.user
    doc = student.dict()
    doc["created_at"] = datetime.utcnow()
    doc["created_by"] = user["sub"]
    inserted_id = db.create_one(doc)
    return {"message": "Student created", "id": str(inserted_id)}

# CREATE BATCH STUDENTS
@app.post("/students/batch", tags=["CREATE"])
def create_students_batch(students: List[Student], request: Request):
    user = request.state.user
    docs = []
    for s in students:
        doc = s.dict()
        doc["created_at"] = datetime.utcnow()
        doc["created_by"] = user["sub"]
        docs.append(doc)
    ids = db.create_many(docs)
    return {"message": f"{len(ids)} students inserted", "ids": [str(i) for i in ids]}

# UPDATE
@app.put("/students/{name}", tags=["UPDATE"])
def update_student(name: str, student: UpdateStudent, request: Request):
    updates = {k: v for k, v in student.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db.update_one({"name": name}, updates)
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Student not found or nothing updated")
    return {"message": f"Student '{name}' updated"}

# DELETE BY NAME
@app.delete("/students/student_name/{name}", tags=["DELETE"])
def delete_student_by_name(name: str, request: Request):
    result = db.delete_one({"name": name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": f"Student '{name}' deleted"}

# DELETE BY ID
@app.delete("/students/student_id/{id}", tags=["DELETE"])
def delete_student_by_id(id: str, request: Request):
    try:
        result = db.delete_one({"_id": ObjectId(id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": f"Student '{id}' deleted"}

# DELETE BY AGE (single)
@app.delete("/students/delete/{age}", tags=["DELETE"])
def delete_students_by_age(age: int, request: Request):
    result = db.delete_one({"age": {"$lt": age}})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No students found below the specified age")
    return {"message": f"Deleted {result.deleted_count} students below age {age}"}

# DELETE BY AGE (batch)
@app.delete("/students/delete/batch/{age}", tags=["DELETE"])
def delete_students_batch(age: int, request: Request):
    result = db.delete_many({"age": {"$lt": age}})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No students found below the specified age")
    return {"message": f"Deleted {result.deleted_count} students below age {age}"}

# DELETE ALL STUDENTS
@app.delete("/students/", tags=["DELETE"])
def delete_all_students(request: Request):
    result = db.delete_all()
    return {"message": f"Deleted {result.deleted_count} students"}
