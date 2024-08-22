from fastapi import FastAPI, Query,Form ,File,UploadFile,HTTPException# Import Query
from typing import Union
from enum import Enum
from pydantic import BaseModel

# Define a Pydantic model for the request body
class Schema1(BaseModel):
    name: str
    Class: str
    roll_no: int

# Define an Enum for model names
class ChoiceNames(str, Enum):
    one = "one"
    two = "Two"
    three = "Three"

app = FastAPI()

@app.get("/hello")
def read_root():
    return {"message": "Hello from Ratnani Ji"}

@app.get("/hy")
def rahul():
    return {"message": "Hi, how are you!!"}

@app.get("/item/{item}")
def path_function(item: str):
    var_name = {"path variable": item}
    return var_name

@app.get("/query/")
def query_function(
    Name: Union[str, None] = None,
    roll_no: Union[str, None] = Query(default=None, min_length=3, max_length=4)
):
    a = {"name": Name, "roll_no": roll_no}
    return a

@app.get("/models/{model_name}")
def get_model(model_name: ChoiceNames):  # Use 'model_name' to match the path parameter
    if model_name.value == "one":
        return {"model_name": model_name, "message": "calling one!!"}
    elif model_name.value == "Two":
        return {"model_name": model_name, "message": "calling Two!!"}
    else:
        return {"model_name": model_name, "message": "calling Three"}

@app.post("/items/")
def create_item(item: Schema1):
    return item



class abc(BaseModel):
    one: str
    two: str
    three: int  # Correctly annotated field

#form data 
@app.post("/form/data")
def form_data(username:str=Form(), password:str=Form()):
    return {"username":username,"password":password}

# file upload 
@app.post("/file/upload")
def file_bytes_len(file:bytes= File()):
    return({"file":len(file)})

@app.post("/form/data/filedata")
def formdata_upload(file1:UploadFile,file2:bytes=File(),name:str=Form()):
    return ({"file_name":file1.filename,"file2_bytes":len(file2),"name":name})

item=[i for i in range(10)]
@app.get("/error/handling")
def handle_error(items:int):
    if items not in item:
        return HTTPException(status_code=400,detail="item is not equal to 2 try another value!!!")
    return {"value":items}