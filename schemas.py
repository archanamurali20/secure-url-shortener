from pydantic import BaseModel, HttpUrl
from sqlmodel  import Field, SQLModel
from random import randint


def code_generator():
        return randint(1,1000000)

class UrlAPI(SQLModel):
    long_url: HttpUrl


class UrlTable(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    long_url:str = Field(index=True)
    code:int=Field(default_factory=code_generator, unique=True, index=True)

class GetCode(SQLModel):
    code:int

class PostURL(SQLModel):
     long_url:str

    
