from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from main import MongoCRUD
from bson import ObjectId
from datetime import datetime
from typing import Optional
from typing import List




app = FastAPI(title="MongoDB CRUD Application")
db = MongoCRUD(db_name="testDB", collection_name="students")

def student_helper(student) -> dict:
    """Convert MongoDB document to JSON-serializable dict"""
    if not student:
        return None
    return {
        # "id": str(student.get("_id")),
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

class UpdateStudent(BaseModel):
    age:Optional[int]=None
    city:Optional[str]=None
    email:Optional[str]=None

class ResponseModel(BaseModel):
    name:str
    age:int
    city:str
    email:str
    


class BatchInsertResponse(BaseModel):
    message: str
    ids: List[str]  

class MessageResponse(BaseModel):
    message:str



@app.get("/", tags=["READ"])
def root():
    students = db.read_all()
    return {"message":"MongoDP CRUD API running"}




#READ
@app.get("/students/", tags=["READ"],response_model=list[ResponseModel])
def get_all_students():
    students = db.read_all()
    if not students:
        raise HTTPException(status_code=404, detail="No students found")
    return students

@app.get("/students/name/{name}", tags=["READ"],response_model=ResponseModel)
def get_student(name: str):
    student = db.read_one({"name": name})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student_helper(student)

@app.get("/students/id/{id}", tags=["READ"],response_model=ResponseModel)
def get_student_by_id(id:str):
    student_id=db.read_one({"_id":ObjectId(id)})
    if not student_id:
        raise HTTPException(status_code=404, detail="Student ID not Found")
    return student_helper(student_id)

@app.get("/students/filter/age", tags=["READ"],response_model=list[ResponseModel])
def get_students_by_age(min_age:int):
    query={"age":{"$gt":min_age}}
    students=db.read_many(query)
    # print("STUDENTS: ",students)
    if not students:
        raise HTTPException(status_code=404, detail="No Students Found")
    
    return [student_helper(s) for s in students]
     
    # print("RES: ", response)
    # return response
    
    
@app.get("/students/filter/name",tags=["READ"],response_model=list[ResponseModel])
def get_students_by_name_starts(letter:str):
    regex_pattern=f"^{letter}"
    query={"name":{"$regex":regex_pattern, "$options":"i"}}
    students=db.read_many(query)
    if not students:
        raise HTTPException(status_code=404, detail=f"No Students found Name starts with {letter} ")
    
    return [student_helper(s) for s in students]
    
    


#CREATE 
@app.post("/students/", tags=["CREATE"],response_model=list[ResponseModel])
def create_student(student:Student):
    doc=student.dict()
    doc["created_at"]=datetime.now()
    inserted_id=db.create_one(doc)
    return {"message":"Student created","id":str(inserted_id)}



@app.post("/students/batch", tags=["CREATE"],response_model=BatchInsertResponse)
def create_students(students:list[Student]):
    
    docs=[s.dict() for s in students]
    
    for doc in docs:
        doc["created_at"]=datetime.now()
        
    inserted_ids=db.create_many(docs)
    return {"message":f"{len(inserted_ids)} students inserted",
            "ids":[str(_id) for _id in inserted_ids]
            
            }
    

# UPDATE
@app.put("/students/update/{name}", tags=["UPDATE"], response_model=MessageResponse)
def update_student(name: str, student:UpdateStudent):
    updated_values={k:v for k, v in student.dict().items() if v is not None}
    if not updated_values:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db.update_one({"name":name}, updated_values)
    if result.modified_count==0:
        raise HTTPException(status_code=404, detail="Student not found or nothing update")
    return {"message":f"Student '{name}' updated"}


# DELETE
@app.delete("/students/student_name/{name}", tags=["DELETE"],response_model=ResponseModel)
def delete_student_by_name(name:str):
    result=db.delete_one({"name":name})
    if result.deleted_count==0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message":f"Student '{name}' deleted"}

@app.delete("/students/student_id/{id}", tags=["DELETE"],response_model=ResponseModel)
def delete_student_by_id(id:str):
    result=db.delete_one({"_id":ObjectId(id)})
    if result.deleted_count==0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message":f"Student '{id}' deleted"}


@app.delete("/students/", tags=["DELETE"],response_model=list[ResponseModel])
def delete_all_students():
    result=db.delete_all()
    return {"message":f"Deleted {result.deleted_count} students"}

