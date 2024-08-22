from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class User(Base):  # Class names should follow the PascalCase convention
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)  # Corrected the type from 'string' to 'String'
    is_active = Column(Boolean, default=True)  # Corrected the type from 'boolen' to 'Boolean'

    items = relationship("Item", back_populates="owner")  # Corrected class name reference

class Item(Base):  # Class names should follow the PascalCase convention
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))  # Corrected the table name from 'user' to 'users'
    owner = relationship("User", back_populates="items")  # Corrected class name reference
