from pydantic import BaseModel, HttpUrl
from sqlmodel  import Field, SQLModel
import secrets
import string


def code_generator():
        sequence = string.ascii_letters + string.digits
        code = ''.join(secrets.choice(sequence) for _ in range(7))
        return code


class UrlAPI(SQLModel):
    long_url: HttpUrl


class UrlTable(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    long_url:str = Field(index=True)
    code:str=Field(default_factory=code_generator, unique=True, index=True)

class GetCode(SQLModel):
    code:str

class PostURL(SQLModel):
     long_url:str

    
