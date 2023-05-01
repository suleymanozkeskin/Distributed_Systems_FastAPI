# models.py
from dotenv import load_dotenv

load_dotenv()

import databases
import sqlalchemy
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from pydantic import BaseModel

# Read environment variables
database_hostname = os.environ["DATABASE_HOSTNAME"]
database_port = os.environ["DATABASE_PORT"]
database_password = os.environ["DATABASE_PASSWORD"]
database_username = os.environ["DATABASE_USERNAME"]

# Create the DATABASE_URLS list
database_names = [
    os.environ[f"DATABASE_NAME_{i}"] for i in range(1, 8)
]
DATABASE_URLS = [
    f"postgresql://{database_username}:{database_password}@{database_hostname}:{database_port}/{database_name}"
    for database_name in database_names
]

databases_list = [databases.Database(url) for url in DATABASE_URLS]
metadata = sqlalchemy.MetaData()
engines = [create_engine(url) for url in DATABASE_URLS]
SessionLocals = [sessionmaker(autocommit=False, autoflush=False, bind=engine) for engine in engines]

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, index=True, unique=True)
    location = Column(String, index=True) # iso country code (2 characters)

# Create tables for all databases
for engine in engines:
    Base.metadata.create_all(bind=engine)

# schema for UserCreate:
class UserCreate(BaseModel):
    name: str
    email: str
    location: str

    # orm mode true
    class Config:
        orm_mode = True

        

