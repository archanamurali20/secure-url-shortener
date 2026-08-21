from pydantic import BaseModel, HttpUrl, EmailStr
from sqlmodel  import Field, SQLModel


# User Table

class UserBase(SQLModel):
     name: str = Field(index=True)
     email: EmailStr = Field(index=True, unique=True)

class UserRequest(UserBase):
     password: str = Field(min_length=8)


class UserTable(UserBase, table=True):
     id: int | None = Field(default=None, primary_key=True)
     hashed_password : str 

# Urls
class UrlAPI(SQLModel):
    long_url: HttpUrl

class UrlTable(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    long_url:str
    code:str=Field(unique=True, index=True)
    owner_id: int = Field(foreign_key="usertable.id",  index=True)

class GetCode(SQLModel):
    code:str
    short_url:str


class GetAllLinks(SQLModel):
     long_url:str
     code: str


# Token
class Token(BaseModel):
     access_token:str
     token_type:str

class TokenData(BaseModel):
     email: str


    
