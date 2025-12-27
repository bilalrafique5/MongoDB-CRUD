from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from main import MongoCRUD
from auth_utils import hash_password, verify_password, create_access_token, decode_access_token
from bson import ObjectId



app = FastAPI(title="MongoDB CRUD + JWT Authentication")
db = MongoCRUD(db_name="testDB", collection_name="students")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.find_user({"username": payload.get("sub")})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

# --- AUTH ROUTES ---
@app.post("/register", response_model=dict)
def register(user: User):
    existing_user = db.find_user({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_pwd = hash_password(user.password)
    db.create_user({"username": user.username, "email": user.email, "password": hashed_pwd})
    return {"message": f"User {user.username} created successfully"}

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.find_user({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

# --- STUDENT CRUD ROUTES (JWT Protected) ---

# READ
@app.get("/students/", response_model=List[Student])
def get_all_students(current_user: dict = Depends(get_current_user)):
    students = db.read_all()
    return [student_helper(s) for s in students]

@app.get("/students/name/{name}", response_model=Student)
def get_student_by_name(name: str, current_user: dict = Depends(get_current_user)):
    student = db.read_one({"name": name})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student_helper(student)

@app.get("/students/id/{id}", response_model=Student)
def get_student_by_id(id: str, current_user: dict = Depends(get_current_user)):
    student = db.read_one({"_id": ObjectId(id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student ID not found")
    return student_helper(student)

@app.get("/students/filter/age", response_model=List[Student])
def get_students_by_age(min_age: int, current_user: dict = Depends(get_current_user)):
    students = db.read_many({"age": {"$gt": min_age}})
    if not students:
        raise HTTPException(status_code=404, detail="No students found")
    return [student_helper(s) for s in students]

@app.get("/students/filter/name", response_model=List[Student])
def get_students_by_name_starts(letter: str, current_user: dict = Depends(get_current_user)):
    regex_pattern = f"^{letter}"
    students = db.read_many({"name": {"$regex": regex_pattern, "$options": "i"}})
    if not students:
        raise HTTPException(status_code=404, detail=f"No students found starting with {letter}")
    return [student_helper(s) for s in students]

# CREATE
@app.post("/students/", response_model=dict)
def create_student(student: Student, current_user: dict = Depends(get_current_user)):
    doc = student.dict()
    doc["created_at"] = datetime.now()
    inserted_id = db.create_one(doc)
    return {"message": "Student created", "id": str(inserted_id)}

@app.post("/students/batch", response_model=dict)
def create_students_batch(students: List[Student], current_user: dict = Depends(get_current_user)):
    docs = [s.dict() for s in students]
    for doc in docs:
        doc["created_at"] = datetime.now()
    inserted_ids = db.create_many(docs)
    return {"message": f"{len(inserted_ids)} students inserted", "ids": [str(_id) for _id in inserted_ids]}

# UPDATE
@app.put("/students/{name}", response_model=dict)
def update_student(name: str, student: UpdateStudent, current_user: dict = Depends(get_current_user)):
    updated_values = {k: v for k, v in student.dict().items() if v is not None}
    if not updated_values:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db.update_one({"name": name}, updated_values)
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Student not found or nothing updated")
    return {"message": f"Student '{name}' updated"}

# DELETE
@app.delete("/students/student_name/{name}", response_model=dict)
def delete_student_by_name(name: str, current_user: dict = Depends(get_current_user)):
    result = db.delete_one({"name": name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": f"Student '{name}' deleted"}

@app.delete("/students/student_id/{id}", response_model=dict)
def delete_student_by_id(id: str, current_user: dict = Depends(get_current_user)):
    result = db.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": f"Student '{id}' deleted"}

@app.delete("/students/", response_model=dict)
def delete_all_students(current_user: dict = Depends(get_current_user)):
    result = db.delete_all()
    return {"message": f"Deleted {result.deleted_count} students"}
