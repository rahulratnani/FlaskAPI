from typing import List
from fastapi import Depends,FastAPI,HTTPException
from sqlalchemy.orm import session
import crud,models,schemas
from database import SessionLocal,engine
models.Base.metadata.create_all(bind=engine)
app=FastAPI()
@app.get("/")
def checking():
    return ("helloooo.....")