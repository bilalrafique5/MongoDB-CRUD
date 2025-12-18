from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from main import MongoCRUD
from bson import ObjectId

app = FastAPI(title="MongoDB CRUD Application")
db = MongoCRUD(db_name="testDB", collection_name="students")

def student_helper(student) -> dict:
    """Convert MongoDB document to JSON-serializable dict"""
    if not student:
        return None
    return {
        "id": str(student.get("_id")),
        "name": student.get("name"),
        "email": student.get("email"),
        "age": student.get("age"),
        "city": student.get("city")
    }

class Student(BaseModel):
    name: str
    age: int
    city: str
    email: str

@app.get("/", tags=["READ"])
def root():
    students = db.read_all()
    return {"students": [student_helper(student) for student in students]}


#READ
@app.get("/students/", tags=["READ"])
def get_all_students():
    students = db.read_all()
    if not students:
        raise HTTPException(status_code=404, detail="No students found")
    return {"students": [student_helper(student) for student in students]}

@app.get("/students/name/{name}", tags=["READ"])
def get_student(name: str):
    student = db.read_one({"name": name})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"student": student_helper(student)}

@app.get("/students/id/{id}", tags=["READ"])
def get_student_by_id(id:str):
    student_id=db.read_one(ObjectId(id))
    if not student_id:
        raise HTTPException(status_code=404, detail="Student ID not Found")
    return {"student_id":student_helper(student_id)}

#CREATE 

# @app.post("/students/")

