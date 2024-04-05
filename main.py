from fastapi import FastAPI, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from pymongo import MongoClient
from bson import ObjectId, errors as bson_errors
import urllib.parse

# MongoDB credentials
username = "Jasjot784"
password = "223784@Home"

# MongoDB connection string from your MongoDB Atlas dashboard
# Replace <username>, <password>, and <cluster_name> with your MongoDB Atlas credentials
encoded_username = urllib.parse.quote_plus(username)
encoded_password = urllib.parse.quote_plus(password)
cluster_name = "cluster0.6dj09wf.mongodb.net"
mongo_connection_str = f"mongodb+srv://{encoded_username}:{encoded_password}@{cluster_name}/students?retryWrites=true&w=majority"

app = FastAPI()

# MongoDB client
client = MongoClient(mongo_connection_str)

# Database and Collection
db = client["students"]
students_collection = db["students"]


# Pydantic models
class Address(BaseModel):
    city: str = Field(..., description="City name", example="New York")
    country: str = Field(..., description="Country name", example="USA")


class Student(BaseModel):
    name: str = Field(..., description="Student's name", example="John Doe")
    age: int = Field(..., description="Student's age", example=20)
    address: Address = Field(..., description="Student's address")


# API Endpoints
@app.post("/students", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_student(student: Student):
    student_dict = student.dict()
    result = students_collection.insert_one(student_dict)
    return {"id": str(result.inserted_id)}



@app.get("/students", response_model=dict, status_code=status.HTTP_200_OK)
async def get_students(country: str = Query(None, description="To apply filter of country. If not given or empty, this filter should be applied.", example="USA"),
                       age: int = Query(None, ge=0, description="Only records which have age greater than or equal to the provided age should be present in the result. If not given or empty, this filter should be applied.")):
    query = {}
    if country:
        query["address.country"] = country
    if age is not None:
        query["age"] = {"$gte": age}

    students = []
    for student in students_collection.find(query):
        students.append({
            "name": student["name"],
            "age": student["age"],
            "address": {
                "city": student["address"]["city"],
                "country": student["address"]["country"]
            }
        })

    return {"data": students}




@app.get("/students/{id}", response_model=Student, status_code=status.HTTP_200_OK)
async def get_student(id: str = Path(..., description="Student ID")):
    try:
        student = students_collection.find_one({"_id": ObjectId(id)})
        if student:
            return Student(**student)
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    except bson_errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid ObjectId format")



@app.patch("/students/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_student(student: Student, id: str = Path(..., description="Student ID")):
    updated_student = student.dict(exclude_unset=True)  # Convert Pydantic model to dict, excluding unset values
    updated_student = {k: v for k, v in updated_student.items() if v is not None}  # Remove None values
    if not updated_student:  # If no valid fields to update
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update")

    try:
        # Check if the student exists
        existing_student = students_collection.find_one({"_id": ObjectId(id)})
        if existing_student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        # Update the student in the database
        result = students_collection.update_one({"_id": ObjectId(id)}, {"$set": updated_student})
        
        if result.modified_count == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No changes to update")

        # No content to return, just return 204 status code
        return
    except bson_errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid ObjectId format")



@app.delete("/students/{id}", response_model=dict, status_code=status.HTTP_200_OK)
async def delete_student(id: str = Path(..., description="Student ID")):
    result = students_collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return {}
