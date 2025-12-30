from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm,HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from main import MongoCRUD
from auth_utils import hash_password, verify_password, create_access_token, decode_access_token
from bson import ObjectId
from jwt_middleware import jwt_middleware
from fastapi import Request

app = FastAPI(title="MongoDB CRUD + JWT Authentication")
app.middleware("http")(jwt_middleware)
db = MongoCRUD(db_name="testDB", collection_name="students")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Define Bearer auth
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    # Apply Bearer auth to all routes except /register and /token
    for path in openapi_schema["paths"]:
        if path not in ["/register", "/token"]:
            for method in openapi_schema["paths"][path]:
                openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi



# --- MODELS ---
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

# --- HELPERS ---
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


# --- AUTH DEPENDENCY ---
bearer_scheme = HTTPBearer()

# Update get_current_user dependency
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
    
    # Include username and email in token
    access_token = create_access_token(username=db_user["username"], email=db_user["email"])
    
    return {"access_token": access_token, "token_type": "bearer"}



# --- STUDENT CRUD ROUTES (JWT Protected) ---

# READ
@app.get("/students/", response_model=List[Student], tags=["READ"])
def get_all_students(request: Request):
    return [student_helper(s) for s in db.read_all()]


@app.get("/students/name/{name}", response_model=Student, tags=["READ"])
def get_student_by_name(name: str, request: Request):
    student = db.read_one({"name": name})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student_helper(student)


@app.get("/students/id/{id}", response_model=Student, tags=["READ"])
def get_student_by_id(id: str, request: Request):
    student = db.read_one({"_id": ObjectId(id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student ID not found")
    return student_helper(student)


@app.get("/students/filter/age", response_model=List[Student], tags=["READ"])
def get_students_by_age(min_age: int, request: Request):
    students = db.read_many({"age": {"$gt": min_age}})
    if not students:
        raise HTTPException(status_code=404, detail="No students found")
    return [student_helper(s) for s in students]


@app.get("/students/filter/name", response_model=List[Student], tags=["READ"])
def get_students_by_name_starts(letter: str, request: Request):
    students = db.read_many({
        "name": {"$regex": f"^{letter}", "$options": "i"}
    })
    if not students:
        raise HTTPException(
            status_code=404,
            detail=f"No students found starting with {letter}"
        )
    return [student_helper(s) for s in students]


# CREATE
@app.post("/students/", tags=["CREATE"])
def create_student(student: Student, request: Request):
    user = request.state.user  # decoded JWT
    doc = student.dict()
    doc["created_at"] = datetime.now()
    doc["created_by"] = user["sub"]

    inserted_id = db.create_one(doc)
    return {"message": "Student created", "id": str(inserted_id)}


@app.post("/students/batch", tags=["CREATE"])
def create_students_batch(students: List[Student], request: Request):
    user = request.state.user

    docs = []
    for s in students:
        doc = s.dict()
        doc["created_at"] = datetime.now()
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



# DELETE
@app.delete("/students/student_name/{name}", tags=["DELETE"])
def delete_student_by_name(name: str, request: Request):
    result = db.delete_one({"name": name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": f"Student '{name}' deleted"}


@app.delete("/students/student_id/{id}", tags=["DELETE"])
def delete_student_by_id(id: str, request: Request):
    result = db.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": f"Student '{id}' deleted"}


@app.delete("/students/", tags=["DELETE"])
def delete_all_students(request: Request):
    result = db.delete_all()
    return {"message": f"Deleted {result.deleted_count} students"}




@app.get("/decode-token", tags=["AUTHENTICATION"])
def decode_token(request: Request):
    return {
        "verified": True,
        "user_info": request.state.user
    }

    

